"""
Name normalization and formatting utilities.

This module consolidates various name handling functions used throughout
the ncaab_processor codebase.
"""

import re
from typing import Optional


# Known typos in source PDFs: {typo: correction}
TYPO_CORRECTIONS = {
    'FUNY, Matty': 'Fung, Matty',
    'FUNY': 'Fung',
}

# Teams that should remain uppercase (acronyms)
UPPERCASE_TEAMS = {
    'VMI', 'TCU', 'LSU', 'LMU', 'UCLA', 'USC', 'UCF', 'SMU', 'BYU', 'UNLV',
    'UIC', 'UTSA', 'ETSU', 'NJIT', 'UMBC', 'FIU', 'FAU', 'UAB', 'USF',
    'FGCU', 'CSUN', 'PFW', 'NIU', 'UIW', 'VCU', 'LIU'
}


def clean_player_name(name: str) -> str:
    """
    Clean a player name by removing position annotations and other artifacts.

    This is used to clean raw names from box scores before matching.

    Args:
        name: Raw player name from box score

    Returns:
        Cleaned name string
    """
    if not name:
        return name

    # Fix known typos
    if name in TYPO_CORRECTIONS:
        name = TYPO_CORRECTIONS[name]

    # Remove position annotations like "3b/1b", "pr/2b", "cf/lf", "(ph/lf)"
    # These appear at the end of names, sometimes with space, sometimes without
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)  # (ph/lf) at end
    name = re.sub(r'\s*[123]?[bB]/[123]?[bB]\s*$', '', name)  # 3b/1b at end
    name = re.sub(r'\s+(?:ph|pr|dh|cf|lf|rf|ss|[123]?b|c)/(?:ph|pr|dh|cf|lf|rf|ss|[123]?b|c)\s*$', '', name, flags=re.IGNORECASE)  # pr/2b, cf/lf
    name = re.sub(r'\s+(?:ph|pr|dh|cf|lf|rf|ss|[123]b|c)\s*$', '', name, flags=re.IGNORECASE)  # Single position

    # Remove game note prefixes like "SB:", "2B:", "CS:", "E:", "SF:", "SH:"
    name = re.sub(r'^(SB|2B|3B|HR|CS|E|SF|SH|HBP|IBB|SO|WP|PB|BK):\s*', '', name)

    # Remove trailing stat notations like "(1)"
    name = re.sub(r'\s*\(\d+\)\s*', ' ', name)

    # Remove "Totals" and anything after
    if 'Totals' in name:
        name = name.split('Totals')[0]

    # Handle ALL CAPS names - convert to title case but preserve suffixes
    if name.isupper() and len(name) > 2:
        # Split on comma if present
        if ',' in name:
            parts = name.split(',', 1)
            last = parts[0].strip().title()
            first = parts[1].strip().title() if len(parts) > 1 else ''
            # Preserve Jr., Sr., III, etc.
            first = re.sub(r'\bIii\b', 'III', first)
            first = re.sub(r'\bIi\b', 'II', first)
            first = re.sub(r'\bIv\b', 'IV', first)
            name = f"{last}, {first}" if first else last
        else:
            name = name.title()
            name = re.sub(r'\bIii\b', 'III', name)
            name = re.sub(r'\bIi\b', 'II', name)
            name = re.sub(r'\bIv\b', 'IV', name)

    return name.strip()


def normalize_name(name: str) -> str:
    """
    Normalize player name for consistent tracking and display.

    Converts to lowercase, removes extra spaces, handles common variations.
    Converts "Last, First" format to "first last" for consistent display.

    Args:
        name: Player name in any format

    Returns:
        Normalized name string (lowercase, "first last" format)
    """
    if not name:
        return ""

    # Strip whitespace
    name = name.strip()

    # Handle "Last, First" or "Last,First" format - convert to "First Last"
    if ',' in name:
        parts = name.split(',', 1)
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ''
        if first:
            name = f"{first} {last}"
        else:
            name = last

    # Lowercase
    name = name.lower()

    # Remove common suffixes
    name = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', name, flags=re.IGNORECASE)

    # Remove extra whitespace
    name = ' '.join(name.split())

    return name


def normalize_name_for_matching(name: str) -> str:
    """
    Normalize a player name for fuzzy matching (lowercase, remove punctuation).

    Used when matching names from game notes (like HR credits) to player names.

    Args:
        name: Player name to normalize

    Returns:
        Normalized name suitable for matching
    """
    # Convert to lowercase
    name = name.lower()
    # Remove common suffixes like ", J." or ", PJ"
    name = re.sub(r',\s*[a-z\.]+$', '', name)
    # Remove periods and extra spaces
    name = re.sub(r'\.', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def normalize_lookup_name(name: str) -> str:
    """
    Normalize player name for lookup matching.

    Used when matching game note entries to player statistics.
    Handles format "LastName,First" or full names.

    Args:
        name: Player name from game notes

    Returns:
        Normalized name for lookup
    """
    if not name:
        return ""
    # Remove parenthetical content like "(19)" and common suffixes
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)
    name = re.sub(r'\s*\d+\s*$', '', name)  # Remove trailing numbers
    name = name.strip()

    # If it's in "LastName,First" format, extract just the last name
    if ',' in name:
        name = name.split(',')[0]

    return name.lower().strip().replace(',', '').replace('.', '')


def normalize_team_name(name: str) -> str:
    """
    Normalize team name capitalization.

    - Converts all-caps names to title case (UTAH -> Utah)
    - Preserves acronyms like VMI, TCU, LSU, UCLA, etc.
    - Handles special cases like "San Francisco", "Oral Roberts"

    Args:
        name: Team name to normalize

    Returns:
        Properly capitalized team name
    """
    if not name:
        return name

    name = name.strip()

    # Check if it's a known acronym that should stay uppercase
    if name.upper() in UPPERCASE_TEAMS:
        return name.upper()

    # If all uppercase and not a known acronym, convert to title case
    if name.isupper() and len(name) > 3:
        return name.title()

    # If mixed case already, return as-is
    return name


def format_innings_pitched(ip: float) -> str:
    """
    Format innings pitched (e.g., 5.1, 5.2 for outs).

    Baseball convention: .1 = 1 out, .2 = 2 outs

    Args:
        ip: Innings pitched as float (e.g., 5.333 for 5.1)

    Returns:
        Formatted string (e.g., "5.1")
    """
    whole = int(ip)
    fraction = ip - whole
    # Convert decimal to outs (0.1 = 1 out, 0.2 = 2 outs)
    if fraction < 0.15:
        outs = 0
    elif fraction < 0.4:
        outs = 1
    else:
        outs = 2
    return f"{whole}.{outs}"


def parse_innings_pitched(ip_str: str) -> float:
    """
    Parse innings pitched string to float.

    Converts "5.1" (5 and 1/3 innings) to 5.333...

    Args:
        ip_str: Innings pitched string (e.g., "5.1")

    Returns:
        Float representation for calculations
    """
    if not ip_str:
        return 0.0

    try:
        if '.' in str(ip_str):
            parts = str(ip_str).split('.')
            whole = int(parts[0])
            outs = int(parts[1]) if len(parts) > 1 else 0
            return whole + (outs / 3.0)
        return float(ip_str)
    except (ValueError, TypeError):
        return 0.0
