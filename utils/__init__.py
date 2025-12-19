"""
Shared utility functions for ncaab_processor.
"""

from .names import (
    normalize_name,
    normalize_name_for_matching,
    normalize_lookup_name,
    normalize_team_name,
    clean_player_name,
    format_innings_pitched,
    parse_innings_pitched,
    UPPERCASE_TEAMS,
    TYPO_CORRECTIONS,
)

__all__ = [
    'normalize_name',
    'normalize_name_for_matching',
    'normalize_lookup_name',
    'normalize_team_name',
    'clean_player_name',
    'format_innings_pitched',
    'parse_innings_pitched',
    'UPPERCASE_TEAMS',
    'TYPO_CORRECTIONS',
]
