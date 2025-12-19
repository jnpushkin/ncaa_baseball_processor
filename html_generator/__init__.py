"""
NCAA Baseball HTML Generator Package.

Generates Baseball Reference-style HTML pages from parsed box score data.
"""

from .page import (
    generate_html_page,
    convert_game_to_html,
    convert_all_games,
)

from .components import (
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
]
