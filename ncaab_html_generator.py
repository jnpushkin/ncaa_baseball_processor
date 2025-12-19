#!/usr/bin/env python3
"""
NCAA Baseball HTML Generator

Generates Baseball Reference-style HTML pages from parsed box score data.
Includes player links to Baseball Reference register pages.

This is a backward-compatibility layer. The actual implementation
is in the html_generator/ package.
"""

# Re-export from html_generator package for backward compatibility
from html_generator import (
    generate_html_page,
    convert_game_to_html,
    convert_all_games,
    BREF_BASE,
    generate_player_link,
    generate_batting_table,
    generate_pitching_table,
    generate_line_score,
    generate_game_notes,
    generate_game_info,
    get_hr_counts_for_players,
    match_player_hr,
)

# Also re-export these for any code that imports them from here
from utils.names import normalize_name_for_matching, format_innings_pitched

__all__ = [
    'generate_html_page',
    'convert_game_to_html',
    'convert_all_games',
    'BREF_BASE',
    'generate_player_link',
    'generate_batting_table',
    'generate_pitching_table',
    'generate_line_score',
    'generate_game_notes',
    'generate_game_info',
    'get_hr_counts_for_players',
    'match_player_hr',
    'normalize_name_for_matching',
    'format_innings_pitched',
]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("NCAA Baseball HTML Generator")
        print("\nUsage:")
        print("  python ncaab_html_generator.py <game.json> [output.html] [--roster-dir DIR]")
        print("  python ncaab_html_generator.py --all <input_dir> <output_dir> [--roster-dir DIR]")
        print("\nExamples:")
        print("  python ncaab_html_generator.py output/game1.json")
        print("  python ncaab_html_generator.py output/game1.json game1.html --roster-dir rosters")
        print("  python ncaab_html_generator.py --all output html_output --roster-dir rosters")
        sys.exit(1)

    roster_dir = None
    if "--roster-dir" in sys.argv:
        idx = sys.argv.index("--roster-dir")
        roster_dir = sys.argv[idx + 1]
        sys.argv = sys.argv[:idx] + sys.argv[idx + 2:]

    if sys.argv[1] == "--all":
        if len(sys.argv) < 4:
            print("Error: --all requires input_dir and output_dir")
            sys.exit(1)
        convert_all_games(sys.argv[2], sys.argv[3], roster_dir)
    else:
        game_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        convert_game_to_html(game_path, output_path, roster_dir)
