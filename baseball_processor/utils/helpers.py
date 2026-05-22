"""
Helper utility functions.
"""

import re
from typing import Any, Optional, Protocol

# Import shared utilities to avoid duplication
from utils.names import (
    format_innings_pitched,
    parse_innings_pitched,
    normalize_team_name,
    normalize_name,
    normalize_player_name,
    UPPERCASE_TEAMS,
)

_GAME_VENUE_OVERRIDES = {
    ("ncaa_api", "6416348"): "GCU Ballpark",
    ("ncaa_api", "6423328"): "Phoenix Municipal Stadium",
}


class _PlayerNameMapper(Protocol):
    def get_player_name(self, any_id: Any) -> Optional[str]:
        ...


_PLAYER_NAME_MAPPER_LOADED = False
_PLAYER_NAME_MAPPER: Optional[_PlayerNameMapper] = None


def _is_initial_token(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]\.?", token))


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


def is_placeholder_player_name(name: Any) -> bool:
    """Return True when a parser emitted a non-identity placeholder."""
    normalized = str(name or "").strip().lower()
    return normalized in {"", "unknown", "none", "null", "n/a", "-", "--"}


def _get_cached_player_name_mapper() -> Optional[_PlayerNameMapper]:
    """Return a local-only Chadwick mapper for player display-name repair."""
    global _PLAYER_NAME_MAPPER_LOADED, _PLAYER_NAME_MAPPER
    if _PLAYER_NAME_MAPPER_LOADED:
        return _PLAYER_NAME_MAPPER

    _PLAYER_NAME_MAPPER_LOADED = True
    try:
        from .player_ids import PlayerIDMapper

        mapper = PlayerIDMapper(auto_download=False)
        if mapper.load_cached_data():
            _PLAYER_NAME_MAPPER = mapper
    except Exception:
        _PLAYER_NAME_MAPPER = None
    return _PLAYER_NAME_MAPPER


def _name_key_tokens(name: Any) -> list[str]:
    """Return lowercase alpha-only name tokens for conservative comparisons."""
    display_name = normalize_player_name(str(name or "").strip())
    tokens = []
    for token in display_name.split():
        cleaned = re.sub(r"[^a-z]", "", token.lower())
        if cleaned:
            tokens.append(cleaned)
    return tokens


def is_single_initial_player_name(name: Any) -> bool:
    """Return True for risky source names like ``H. Ford`` but not ``T.J. Ford``."""
    display_name = normalize_player_name(str(name or "").strip())
    parts = display_name.split()
    if len(parts) < 2:
        return False
    first_token = parts[0]
    if not _is_initial_token(first_token):
        return False
    if len(parts) >= 3 and _is_initial_token(parts[1]):
        return False
    return bool(_name_key_tokens(display_name)[-1:])


def _compact_initial_tokens(name: str) -> str:
    """Format spaced initial names from Chadwick as compact display initials."""
    parts = name.split()
    if len(parts) < 3:
        return name

    initials = []
    index = 0
    while index < len(parts) and _is_initial_token(parts[index]):
        initials.append(parts[index].rstrip(".").upper() + ".")
        index += 1
    if len(initials) < 2:
        return name
    return " ".join(["".join(initials)] + parts[index:])


def _is_compatible_chadwick_name(abbreviated_name: str, candidate_name: str) -> bool:
    """Return True when a Chadwick name safely expands the source initial name."""
    current_tokens = _name_key_tokens(abbreviated_name)
    candidate_tokens = _name_key_tokens(candidate_name)
    if len(current_tokens) < 2 or len(candidate_tokens) < 2:
        return False
    if len(current_tokens[0]) != 1:
        return False
    if current_tokens[0] != candidate_tokens[0][0]:
        return False
    return current_tokens[-1] == candidate_tokens[-1]


def resolve_player_display_name(
    name: Any,
    bref_id: Any = None,
    mapper: Optional[_PlayerNameMapper] = None,
) -> str:
    """
    Expand single-initial NCAA display names from Chadwick/B-Ref IDs.

    This deliberately only repairs names such as ``H. Ford`` when the source
    row has a player ID and Chadwick agrees on first initial plus last name.
    Multi-initial display names such as ``T.J. McKenzie`` are left alone.
    """
    display_name = normalize_player_name(str(name or "").strip())
    if not display_name or not bref_id or not is_single_initial_player_name(display_name):
        return display_name

    active_mapper = mapper or _get_cached_player_name_mapper()
    if active_mapper is None:
        return display_name

    candidate = active_mapper.get_player_name(bref_id)
    if not candidate:
        return display_name

    candidate_name = normalize_player_name(str(candidate).strip())
    if is_single_initial_player_name(candidate_name):
        return display_name
    if not _is_compatible_chadwick_name(display_name, candidate_name):
        return display_name
    return _compact_initial_tokens(candidate_name)


def normalize_venue_name(name: Any) -> str:
    """Return a canonical venue display name across source-specific variants."""
    venue = re.sub(r"\s+", " ", str(name or "").strip())
    if not venue:
        return ""

    exact_aliases = {
        "Benedetti Diamond (San Francisco, CA)": "Dante Benedetti Diamond",
        "Benedetti Diamond": "Dante Benedetti Diamond",
        "Dante Benedetti Diamond": "Dante Benedetti Diamond",
        "Charles Schwab Field (Omaha, Neb.)": "Charles Schwab Field Omaha",
        "Charles Schwab Field": "Charles Schwab Field Omaha",
        "Charles Schwab Field Omaha": "Charles Schwab Field Omaha",
        "Evans Diamond at Stu Gordon Stadium": "Stu Gordon Stadium",
        "Stu Gordon Stadium (Berkeley, CA)": "Stu Gordon Stadium",
        "Stu Gordon Stadium": "Stu Gordon Stadium",
        "Excite Ballpark (San Jose, Calif.)": "Excite Ballpark",
        "Excite Ballpark": "Excite Ballpark",
        "Phoenix Muni Stadium": "Phoenix Municipal Stadium",
        "Phoenix Municipal Stadium": "Phoenix Municipal Stadium",
        "Br. Ronald Gallagher": "Louis Guisto Field at Br. Ronald Gallagher Stadium",
        "Louis Guisto Field at Br. Ronald Gallagher Stadium": "Louis Guisto Field at Br. Ronald Gallagher Stadium",
        "Davenport Field": "Disharoon Park",
        "Disharoon Park": "Disharoon Park",
        "Calvin Falwell Field": "Bank of the James Stadium",
        "Bank of the James Stadium": "Bank of the James Stadium",
        "Perfect Game Field": "Veterans Memorial Stadium",
        "Veterans Memorial Stadium": "Veterans Memorial Stadium",
    }
    if venue in exact_aliases:
        return exact_aliases[venue]

    # Source strings often append a city/state parenthetical that makes the
    # same venue appear as multiple places in the UI.
    stripped = re.sub(r"\s*\([^)]*\)\s*$", "", venue).strip()
    return exact_aliases.get(stripped, stripped)


def resolve_venue_name(meta: dict[str, Any]) -> str:
    """Return the normalized venue, including source-specific known overrides."""
    venue = normalize_venue_name(meta.get("venue", ""))
    if venue:
        return venue

    source = str(meta.get("source") or "").lower()
    game_id = str(meta.get("game_id") or meta.get("game_pk") or "")
    return normalize_venue_name(_GAME_VENUE_OVERRIDES.get((source, game_id), ""))


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
