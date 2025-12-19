"""
NCAA Baseball Box Score PDF Parser

Converts NCAA baseball box score PDFs into structured JSON format.
Supports multiple PDF formats from different years/sources.
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class PlayerBattingStats:
    number: str
    name: str
    position: str
    at_bats: int
    runs: int
    hits: int
    rbi: int
    walks: int
    strikeouts: int
    put_outs: int
    assists: int
    left_on_base: int


@dataclass
class PitcherStats:
    number: str
    name: str
    innings_pitched: float
    hits: int
    runs: int
    earned_runs: int
    walks: int
    strikeouts: int
    batters_faced: int
    at_bats: int
    pitches: int


@dataclass
class PlayEvent:
    description: str
    pitch_count: Optional[str] = None  # e.g., "2-2 KBBK"
    rbi: int = 0
    runs_scored: list = None


def parse_innings_from_text(text: str) -> list[int]:
    """Extract runs per inning from score line."""
    # Pattern: team name followed by numbers
    pattern = r'^\s*(?:VMI|Virginia|[A-Za-z\s\.#\d]+)\s+([\d\s]+)\s+\d+\s+\d+\s+\d+\s+\d+\s*$'
    innings = []
    for line in text.split('\n'):
        # Look for lines with score by innings data
        parts = line.strip().split()
        if len(parts) >= 13:  # At least 9 innings + R H E LOB
            try:
                # Try to extract 9 inning scores
                innings = [int(parts[i]) for i in range(1, 10) if parts[i].isdigit()]
                if len(innings) == 9:
                    return innings
            except (ValueError, IndexError):
                continue
    return innings


def parse_player_batting_line(line: str) -> Optional[PlayerBattingStats]:
    """Parse a single player batting line from box score."""
    # Pattern: # Player Pos ab r h rbi bb k po a lob
    # Example: 4 Eaton ss 5 0 0 0 0 1 3 3 5
    parts = line.strip().split()
    if len(parts) < 11:
        return None

    try:
        # Check if first part is a number (jersey number)
        if not parts[0].isdigit():
            return None

        return PlayerBattingStats(
            number=parts[0],
            name=parts[1],
            position=parts[2],
            at_bats=int(parts[3]),
            runs=int(parts[4]),
            hits=int(parts[5]),
            rbi=int(parts[6]),
            walks=int(parts[7]),
            strikeouts=int(parts[8]),
            put_outs=int(parts[9]),
            assists=int(parts[10]),
            left_on_base=int(parts[11]) if len(parts) > 11 else 0
        )
    except (ValueError, IndexError):
        return None


def parse_pitcher_line(line: str) -> Optional[PitcherStats]:
    """Parse a single pitcher stats line."""
    # Pattern: # Name ip h r er bb k bf ab np
    # Example: 35 Barbery 5.0 6 3 1 1 2 23 22 79
    parts = line.strip().split()
    if len(parts) < 10:
        return None

    try:
        if not parts[0].isdigit():
            return None

        return PitcherStats(
            number=parts[0],
            name=parts[1],
            innings_pitched=float(parts[2]),
            hits=int(parts[3]),
            runs=int(parts[4]),
            earned_runs=int(parts[5]),
            walks=int(parts[6]),
            strikeouts=int(parts[7]),
            batters_faced=int(parts[8]),
            at_bats=int(parts[9]),
            pitches=int(parts[10]) if len(parts) > 10 else 0
        )
    except (ValueError, IndexError):
        return None


def extract_game_notes(text: str) -> dict:
    """Extract additional game statistics from the notes section.

    Parses both format A (e.g., "HR - Player (count)") and format B (e.g., "HR: Player (count)")
    """
    notes = {
        "errors": [],        # E - Player
        "double_plays": {},  # DP - Team count
        "doubles": [],       # 2B - Player (season)
        "triples": [],       # 3B - Player (season)
        "home_runs": [],     # HR - Player count (season)
        "stolen_bases": [],  # SB - Player
        "caught_stealing": [], # CS - Player
        "hit_by_pitch": [],  # HBP - Player (season)
        "intentional_walks": [], # IBB - Player
        "strikeouts_looking": [], # KL - Player
        "grounded_into_dp": [], # GDP - Player
        "wild_pitches": [],  # WP - Player
        "passed_balls": [],  # PB - Player
        "hit_batters": [],   # HB - Pitcher
        "balks": [],         # BK - Pitcher
        "win": None,         # Win - Player (record)
        "loss": None,        # Loss - Player (record)
        "save": None,        # Save - Player (count) or None
    }

    # Extract errors: E - Player1 ; Player2 ; or E: Player
    errors_match = re.search(r'E\s*[-:]\s*([^;]+(?:;\s*[^;]+)*?)(?:;?\s*DP|;?\s*$|\n)', text)
    if errors_match:
        errors_str = errors_match.group(1)
        notes["errors"] = [e.strip() for e in errors_str.split(';') if e.strip() and 'DP' not in e]

    # Extract double plays: DP - Team1 X or DP: X
    dp_match = re.search(r'DP\s*[-:]\s*(\d+|[^.]+?)(?:\.|$|\n)', text)
    if dp_match:
        dp_str = dp_match.group(1).strip()
        if dp_str.isdigit():
            notes["double_plays"]["count"] = int(dp_str)
        else:
            for dp in dp_str.split(';'):
                parts = dp.strip().rsplit(' ', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    notes["double_plays"][parts[0].strip()] = int(parts[1])

    # Extract doubles: 2B - Player (season) ; or 2B: Player (count)
    # Use a more restrictive pattern that stops at newline
    # Common stat prefixes to filter out
    stat_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E|3B|HR)\b'
    doubles_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E|3B|HR)\b'

    # Use findall to capture ALL 2B lines (there may be multiple, one per team)
    doubles_matches = re.findall(r'^2B\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    for doubles_line in doubles_matches:
        for item in doubles_line.split(';'):
            item = item.strip()
            # Skip items that are clearly not doubles
            if item and not re.match(doubles_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    # Skip if player name looks like a stat prefix
                    if not re.match(doubles_prefixes, player_name, re.IGNORECASE):
                        notes["doubles"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })
                elif item and not re.match(doubles_prefixes, item, re.IGNORECASE):
                    notes["doubles"].append({"player": item, "game_count": 1, "season_total": None})

    # Extract triples: 3B - Player count (season) ;
    # Use findall to capture ALL 3B lines (there may be multiple, one per team)
    triples_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E|2B|HR)\b'
    triples_matches = re.findall(r'^3B\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    for triples_line in triples_matches:
        for item in triples_line.split(';'):
            item = item.strip()
            if item and not re.match(triples_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    if not re.match(triples_prefixes, player_name, re.IGNORECASE):
                        notes["triples"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })
                elif item and not re.match(triples_prefixes, item, re.IGNORECASE):
                    notes["triples"].append({"player": item, "game_count": 1, "season_total": None})

    # Extract home runs: HR - Player count (season) ; or HR: Player (count)
    # Use findall to capture ALL HR lines (there may be multiple, one per team)
    hr_matches = re.findall(r'^HR\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    for hr_line in hr_matches:
        for item in hr_line.split(';'):
            item = item.strip()
            # Skip items that are clearly not home runs (SH, SF, HBP, CS, SB, etc.)
            # Use word boundary \b to catch formats like "HBP - Player" or "SF Player"
            stat_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E)\b'
            if item and not re.match(stat_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    # Skip if player name looks like a stat prefix
                    if not re.match(stat_prefixes, player_name, re.IGNORECASE):
                        notes["home_runs"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })

    # Extract stolen bases: SB - Player count (season) ;
    # Use findall to capture ALL SB lines (there may be multiple, one per team)
    sb_prefixes = r'^(CS|GDP|LOB|DP|WP|PB|BK|IBB|E)\b'
    sb_matches = re.findall(r'^SB\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    for sb_line in sb_matches:
        for item in sb_line.split(';'):
            item = item.strip()
            if item and 'CS' not in item and not re.match(sb_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    if not re.match(sb_prefixes, player_name, re.IGNORECASE):
                        notes["stolen_bases"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })
                elif item and not re.match(sb_prefixes, item, re.IGNORECASE):
                    notes["stolen_bases"].append({"player": item, "game_count": 1, "season_total": None})

    # Extract caught stealing: CS - Player (count) ; (single line only)
    cs_match = re.search(r'^CS\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if cs_match:
        for item in cs_match.group(1).split(';'):
            item = item.strip()
            if item:
                notes["caught_stealing"].append(item)

    # Extract hit by pitch (batters): HBP - Player (count) ; or HBP: Player (count)
    # Note: Format B also has "HBP:" for pitchers who hit batters
    hbp_match = re.search(r'^HBP\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if hbp_match:
        for item in hbp_match.group(1).split(';'):
            item = item.strip()
            if item:
                notes["hit_by_pitch"].append(item)

    # Extract grounded into double play: GDP - Player ;
    gdp_match = re.search(r'^GDP\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if gdp_match:
        for item in gdp_match.group(1).split(';'):
            item = item.strip()
            if item and 'LOB' not in item:
                notes["grounded_into_dp"].append(item)

    # Extract win/loss/save - both "Win - Player (record)" and "Win: Player (record)"
    win_match = re.search(r'Win\s*[-:]\s*([^(]+)\s*\((\d+-\d+)\)', text)
    if win_match:
        notes["win"] = {"player": win_match.group(1).strip(), "record": win_match.group(2)}

    loss_match = re.search(r'Loss\s*[-:]\s*([^(]+)\s*\((\d+-\d+)\)', text)
    if loss_match:
        notes["loss"] = {"player": loss_match.group(1).strip(), "record": loss_match.group(2)}

    save_match = re.search(r'Save\s*[-:]\s*([^(]+)\s*\((\d+)\)', text)
    if save_match:
        notes["save"] = {"player": save_match.group(1).strip(), "count": int(save_match.group(2))}
    elif re.search(r'Save\s*[-:]\s*None', text):
        notes["save"] = None

    # Extract wild pitches: WP - Pitcher (count) ; (single line only)
    wp_match = re.search(r'^WP\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if wp_match:
        for item in wp_match.group(1).split(';'):
            item = item.strip()
            if item and not any(x in item for x in ['HB -', 'PB -']):
                notes["wild_pitches"].append(item)

    # Extract passed balls: PB - Player ; (single line only)
    pb_match = re.search(r'^PB\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if pb_match:
        for item in pb_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                notes["passed_balls"].append(item)

    # Extract sacrifice hits: SH - Player (count) (single line only)
    sh_match = re.search(r'^SH\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if sh_match:
        notes["sacrifice_hits"] = []
        for item in sh_match.group(1).split(';'):
            item = item.strip()
            if item:
                notes["sacrifice_hits"].append(item)

    return notes


def extract_game_metadata(text: str) -> dict:
    """Extract game metadata from PDF text."""
    metadata = {
        "date": None,
        "venue": None,
        "stadium": None,
        "city": None,
        "away_team": None,
        "away_team_rank": None,
        "away_team_record": None,
        "away_team_score": None,
        "home_team": None,
        "home_team_rank": None,
        "home_team_record": None,
        "home_team_score": None,
        "attendance": None,
        "duration": None,
        "start_time": None,
        "weather": None,
        "umpires": {}
    }

    # Extract date (format: February 20, 2018 or 2/20/2018)
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
    if date_match:
        metadata["date"] = date_match.group(1)
    else:
        date_match = re.search(r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})', text)
        if date_match:
            metadata["date"] = date_match.group(1)

    # Extract venue/stadium and city
    # Format: "at Davenport Field (Charlottesville, Va.)"
    venue_match = re.search(r'at\s+([A-Za-z\s]+(?:Field|Stadium|Park|Center|Arena|Coliseum|Complex))\s*\(([^)]+)\)', text)
    if venue_match:
        metadata["stadium"] = venue_match.group(1).strip()
        metadata["city"] = venue_match.group(2).strip()
        metadata["venue"] = f"{metadata['stadium']} ({metadata['city']})"
    else:
        # Fallback: try simpler pattern
        venue_match = re.search(r'at\s+([^(]+)\s*\(([^)]+)\)', text)
        if venue_match:
            metadata["stadium"] = venue_match.group(1).strip()
            metadata["city"] = venue_match.group(2).strip()
            metadata["venue"] = f"{metadata['stadium']} ({metadata['city']})"

    # Extract teams and scores - look for box score header format
    # "VMI 9 (2-2)" or "#18 Virginia 4 (2-2)" on same line
    # Also handles "VMI 9 (2-2) Virginia 4 (2-2)" format
    box_header = re.search(r'(#\d+\s+)?([A-Za-z]+)\s+(\d+)\s+\((\d+-\d+)\)\s+(#\d+\s+)?([A-Za-z]+)\s+(\d+)\s+\((\d+-\d+)\)', text)
    if box_header:
        # Away team (first)
        metadata["away_team_rank"] = box_header.group(1).strip() if box_header.group(1) else None
        metadata["away_team"] = box_header.group(2).strip()
        metadata["away_team_score"] = int(box_header.group(3))
        metadata["away_team_record"] = box_header.group(4)

        # Home team (second)
        metadata["home_team_rank"] = box_header.group(5).strip() if box_header.group(5) else None
        metadata["home_team"] = box_header.group(6).strip()
        metadata["home_team_score"] = int(box_header.group(7))
        metadata["home_team_record"] = box_header.group(8)
    else:
        # Fallback: look for separate patterns
        team_pattern = r'(#\d+\s+)?([A-Za-z\s\.]+?)\s+(\d+)\s+\((\d+-\d+)\)'
        teams = re.findall(team_pattern, text[:1000])

        if len(teams) >= 2:
            metadata["away_team_rank"] = teams[0][0].strip() if teams[0][0] else None
            metadata["away_team"] = teams[0][1].strip()
            metadata["away_team_score"] = int(teams[0][2])
            metadata["away_team_record"] = teams[0][3]

            metadata["home_team_rank"] = teams[1][0].strip() if teams[1][0] else None
            metadata["home_team"] = teams[1][1].strip()
            metadata["home_team_score"] = int(teams[1][2])
            metadata["home_team_record"] = teams[1][3]

    # Also look for title format: "VMI at Virginia" to confirm home/away
    matchup = re.search(r'^([A-Za-z]+)\s+at\s+(#?\d*\s*[A-Za-z]+)', text, re.MULTILINE)
    if matchup:
        away_name = matchup.group(1).strip()
        home_match = matchup.group(2).strip()
        # Check if home team has a rank
        home_rank_match = re.match(r'(#\d+)\s+(.+)', home_match)
        if home_rank_match:
            if not metadata["home_team_rank"]:
                metadata["home_team_rank"] = home_rank_match.group(1)

    # Look for rankings in page 1 format: "#18 Virginia" on its own line
    # Check for away team rank
    if not metadata["away_team_rank"] and metadata["away_team"]:
        away_rank = re.search(rf'(#\d+)\s+{re.escape(metadata["away_team"])}', text)
        if away_rank:
            metadata["away_team_rank"] = away_rank.group(1)

    # Check for home team rank
    if not metadata["home_team_rank"] and metadata["home_team"]:
        home_rank = re.search(rf'(#\d+)\s+{re.escape(metadata["home_team"])}', text)
        if home_rank:
            metadata["home_team_rank"] = home_rank.group(1)

    # Extract attendance
    attendance_match = re.search(r'Attendance:\s*([\d,]+)', text)
    if attendance_match:
        metadata["attendance"] = int(attendance_match.group(1).replace(',', ''))

    # Extract duration
    duration_match = re.search(r'Duration:\s*([\d:]+)', text)
    if duration_match:
        metadata["duration"] = duration_match.group(1)

    # Extract start time
    start_match = re.search(r'Start:\s*(\d{1,2}:\d{2}\s*[AP]M)', text)
    if start_match:
        metadata["start_time"] = start_match.group(1)

    # Extract weather
    weather_match = re.search(r'Weather:\s*(.+?)(?:\n|$)', text)
    if weather_match:
        metadata["weather"] = weather_match.group(1).strip()

    # Extract umpires
    umpires_match = re.search(r'Umpires\s*-\s*HP:\s*([^;]+);\s*1B:\s*([^;]+);\s*2B:\s*([^;]+);\s*3B:\s*([^.\n]+)', text)
    if umpires_match:
        metadata["umpires"] = {
            "home_plate": umpires_match.group(1).strip(),
            "first_base": umpires_match.group(2).strip(),
            "second_base": umpires_match.group(3).strip(),
            "third_base": umpires_match.group(4).strip()
        }

    # Venue-based home/away validation
    # If venue/city contains one team's name but not the other, that team should be home
    metadata["_teams_swapped"] = False
    venue = metadata.get("venue", "") or ""
    city = metadata.get("city", "") or ""
    venue_city = (venue + " " + city).lower()
    away_team = (metadata.get("away_team") or "").lower()
    home_team = (metadata.get("home_team") or "").lower()

    # Map team names to their home cities/venues
    team_home_cities = {
        'virginia': ['charlottesville', 'davenport'],
        'california': ['berkeley'],
        'stanford': ['stanford', 'palo alto', 'sunken diamond'],
        'san francisco': ['san francisco', 'benedetti'],
        'ucla': ['los angeles', 'jackie robinson'],
        'usc': ['los angeles', 'dedeaux'],
        'arizona': ['tucson', 'hi corbett'],
        'arizona state': ['tempe', 'phoenix municipal'],
        'florida': ['gainesville'],
        'lsu': ['baton rouge', 'alex box'],
        'texas': ['austin', 'disch-falk'],
        'vanderbilt': ['nashville', 'hawkins'],
        'tennessee': ['knoxville', 'lindsey nelson'],
        'nc state': ['raleigh', 'doak'],
        'north carolina': ['chapel hill', 'boshamer'],
        'wake forest': ['winston-salem'],
        'clemson': ['clemson'],
        'georgia': ['athens', 'foley'],
        'arkansas': ['fayetteville', 'baum'],
        'ole miss': ['oxford', 'swayze'],
        'mississippi state': ['starkville', 'dudy noble'],
        'oregon state': ['corvallis', 'goss'],
    }

    if away_team and home_team and venue_city:
        # Check if venue suggests teams should be swapped
        away_home_cities = team_home_cities.get(away_team, [away_team])
        home_home_cities = team_home_cities.get(home_team, [home_team])

        away_in_venue = any(city_name in venue_city for city_name in away_home_cities)
        home_in_venue = any(city_name in venue_city for city_name in home_home_cities)

        # Also check if team name is directly in venue
        if not away_in_venue:
            away_in_venue = away_team in venue_city
        if not home_in_venue:
            home_in_venue = home_team in venue_city

        if away_in_venue and not home_in_venue:
            # Away team's venue - they should be home, swap!
            metadata["_teams_swapped"] = True

    return metadata


VALID_POSITIONS = {'ss', 'cf', 'rf', 'lf', '1b', '2b', '3b', 'c', 'p', 'dh', 'ph', 'ph/ss', 'ph/lf', 'ph/1b', 'ph/rf', 'ph/cf', 'ph/3b', 'ph/2b', 'ph/c', 'ph/dh', 'pr', 'pr/ss', 'pr/lf', 'pr/rf'}


def find_player_boundary(parts: list, start_idx: int) -> int:
    """Find where the next player's stats start in a combined line.

    Looks for pattern: jersey_number, name(s), position, then 9 numeric stats.
    Returns the index of the next jersey number, or -1 if not found.
    """
    # After the stats (9 numbers), look for a new jersey number
    # We need to count 9 numeric stats after the position
    for i in range(start_idx, len(parts)):
        if not parts[i].isdigit():
            continue
        # This might be a jersey number - check if there's a position within next 3 fields
        for j in range(i + 1, min(i + 4, len(parts))):
            if parts[j].lower() in VALID_POSITIONS:
                # Found position - verify this is a valid player start
                # Check if there are 9 numbers after the position
                pos_idx = j
                remaining = parts[pos_idx + 1:]
                if len(remaining) >= 9:
                    try:
                        # Try to parse the 9 stats
                        [int(remaining[k]) for k in range(9)]
                        return i
                    except (ValueError, IndexError):
                        continue
    return -1


def parse_side_by_side_batting_line(line: str) -> tuple:
    """Parse a side-by-side batting line containing both teams' stats.

    Format: # Name Pos ab r h rbi bb k po a lob # Name Pos ab r h rbi bb k po a lob
    Example: 4 Eaton ss 5 0 0 0 0 1 3 3 5 31 McCarthy, J. cf 5 0 0 0 0 1 1 0 2

    Names may contain commas and spaces (e.g., "McCarthy, J.").

    Returns tuple of (away_player, home_player) or (None, None) if not parseable.
    """
    parts = line.strip().split()
    if len(parts) < 22:  # Need at least 11 fields per team (with simple names)
        return (None, None)

    try:
        # First, find the away player's position
        away_pos_idx = None
        for i in range(1, min(5, len(parts))):  # Position should be in first few fields
            if parts[i].lower() in VALID_POSITIONS:
                away_pos_idx = i
                break

        if away_pos_idx is None:
            return (None, None)

        # Away player stats are at indices: pos_idx+1 to pos_idx+9
        # Then LOB is at pos_idx+10 (index relative to position)
        # So home player starts after 9 stats following position

        # Parse away player
        away_number = parts[0]
        away_name = ' '.join(parts[1:away_pos_idx])  # Join name parts
        away_position = parts[away_pos_idx]
        stats_start = away_pos_idx + 1

        away_stats = [int(parts[stats_start + k]) for k in range(9)]

        away_player = PlayerBattingStats(
            number=away_number,
            name=away_name,
            position=away_position,
            at_bats=away_stats[0],
            runs=away_stats[1],
            hits=away_stats[2],
            rbi=away_stats[3],
            walks=away_stats[4],
            strikeouts=away_stats[5],
            put_outs=away_stats[6],
            assists=away_stats[7],
            left_on_base=away_stats[8]
        )

        # Home player starts after away player's stats
        home_start = stats_start + 9  # Index right after away player's LOB

        if home_start >= len(parts):
            return (away_player, None)

        # Find home player's position
        home_pos_idx = None
        for i in range(home_start + 1, min(home_start + 5, len(parts))):
            if parts[i].lower() in VALID_POSITIONS:
                home_pos_idx = i
                break

        if home_pos_idx is None:
            return (away_player, None)

        # Parse home player
        home_number = parts[home_start]
        home_name = ' '.join(parts[home_start + 1:home_pos_idx])
        home_position = parts[home_pos_idx]
        home_stats_start = home_pos_idx + 1

        # Check if we have enough stats
        if home_stats_start + 9 > len(parts):
            return (away_player, None)

        home_stats = [int(parts[home_stats_start + k]) for k in range(9)]

        home_player = PlayerBattingStats(
            number=home_number,
            name=home_name,
            position=home_position,
            at_bats=home_stats[0],
            runs=home_stats[1],
            hits=home_stats[2],
            rbi=home_stats[3],
            walks=home_stats[4],
            strikeouts=home_stats[5],
            put_outs=home_stats[6],
            assists=home_stats[7],
            left_on_base=home_stats[8]
        )

        return (away_player, home_player)
    except (ValueError, IndexError):
        return (None, None)


def parse_single_pitcher(parts: list) -> Optional[PitcherStats]:
    """Parse a single pitcher's stats from a list of parts.

    Expected format: # Name ip h r er bb k bf ab np
    Name may contain multiple parts (e.g., "McGarry, G.")
    """
    if len(parts) < 10:
        return None

    try:
        # Find the IP field (first float-like value after jersey number)
        ip_idx = None
        for i in range(1, min(5, len(parts))):
            try:
                float(parts[i])
                ip_idx = i
                break
            except ValueError:
                continue

        if ip_idx is None:
            return None

        # Name is everything between jersey number and IP
        number = parts[0]
        name = ' '.join(parts[1:ip_idx])

        # Stats start at IP
        return PitcherStats(
            number=number,
            name=name,
            innings_pitched=float(parts[ip_idx]),
            hits=int(parts[ip_idx + 1]),
            runs=int(parts[ip_idx + 2]),
            earned_runs=int(parts[ip_idx + 3]),
            walks=int(parts[ip_idx + 4]),
            strikeouts=int(parts[ip_idx + 5]),
            batters_faced=int(parts[ip_idx + 6]),
            at_bats=int(parts[ip_idx + 7]),
            pitches=int(parts[ip_idx + 8])
        )
    except (ValueError, IndexError):
        return None


def parse_side_by_side_pitching_line(line: str) -> tuple:
    """Parse a side-by-side pitching line containing both teams' stats.

    Format: # Name ip h r er bb k bf ab np # Name ip h r er bb k bf ab np
    Names may contain commas (e.g., "McGarry, G.")

    May also contain only one team's pitcher (e.g., when teams have different numbers of pitchers).

    Returns tuple of (away_pitcher, home_pitcher) or (None, None) if not parseable.
    """
    parts = line.strip().split()
    if len(parts) < 10:
        return (None, None)

    try:
        # First, find the away pitcher's IP (first float after jersey number)
        away_ip_idx = None
        for i in range(1, min(5, len(parts))):
            try:
                float(parts[i])
                away_ip_idx = i
                break
            except ValueError:
                continue

        if away_ip_idx is None:
            return (None, None)

        # Away pitcher stats end 9 values after IP
        away_end = away_ip_idx + 9

        # Check if there's a home pitcher
        if away_end >= len(parts):
            # Only away pitcher
            away_pitcher = parse_single_pitcher(parts)
            return (away_pitcher, None)

        # Check if remaining parts form a valid home pitcher
        home_parts = parts[away_end:]
        if len(home_parts) < 10:
            # Not enough for home pitcher, just parse away
            away_pitcher = parse_single_pitcher(parts[:away_end])
            return (away_pitcher, None)

        # Check if home_parts starts with a jersey number
        if not home_parts[0].isdigit():
            away_pitcher = parse_single_pitcher(parts[:away_end])
            return (away_pitcher, None)

        # Parse both pitchers
        away_pitcher = parse_single_pitcher(parts[:away_end])
        home_pitcher = parse_single_pitcher(home_parts)

        return (away_pitcher, home_pitcher)
    except (ValueError, IndexError):
        return (None, None)


def parse_box_score_from_tables(pdf_page) -> dict:
    """Parse box score using text parsing for side-by-side layout."""
    result = {
        "away_batting": [],
        "home_batting": [],
        "away_pitching": [],
        "home_pitching": [],
        "line_score": {
            "away_innings": [],
            "home_innings": []
        }
    }

    text = pdf_page.extract_text() or ""
    lines = text.split('\n')

    in_batting_section = False
    in_pitching_section = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect batting section header (case-insensitive)
        if '# player pos ab' in stripped.lower():
            in_batting_section = True
            in_pitching_section = False
            continue

        # Detect pitching section header (format: "VMI ip h r er bb k bf ab np VA ip...")
        if re.match(r'^VMI\s+ip\s+h\s+r', stripped, re.IGNORECASE) or 'ip h r er bb k' in stripped.lower():
            in_batting_section = False
            in_pitching_section = True
            continue

        # Detect end of sections
        if 'Score by Innings' in stripped:
            in_batting_section = False
            in_pitching_section = False

        # Parse batting lines
        if in_batting_section:
            # Check for Totals line - but it might also contain last home player
            # Format: "Totals 36 9 12 8 10 5 27 9 11 18 Novak, J. 3b 2 1 1 0 2 0 1 3 0"
            if stripped.startswith('Totals'):
                # Try to extract last home player from mixed line
                parts = stripped.split()
                # Skip "Totals" and the 9 numeric totals, then look for remaining player
                if len(parts) > 10:
                    # Check if there's a player after the totals
                    remaining = ' '.join(parts[10:])  # Skip Totals + 9 stat columns
                    if remaining:
                        # Try to parse the remaining part as a single player
                        home_player = parse_player_batting_line(remaining)
                        if home_player:
                            result["home_batting"].append(asdict(home_player))
                in_batting_section = False
                continue

            # Try to parse side-by-side batting line
            away_player, home_player = parse_side_by_side_batting_line(stripped)
            if away_player:
                result["away_batting"].append(asdict(away_player))
            if home_player:
                result["home_batting"].append(asdict(home_player))

        # Parse pitching lines
        if in_pitching_section:
            # Check for end markers
            if stripped.startswith('Win -') or stripped.startswith('WP -'):
                in_pitching_section = False
                continue

            # Try side-by-side pitching line first
            away_pitcher, home_pitcher = parse_side_by_side_pitching_line(stripped)
            if away_pitcher and home_pitcher:
                # Both teams have pitchers on this line
                result["away_pitching"].append(asdict(away_pitcher))
                result["home_pitching"].append(asdict(home_pitcher))
            elif away_pitcher and not home_pitcher:
                # Only one pitcher on line - after side-by-side lines end,
                # remaining single pitchers belong to home team
                # (because away team exhausted their pitchers first in the PDF layout)
                # Check if we already have home pitchers (meaning we've seen side-by-side lines)
                if result["home_pitching"]:
                    result["home_pitching"].append(asdict(away_pitcher))
                else:
                    result["away_pitching"].append(asdict(away_pitcher))

        # Parse score by innings
        if 'Score by Innings' in stripped:
            for j in range(i+1, min(i+4, len(lines))):
                score_line = lines[j].strip()
                parts = score_line.split()
                if len(parts) >= 13:
                    team_name = parts[0]
                    try:
                        innings = [int(parts[k]) for k in range(1, 10)]
                        if team_name == 'VMI':
                            result["line_score"]["away_innings"] = innings
                        elif team_name == 'Virginia':
                            result["line_score"]["home_innings"] = innings
                    except ValueError:
                        pass

    return result


def parse_box_score_page_text(text: str) -> dict:
    """Parse the box score page from text to extract player and pitching stats."""
    result = {
        "away_batting": [],
        "home_batting": [],
        "away_pitching": [],
        "home_pitching": [],
        "line_score": {
            "away_innings": [],
            "home_innings": []
        }
    }

    lines = text.split('\n')
    current_section = None
    found_away_batting = False
    found_home_batting = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect section headers - look for team name with record
        # Away team header: "VMI 9 (2-2)"
        if re.match(r'^VMI\s+\d+\s*\(\d+-\d+\)', stripped):
            current_section = "away_batting"
            found_away_batting = True
            continue
        # Home team header: "Virginia 4 (2-2)"
        elif re.match(r'^Virginia\s+\d+\s*\(\d+-\d+\)', stripped):
            current_section = "home_batting"
            found_home_batting = True
            continue
        # Also detect from header row patterns
        elif 'VMI' in stripped and '(' in stripped and 'ip' not in stripped.lower() and not found_away_batting:
            current_section = "away_batting"
            found_away_batting = True
            continue
        elif 'Virginia' in stripped and '(' in stripped and 'ip' not in stripped.lower() and not found_home_batting:
            current_section = "home_batting"
            found_home_batting = True
            continue

        # Parse player batting stats
        if current_section in ["away_batting", "home_batting"]:
            player = parse_player_batting_line(stripped)
            if player:
                if current_section == "away_batting":
                    result["away_batting"].append(asdict(player))
                else:
                    result["home_batting"].append(asdict(player))
            elif 'Totals' in stripped:
                current_section = None

        # Parse pitching section - look for "VMI ip h r" or "VA ip h r" patterns
        if re.match(r'^VMI\s+ip\s+h\s+r', stripped, re.IGNORECASE):
            current_section = "away_pitching"
            continue
        elif re.match(r'^VA\s+ip\s+h\s+r', stripped, re.IGNORECASE):
            current_section = "home_pitching"
            continue

        if current_section in ["away_pitching", "home_pitching"]:
            pitcher = parse_pitcher_line(stripped)
            if pitcher:
                if current_section == "away_pitching":
                    result["away_pitching"].append(asdict(pitcher))
                else:
                    result["home_pitching"].append(asdict(pitcher))
            # Check for end of pitching section
            if stripped.startswith('Win -') or stripped.startswith('WP -'):
                current_section = None

        # Parse score by innings
        if 'Score by Innings' in stripped:
            for j in range(i+1, min(i+4, len(lines))):
                score_line = lines[j].strip()
                parts = score_line.split()
                if len(parts) >= 13 and parts[0] == 'VMI':
                    try:
                        result["line_score"]["away_innings"] = [int(parts[k]) for k in range(1, 10)]
                    except ValueError:
                        pass
                elif len(parts) >= 13 and parts[0] == 'Virginia':
                    try:
                        result["line_score"]["home_innings"] = [int(parts[k]) for k in range(1, 10)]
                    except ValueError:
                        pass

    return result


def parse_box_score_page(text: str) -> dict:
    """Parse the box score page to extract player and pitching stats (legacy wrapper)."""
    return parse_box_score_page_text(text)


def detect_pdf_format(text: str) -> str:
    """Detect which PDF format we're dealing with.

    Returns:
        'format_a': Original format (VMI at Virginia style, side-by-side stats with jersey #)
        'format_a_no_num': Format A variant without jersey numbers
        'format_b': Newer format (Team (record) -vs- Team (record) style)
    """
    if '-vs-' in text:
        return 'format_b'
    # Check for column headers
    if 'Player AB R H RBI BB SO LOB' in text:
        return 'format_b'
    if '# player pos ab r h rbi bb k po a lob' in text.lower():
        return 'format_a'
    # Format A without jersey numbers: "Player ab r h rbi bb k po a lob"
    if re.search(r'Player\s+ab\s+r\s+h\s+rbi\s+bb\s+k\s+po\s+a\s+lob', text, re.IGNORECASE):
        return 'format_a_no_num'
    if ' at ' in text.lower() or ' @ ' in text:
        # Check if it has jersey numbers
        if '# Player Pos' in text:
            return 'format_a'
        return 'format_a_no_num'
    return 'format_a'  # Default


def parse_format_a_no_num_batting_line(line: str) -> tuple:
    """Parse side-by-side batting line without jersey numbers.

    Format: Name Pos ab r h rbi bb k po a lob Name Pos ab r h rbi bb k po a lob
    Example: Harris cf 4 1 0 0 1 0 2 0 0 Clement, E. 2b 5 1 1 0 0 0 4 2 0
    """
    parts = line.strip().split()
    if len(parts) < 20:
        return (None, None)

    try:
        # Find away player's position
        away_pos_idx = None
        for i in range(1, min(5, len(parts))):
            if parts[i].lower() in VALID_POSITIONS:
                away_pos_idx = i
                break

        if away_pos_idx is None:
            return (None, None)

        # Parse away player (name, pos, then 9 stats)
        away_name = ' '.join(parts[:away_pos_idx])
        away_pos = parts[away_pos_idx]
        stats_start = away_pos_idx + 1
        away_stats = [int(parts[stats_start + k]) for k in range(9)]

        away_player = PlayerBattingStats(
            number="",
            name=away_name,
            position=away_pos,
            at_bats=away_stats[0],
            runs=away_stats[1],
            hits=away_stats[2],
            rbi=away_stats[3],
            walks=away_stats[4],
            strikeouts=away_stats[5],
            put_outs=away_stats[6],
            assists=away_stats[7],
            left_on_base=away_stats[8]
        )

        # Home player starts after away stats
        home_start = stats_start + 9
        if home_start >= len(parts):
            return (away_player, None)

        # Find home player's position
        home_pos_idx = None
        for i in range(home_start + 1, min(home_start + 5, len(parts))):
            if parts[i].lower() in VALID_POSITIONS:
                home_pos_idx = i
                break

        if home_pos_idx is None:
            return (away_player, None)

        home_name = ' '.join(parts[home_start:home_pos_idx])
        home_pos = parts[home_pos_idx]
        home_stats_start = home_pos_idx + 1

        if home_stats_start + 9 > len(parts):
            return (away_player, None)

        home_stats = [int(parts[home_stats_start + k]) for k in range(9)]

        home_player = PlayerBattingStats(
            number="",
            name=home_name,
            position=home_pos,
            at_bats=home_stats[0],
            runs=home_stats[1],
            hits=home_stats[2],
            rbi=home_stats[3],
            walks=home_stats[4],
            strikeouts=home_stats[5],
            put_outs=home_stats[6],
            assists=home_stats[7],
            left_on_base=home_stats[8]
        )

        return (away_player, home_player)
    except (ValueError, IndexError):
        return (None, None)


def parse_format_a_no_num_box_score(pdf_page) -> dict:
    """Parse box score from format A without jersey numbers."""
    result = {
        "away_batting": [],
        "home_batting": [],
        "away_pitching": [],
        "home_pitching": [],
        "line_score": {
            "away_innings": [],
            "home_innings": []
        }
    }

    text = pdf_page.extract_text() or ""
    lines = text.split('\n')

    in_batting_section = False
    in_pitching_section = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect batting header (without #)
        if re.search(r'^Player\s+ab\s+r\s+h\s+rbi', stripped, re.IGNORECASE):
            in_batting_section = True
            in_pitching_section = False
            continue

        # Detect pitching header
        if re.match(r'^[A-Z]{2,3}\s+ip\s+h\s+r', stripped, re.IGNORECASE):
            in_batting_section = False
            in_pitching_section = True
            continue

        if 'Score by Innings' in stripped:
            in_batting_section = False
            in_pitching_section = False

        # Parse batting
        if in_batting_section:
            if stripped.startswith('Totals'):
                in_batting_section = False
                continue

            away_player, home_player = parse_format_a_no_num_batting_line(stripped)
            if away_player:
                result["away_batting"].append(asdict(away_player))
            if home_player:
                result["home_batting"].append(asdict(home_player))

        # Parse pitching (use existing side-by-side logic)
        if in_pitching_section:
            if stripped.startswith('Win -') or stripped.startswith('WP -'):
                in_pitching_section = False
                continue

            away_pitcher, home_pitcher = parse_side_by_side_pitching_line(stripped)
            if away_pitcher and home_pitcher:
                result["away_pitching"].append(asdict(away_pitcher))
                result["home_pitching"].append(asdict(home_pitcher))
            elif away_pitcher:
                if result["home_pitching"]:
                    result["home_pitching"].append(asdict(away_pitcher))
                else:
                    result["away_pitching"].append(asdict(away_pitcher))

        # Parse line score
        if 'Score by Innings' in stripped:
            for j in range(i+1, min(i+4, len(lines))):
                score_line = lines[j].strip()
                parts = score_line.split()
                if len(parts) >= 13:
                    team_name = parts[0]
                    try:
                        innings = [int(parts[k]) if parts[k] != 'X' else 0 for k in range(1, 10)]
                        if not result["line_score"]["away_innings"]:
                            result["line_score"]["away_innings"] = innings
                        elif not result["line_score"]["home_innings"]:
                            result["line_score"]["home_innings"] = innings
                    except ValueError:
                        pass

    return result


def parse_format_b_batting_line(line: str, has_position: bool = False) -> Optional[PlayerBattingStats]:
    """Parse a batting line from format B (newer format).

    Format: Name Position AB R H RBI BB SO LOB
    or: Name AB R H RBI BB SO LOB (no position)

    Example: Eddie Park cf 5 1 1 0 0 1 1
    """
    stripped = line.strip()

    # Skip game note lines that got mixed in with batting data
    # These start with stat prefixes like "SH:", "2B:", "CS:", "E:", etc.
    game_note_prefixes = ('SH:', 'SF:', '2B:', '3B:', 'HR:', 'SB:', 'CS:', 'E:',
                          'HBP:', 'IBB:', 'WP:', 'PB:', 'BK:', 'DP:', 'LOB:',
                          'Totals', 'TOTALS')
    if any(stripped.startswith(prefix) for prefix in game_note_prefixes):
        return None

    # Also skip lines that contain "Totals" anywhere (merged lines)
    if 'Totals' in stripped or 'TOTALS' in stripped:
        return None

    parts = stripped.split()
    if len(parts) < 7:
        return None

    try:
        # Find where the stats begin (first sequence of numbers)
        stats_start = None
        for i in range(len(parts)):
            # Look for a sequence of numbers (at least 5 in a row for AB R H RBI BB)
            if parts[i].isdigit():
                # Check if next few are also digits
                if i + 4 < len(parts):
                    try:
                        [int(parts[i+j]) for j in range(5)]
                        stats_start = i
                        break
                    except ValueError:
                        continue

        if stats_start is None or stats_start < 1:
            return None

        # Check if there's a position before stats
        potential_pos = parts[stats_start - 1].lower()
        if potential_pos in VALID_POSITIONS:
            name = ' '.join(parts[:stats_start - 1])
            position = parts[stats_start - 1]
        else:
            name = ' '.join(parts[:stats_start])
            position = ""

        # Parse stats: AB R H RBI BB SO LOB
        stats = [int(parts[stats_start + i]) for i in range(7)]

        return PlayerBattingStats(
            number="",  # Format B doesn't have jersey numbers
            name=name,
            position=position,
            at_bats=stats[0],
            runs=stats[1],
            hits=stats[2],
            rbi=stats[3],
            walks=stats[4],
            strikeouts=stats[5],
            put_outs=0,  # Not in format B
            assists=0,   # Not in format B
            left_on_base=stats[6]
        )
    except (ValueError, IndexError):
        return None


def parse_format_b_pitching_line(line: str) -> Optional[PitcherStats]:
    """Parse a pitching line from format B.

    Format: Name (W/L, record) IP H R ER BB SO WP BK HBP IBB AB BF FO GO NP
    Example: Landon Stump (L, 6-2) 2.0 4 5 5 2 0 0 0 0 0 10 12 1 5 56
    """
    stripped = line.strip()
    if not stripped or stripped.lower().startswith('totals'):
        return None

    # Skip header lines
    if 'IP H R' in stripped.upper():
        return None

    try:
        # Find IP value - look for pattern like "X.X" or single digit followed by numbers
        # IP is the first numeric value that looks like innings (0-9.0-9.2)
        ip_match = re.search(r'\s(\d+\.\d)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', stripped)
        if not ip_match:
            return None

        # Name is everything before the IP value
        ip_start = ip_match.start(1)
        name = stripped[:ip_start].strip()

        # Remove win/loss record from name if present: "(W, 5-1)" or "(L, 6-2)" or "(S, 1)"
        name = re.sub(r'\s*\([WLS],?\s*[\d-]+\)\s*$', '', name)

        # Parse stats: IP H R ER BB SO (positions 1-6 of match)
        ip = float(ip_match.group(1))
        h = int(ip_match.group(2))
        r = int(ip_match.group(3))
        er = int(ip_match.group(4))
        bb = int(ip_match.group(5))
        so = int(ip_match.group(6))

        # Try to get additional stats (WP BK HBP IBB AB BF FO GO NP)
        remaining = stripped[ip_match.end(6):].strip().split()
        bf = 0
        ab = 0
        pitches = 0
        if len(remaining) >= 9:
            # WP BK HBP IBB AB BF FO GO NP
            try:
                ab = int(remaining[4])  # AB
                bf = int(remaining[5])  # BF
                pitches = int(remaining[8])  # NP
            except (ValueError, IndexError):
                pass

        return PitcherStats(
            number="",
            name=name,
            innings_pitched=ip,
            hits=h,
            runs=r,
            earned_runs=er,
            walks=bb,
            strikeouts=so,
            batters_faced=bf,
            at_bats=ab,
            pitches=pitches
        )
    except (ValueError, IndexError):
        return None


def parse_format_b_box_score(text: str) -> dict:
    """Parse box score from format B (newer NCAA format).

    This format has side-by-side batting stats on page 1 with headers like:
    Team1 Score  Team2 Score
    Player AB R H RBI BB SO LOB  Player AB R H RBI BB SO LOB

    Pitching format:
    Team IP H R ER BB SO WP BK HBP IBB AB BF FO GO NP
    """
    result = {
        "away_batting": [],
        "home_batting": [],
        "away_pitching": [],
        "home_pitching": [],
        "line_score": {
            "away_innings": [],
            "home_innings": []
        }
    }

    lines = text.split('\n')
    in_batting_section = False
    in_pitching_section = False
    current_pitching_team = None  # 'away' or 'home'

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect batting section header
        if 'Player AB R H RBI BB SO LOB' in stripped:
            in_batting_section = True
            in_pitching_section = False
            continue

        # Detect pitching section header - format: "Team IP H R ER BB SO..."
        pitching_header_match = re.match(r'^([A-Za-z\s]+)\s+IP\s+H\s+R\s+ER', stripped)
        if pitching_header_match:
            in_batting_section = False
            in_pitching_section = True
            team_name = pitching_header_match.group(1).strip()
            # First pitching header is away team, second is home team
            if current_pitching_team is None:
                current_pitching_team = 'away'
            else:
                current_pitching_team = 'home'
            continue

        # Detect play by play section (end of box score)
        if 'Play By Play' in stripped or 'Play-By-Play' in stripped:
            in_batting_section = False
            in_pitching_section = False
            break

        # Detect end of pitching section (Win/Loss/Save lines)
        if stripped.startswith('Win:') or stripped.startswith('Loss:') or stripped.startswith('Save:'):
            in_pitching_section = False
            continue

        # Detect score by innings
        if 'Score by Innings' in stripped:
            in_batting_section = False
            # Parse next two lines for team scores
            for j in range(i+1, min(i+4, len(lines))):
                score_line = lines[j].strip()
                parts = score_line.split()
                if len(parts) >= 12:
                    # Find where innings start (first number)
                    for k, p in enumerate(parts):
                        if p.isdigit():
                            try:
                                # Get innings (typically 9)
                                innings = []
                                for m in range(k, min(k+9, len(parts))):
                                    if parts[m].isdigit() or parts[m] == 'X':
                                        innings.append(0 if parts[m] == 'X' else int(parts[m]))
                                    else:
                                        break
                                if len(innings) >= 7:
                                    if not result["line_score"]["away_innings"]:
                                        result["line_score"]["away_innings"] = innings
                                    else:
                                        result["line_score"]["home_innings"] = innings
                            except ValueError:
                                pass
                            break

        # Parse batting lines - format B has both teams side by side
        if in_batting_section and stripped:
            # Skip totals and empty lines
            if stripped.lower().startswith('totals') or stripped.lower().startswith('player'):
                continue
            if re.match(r'^\d+ p\b', stripped.lower()):  # Pitcher line like "0 0 0 0 0 0 0"
                continue

            # Try to split line into two players
            # Look for pattern where stats end and new name begins
            parts = stripped.split()
            if len(parts) >= 14:  # Likely two players
                # Find the split point - after 7 numeric stats
                split_idx = None
                num_count = 0
                for idx, p in enumerate(parts):
                    if p.isdigit():
                        num_count += 1
                        if num_count == 7:  # After LOB
                            split_idx = idx + 1
                            break
                    elif num_count > 0 and not p.isdigit():
                        # Reset if we hit non-number before getting 7
                        num_count = 0

                if split_idx and split_idx < len(parts):
                    away_line = ' '.join(parts[:split_idx])
                    home_line = ' '.join(parts[split_idx:])

                    away_player = parse_format_b_batting_line(away_line)
                    home_player = parse_format_b_batting_line(home_line)

                    if away_player:
                        result["away_batting"].append(asdict(away_player))
                    if home_player:
                        result["home_batting"].append(asdict(home_player))
            else:
                # Single player line
                player = parse_format_b_batting_line(stripped)
                if player:
                    # Determine team based on context
                    if len(result["away_batting"]) <= len(result["home_batting"]):
                        result["away_batting"].append(asdict(player))
                    else:
                        result["home_batting"].append(asdict(player))

        # Parse pitching lines
        if in_pitching_section and stripped:
            # Skip totals line
            if stripped.lower().startswith('totals'):
                continue
            # Skip non-pitching lines (game notes, etc.)
            if any(x in stripped for x in ['HR:', 'HBP:', 'DP:', '2B:', 'SH:', 'HBP:', 'SB:']):
                in_pitching_section = False
                continue

            pitcher = parse_format_b_pitching_line(stripped)
            if pitcher:
                if current_pitching_team == 'away':
                    result["away_pitching"].append(asdict(pitcher))
                else:
                    result["home_pitching"].append(asdict(pitcher))

    return result


def extract_format_b_metadata(text: str) -> dict:
    """Extract metadata from format B PDFs."""
    metadata = {
        "date": None,
        "venue": None,
        "stadium": None,
        "city": None,
        "away_team": None,
        "away_team_rank": None,
        "away_team_record": None,
        "away_team_score": None,
        "home_team": None,
        "home_team_rank": None,
        "home_team_record": None,
        "home_team_score": None,
        "attendance": None,
        "duration": None,
        "start_time": None,
        "weather": None,
        "umpires": {}
    }

    # Format variations:
    # 1. "# 15 UCLA (48-17) -vs- # 6 LSU (50-15)" - ranked teams with W-L record
    # 2. "Arizona (16-13, 9-5 PAC-12) -vs- California (16-12, 5-9 PAC-12)" - conference record
    # 3. "Arizona (0) -vs- Coastal Carolina (0)" - single number (tournament series)
    # 4. "LMU (22-20) -vs- Saint Mary's (21-19)" - team names with apostrophes
    # Pattern handles: optional ranking, team name (including apostrophes), parenthesized record
    matchup = re.search(
        r"(?:#\s*(\d+)\s+)?([A-Za-z\s']+?)\s*\(([^)]+)\)\s*-vs-\s*(?:#\s*(\d+)\s+)?([A-Za-z\s']+?)\s*\(([^)]+)\)",
        text
    )
    if matchup:
        # Away team
        metadata["away_team_rank"] = f"#{matchup.group(1)}" if matchup.group(1) else None
        metadata["away_team"] = matchup.group(2).strip()
        metadata["away_team_record"] = matchup.group(3)

        # Home team
        metadata["home_team_rank"] = f"#{matchup.group(4)}" if matchup.group(4) else None
        metadata["home_team"] = matchup.group(5).strip()
        metadata["home_team_record"] = matchup.group(6)

    # Extract date - format: 6/17/2023 or M/D/YYYY
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
    if date_match:
        metadata["date"] = date_match.group(1)

    # Extract venue - format: "at City, State (Stadium)"
    venue_match = re.search(r'at\s+([^(]+)\s*\(([^)]+)\)', text)
    if venue_match:
        metadata["city"] = venue_match.group(1).strip()
        metadata["stadium"] = venue_match.group(2).strip()
        metadata["venue"] = f"{metadata['stadium']} ({metadata['city']})"

    # Extract scores from line like "UCLA 5 LSU 9" (appears after score by innings)
    if metadata["away_team"] and metadata["home_team"]:
        # Pattern: "Team1 X Team2 Y" on its own line
        pattern = rf'^{re.escape(metadata["away_team"])}\s+(\d+)\s+{re.escape(metadata["home_team"])}\s+(\d+)\s*$'
        score_match = re.search(pattern, text, re.MULTILINE)
        if score_match:
            metadata["away_team_score"] = int(score_match.group(1))
            metadata["home_team_score"] = int(score_match.group(2))

    # Extract attendance
    attendance_match = re.search(r'Attendance[:\s]+(\d[\d,]*)', text, re.IGNORECASE)
    if attendance_match:
        metadata["attendance"] = int(attendance_match.group(1).replace(',', ''))

    # Extract duration
    duration_match = re.search(r'Time[:\s]+(\d+:\d+)', text, re.IGNORECASE)
    if duration_match:
        metadata["duration"] = duration_match.group(1)

    # Extract start time
    start_match = re.search(r'Start[:\s]+(\d{1,2}:\d{2}\s*(?:am|pm)?)', text, re.IGNORECASE)
    if start_match:
        metadata["start_time"] = start_match.group(1)

    # Extract weather
    weather_match = re.search(r'Weather[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
    if weather_match:
        metadata["weather"] = weather_match.group(1).strip()

    # Extract umpires
    umpires_match = re.search(r'Umpires?[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
    if umpires_match:
        metadata["umpires"]["list"] = umpires_match.group(1).strip()

    return metadata


def parse_format_b_play_by_play(text: str) -> dict:
    """Parse play-by-play from format B PDFs."""
    innings = {}
    current_inning = None
    current_half = None

    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Detect team batting indicator - "Team - Top/Bottom of Xth"
        half_match = re.search(r'([A-Za-z\s]+)\s*-\s*(Top|Bottom)\s+of\s+(\d+)', stripped, re.IGNORECASE)
        if half_match:
            current_inning = int(half_match.group(3))
            current_half = "top" if half_match.group(2).lower() == "top" else "bottom"
            if current_inning not in innings:
                innings[current_inning] = {"top": [], "bottom": []}
            continue

        # Skip summary lines
        if stripped.startswith('Runs:') or stripped.startswith('No play'):
            continue

        # Parse play events
        if current_inning and current_half and stripped:
            # Extract pitch count if present
            pitch_match = re.search(r'\((\d-\d\s*[BKFSX]*)\)', stripped)
            pitch_count = pitch_match.group(1) if pitch_match else None

            # Check for RBI
            rbi_match = re.search(r'(\d+)\s*RBI', stripped)
            rbi = int(rbi_match.group(1)) if rbi_match else 0
            if ', RBI' in stripped and not rbi_match:
                rbi = 1

            # Skip if this looks like just a score line (just numbers)
            if re.match(r'^\d+\s+\d+\s*$', stripped):
                continue

            event = {
                "description": stripped,
                "pitch_count": pitch_count,
                "rbi": rbi
            }

            innings[current_inning][current_half].append(event)

    return innings


def parse_play_by_play(text: str) -> dict:
    """Parse play-by-play text into structured data."""
    innings = {}
    current_inning = None
    current_half = None
    in_scoring_summary = False

    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()

        # Detect and skip "Scoring Innings" summary section
        if 'Scoring Innings' in stripped:
            in_scoring_summary = True
            continue

        # Skip content in scoring summary section
        if in_scoring_summary:
            # Check if we've reached actual play-by-play again (new page)
            if re.match(r'^(\d+)(?:st|nd|rd|th)\s+Inning', stripped):
                in_scoring_summary = False
            else:
                continue

        # Detect inning headers
        inning_match = re.match(r'^(\d+)(?:st|nd|rd|th)\s+Inning', stripped)
        if inning_match:
            current_inning = int(inning_match.group(1))
            if current_inning not in innings:
                innings[current_inning] = {"top": [], "bottom": []}
            continue

        # Detect half-inning - format 1: "Top of 1st batting"
        if 'Top of' in stripped and 'batting' in stripped.lower():
            half_match = re.search(r'Top of (\d+)', stripped)
            if half_match:
                current_inning = int(half_match.group(1))
                if current_inning not in innings:
                    innings[current_inning] = {"top": [], "bottom": []}
            current_half = "top"
            continue
        elif 'Bottom of' in stripped and 'batting' in stripped.lower():
            half_match = re.search(r'Bottom of (\d+)', stripped)
            if half_match:
                current_inning = int(half_match.group(1))
                if current_inning not in innings:
                    innings[current_inning] = {"top": [], "bottom": []}
            current_half = "bottom"
            continue

        # Detect half-inning - format 2: "RU 1st -" or "VA 1st -" (team abbreviation + inning)
        # First occurrence of team is away (top), alternating after that
        team_inning_match = re.match(r'^([A-Z]{2,3})\s+(\d+)(?:st|nd|rd|th)\s*-', stripped)
        if team_inning_match:
            inning_num = int(team_inning_match.group(2))
            if inning_num not in innings:
                innings[inning_num] = {"top": [], "bottom": []}
            # Alternate between top and bottom based on whether we've seen this inning before
            if current_inning != inning_num:
                current_inning = inning_num
                current_half = "top"
            else:
                current_half = "bottom"
            # Don't continue - parse the rest of the line as events
            remaining = stripped[team_inning_match.end():].strip()
            if remaining and remaining != 'No play.':
                for event_text in remaining.split('.;'):
                    event_text = event_text.strip()
                    if event_text and not re.match(r'^\d+\s+R,', event_text):
                        pitch_match = re.search(r'\((\d-\d\s*[BKFS]*)\)', event_text)
                        pitch_count = pitch_match.group(1) if pitch_match else None
                        rbi_match = re.search(r'(\d+)\s*RBI', event_text)
                        rbi = int(rbi_match.group(1)) if rbi_match else 0
                        if ', RBI' in event_text and not rbi_match:
                            rbi = 1
                        innings[current_inning][current_half].append({
                            "description": event_text.rstrip('.'),
                            "pitch_count": pitch_count,
                            "rbi": rbi
                        })
            continue

        # Skip summary lines and headers
        if not stripped or 'This Inning' in stripped or stripped.startswith('Score by'):
            continue
        if re.match(r'^[A-Z]+\s+\d+\s+\d+\s+\d+\s+\d+', stripped):  # Score line
            continue
        if 'starters:' in stripped.lower():
            continue
        # Skip inning summary lines like "6 R, 4 H, 1 E, 1 LOB."
        if re.match(r'^\d+\s+R,\s+\d+\s+H,\s+\d+\s+E,\s+\d+\s+LOB', stripped):
            continue
        # Skip page headers
        if 'Play By Play' in stripped or 'at Davenport Field' in stripped:
            continue

        # Parse play events
        if current_inning and current_half and stripped:
            # Skip if line looks like inning summary "R H E L" or team starter list
            if re.match(r'^\d+/[a-z]+/', stripped):  # Starter format: 4/ss/Eaton
                continue

            # Extract pitch count if present
            pitch_match = re.search(r'\((\d-\d\s*[BKFS]*)\)', stripped)
            pitch_count = pitch_match.group(1) if pitch_match else None

            # Check for RBI
            rbi_match = re.search(r'(\d+)\s*RBI', stripped)
            rbi = int(rbi_match.group(1)) if rbi_match else 0
            if ', RBI' in stripped and not rbi_match:
                rbi = 1

            event = {
                "description": stripped,
                "pitch_count": pitch_count,
                "rbi": rbi
            }

            innings[current_inning][current_half].append(event)

    return innings


def parse_ncaab_pdf(pdf_path: str) -> dict:
    """
    Main function to parse an NCAA baseball box score PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing all parsed game data
    """
    result = {
        "metadata": {},
        "box_score": {},
        "game_notes": {},
        "play_by_play": {},
        "format": None
    }

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"

        # Detect PDF format
        pdf_format = detect_pdf_format(full_text)
        result["format"] = pdf_format

        # Extract game notes (applies to all formats)
        result["game_notes"] = extract_game_notes(full_text)

        if pdf_format == 'format_b':
            # Use format B parsers (newer NCAA format)
            result["metadata"] = extract_format_b_metadata(full_text)

            # Parse box score from page 1 (format B has everything on page 1)
            page1_text = pdf.pages[0].extract_text() or ""
            result["box_score"] = parse_format_b_box_score(page1_text)

            # Parse play-by-play (starts on page 2 for format B)
            pbp_text = ""
            for page in pdf.pages[1:]:
                page_text = page.extract_text() or ""
                pbp_text += page_text + "\n"
            result["play_by_play"] = parse_format_b_play_by_play(pbp_text)

        elif pdf_format == 'format_a_no_num':
            # Format A without jersey numbers
            result["metadata"] = extract_game_metadata(full_text)

            # Parse box score from page 2
            if len(pdf.pages) >= 2:
                result["box_score"] = parse_format_a_no_num_box_score(pdf.pages[1])

            # Parse play-by-play
            pbp_text = ""
            for page in pdf.pages[2:]:
                page_text = page.extract_text() or ""
                if 'Scoring Innings - Final' in page_text:
                    break
                pbp_text += page_text + "\n"
            result["play_by_play"] = parse_play_by_play(pbp_text)

        else:
            # Use format A parsers (original format with jersey numbers)
            result["metadata"] = extract_game_metadata(full_text)

            # Parse box score (primarily from page 2)
            if len(pdf.pages) >= 2:
                result["box_score"] = parse_box_score_from_tables(pdf.pages[1])

            # Parse play-by-play (pages 3 onward)
            pbp_text = ""
            for page in pdf.pages[2:]:
                page_text = page.extract_text() or ""
                if 'Scoring Innings - Final' in page_text:
                    break
                pbp_text += page_text + "\n"
            result["play_by_play"] = parse_play_by_play(pbp_text)

    # If venue-based validation detected teams should be swapped, swap them
    # Note: Only swap metadata team names, NOT the batting lineups
    # The lineups are parsed in order from the PDF and are correct;
    # it's the team name labels that are wrong
    if result["metadata"].get("_teams_swapped"):
        meta = result["metadata"]

        # Swap team metadata only - the lineups stay as-is
        meta["away_team"], meta["home_team"] = meta["home_team"], meta["away_team"]
        meta["away_team_score"], meta["home_team_score"] = meta["home_team_score"], meta["away_team_score"]
        meta["away_team_rank"], meta["home_team_rank"] = meta["home_team_rank"], meta["away_team_rank"]
        meta["away_team_record"], meta["home_team_record"] = meta["home_team_record"], meta["away_team_record"]

        # Remove the swap flag from output
        del meta["_teams_swapped"]

    return result


def convert_pdf_to_json(pdf_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert a PDF to JSON and optionally save to file.

    Args:
        pdf_path: Path to input PDF
        output_path: Optional path for output JSON (default: same name as PDF with .json extension)

    Returns:
        JSON string of parsed data
    """
    data = parse_ncaab_pdf(pdf_path)
    json_str = json.dumps(data, indent=2)

    if output_path is None:
        output_path = str(Path(pdf_path).with_suffix('.json'))

    with open(output_path, 'w') as f:
        f.write(json_str)

    print(f"Saved JSON to: {output_path}")
    return json_str


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ncaab_parser.py <pdf_path> [output_path]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = convert_pdf_to_json(pdf_path, output_path)
    print("\nPreview of parsed data:")
    data = json.loads(result)
    print(f"Game: {data['metadata'].get('away_team')} vs {data['metadata'].get('home_team')}")
    print(f"Date: {data['metadata'].get('date')}")
    print(f"Score: {data['metadata'].get('away_team_score')} - {data['metadata'].get('home_team_score')}")
    print(f"Batting stats parsed: {len(data['box_score'].get('away_batting', []))} away, {len(data['box_score'].get('home_batting', []))} home")
    print(f"Innings with play-by-play: {len(data['play_by_play'])}")
