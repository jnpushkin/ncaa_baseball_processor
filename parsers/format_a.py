"""
Format A parser for NCAA baseball box scores.

Format A is the original VMI at Virginia style with side-by-side stats and jersey numbers.
"""

import re
from dataclasses import asdict
from typing import Optional

from .models import PlayerBattingStats, PitcherStats


# Valid baseball positions
VALID_POSITIONS = {
    'ss', 'cf', 'rf', 'lf', '1b', '2b', '3b', 'c', 'p', 'dh', 'ph',
    'ph/ss', 'ph/lf', 'ph/1b', 'ph/rf', 'ph/cf', 'ph/3b', 'ph/2b', 'ph/c', 'ph/dh',
    'pr', 'pr/ss', 'pr/lf', 'pr/rf'
}


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
    OR: Name ip h r er bb k bf ab np (no jersey number)
    Name may contain multiple parts (e.g., "McGarry, G.")
    """
    if len(parts) < 10:
        return None

    try:
        # Check if first part is a jersey number (digits only)
        has_jersey_number = parts[0].isdigit()

        # Find the IP field (first float-like value)
        ip_idx = None
        start_idx = 1 if has_jersey_number else 0
        for i in range(start_idx, min(start_idx + 4, len(parts))):
            try:
                float(parts[i])
                ip_idx = i
                break
            except ValueError:
                continue

        if ip_idx is None:
            return None

        # Extract name and number based on format
        if has_jersey_number:
            number = parts[0]
            name = ' '.join(parts[1:ip_idx])
        else:
            number = ''
            name = ' '.join(parts[0:ip_idx])

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

        # Check if home_parts looks like a valid pitcher entry
        # It should start with either a jersey number OR a name (letters)
        first_char = home_parts[0][0] if home_parts[0] else ''
        if not (first_char.isdigit() or first_char.isalpha()):
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
