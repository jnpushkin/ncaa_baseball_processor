"""
Format A (no jersey numbers) parser for NCAA baseball box scores.

This is a variant of Format A without jersey numbers.
"""

import re
from dataclasses import asdict
from typing import Optional

from .models import PlayerBattingStats
from .format_a import VALID_POSITIONS, parse_side_by_side_pitching_line


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
