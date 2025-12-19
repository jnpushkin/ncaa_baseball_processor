"""
Helper utility functions.
"""

import re
from typing import Any, Optional

# Import shared utilities to avoid duplication
from utils.names import (
    format_innings_pitched,
    parse_innings_pitched,
    normalize_team_name,
    UPPERCASE_TEAMS,
)


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value or value == '-':
                return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value or value == '-':
                return default
        return float(value)
    except (ValueError, TypeError):
        return default


def normalize_name(name: str) -> str:
    """
    Normalize player name for consistent tracking.

    Converts to lowercase, removes extra spaces, handles common variations.
    Converts "Last, First" format to "first last" for consistent display.
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


def calculate_batting_average(hits: int, at_bats: int) -> str:
    """Calculate batting average."""
    if at_bats == 0:
        return '.000'
    avg = hits / at_bats
    return f".{int(avg * 1000):03d}"


def calculate_era(earned_runs: int, innings_pitched: float) -> str:
    """Calculate ERA."""
    if innings_pitched == 0:
        return '-'
    era = (earned_runs * 9) / innings_pitched
    return f"{era:.2f}"


def calculate_whip(walks: int, hits: int, innings_pitched: float) -> str:
    """Calculate WHIP."""
    if innings_pitched == 0:
        return '-'
    whip = (walks + hits) / innings_pitched
    return f"{whip:.2f}"


def parse_date_for_sort(date_str: str) -> str:
    """Convert date string to sortable format (YYYY-MM-DD).

    Handles formats like:
    - M/D/YYYY or MM/DD/YYYY
    - YYYY-MM-DD
    """
    if not date_str:
        return "0000-00-00"

    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                month, day, year = parts
                # Handle 2-digit year
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                return f"{year}-{int(month):02d}-{int(day):02d}"
        elif '-' in date_str:
            # Already in YYYY-MM-DD format
            return date_str
    except (ValueError, IndexError):
        pass

    return date_str
