"""
Format B parser for NCAA baseball box scores.

Format B is the newer NCAA format with Team (record) -vs- Team (record) style.
"""

import re
from dataclasses import asdict
from typing import Optional

from .models import PlayerBattingStats, PitcherStats
from .format_a import VALID_POSITIONS


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
