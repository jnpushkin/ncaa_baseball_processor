#!/usr/bin/env python3
"""
Partner League Roster Integration

Fetches and caches rosters from Baseball Reference for Partner League teams,
enabling player ID lookups for crossover tracking.
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

# Import from existing scraper
from bref_roster_scraper import fetch_roster, lookup_player, REQUEST_DELAY

# Lazy import to avoid circular dependency
_partner_stadiums = None


def _get_partner_stadiums():
    """Lazy load partner_stadiums module."""
    global _partner_stadiums
    if _partner_stadiums is None:
        from baseball_processor.utils.partner_stadiums import (
            get_bref_team_id,
            get_canonical_team_name,
            PARTNER_TEAM_DATA,
        )
        _partner_stadiums = {
            'get_bref_team_id': get_bref_team_id,
            'get_canonical_team_name': get_canonical_team_name,
            'PARTNER_TEAM_DATA': PARTNER_TEAM_DATA,
        }
    return _partner_stadiums


# Cache directory for partner rosters
PARTNER_ROSTER_CACHE_DIR = Path("partner/rosters")


def get_cached_roster_path(team_name: str, year: int) -> Path:
    """Get the cache file path for a team roster."""
    ps = _get_partner_stadiums()
    canonical = ps['get_canonical_team_name'](team_name)
    safe_name = canonical.lower().replace(' ', '_').replace('-', '_').replace("'", "")
    return PARTNER_ROSTER_CACHE_DIR / f"{safe_name}_{year}.json"


def load_cached_roster(team_name: str, year: int) -> Optional[Dict]:
    """Load a cached roster if it exists."""
    cache_path = get_cached_roster_path(team_name, year)
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading cached roster: {e}")
    return None


def save_roster_to_cache(roster: Dict, team_name: str, year: int) -> Path:
    """Save a roster to the cache."""
    cache_path = get_cached_roster_path(team_name, year)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(roster, f, indent=2)
    return cache_path


def fetch_partner_roster(team_name: str, year: int, use_cache: bool = True) -> Optional[Dict]:
    """
    Fetch roster for a Partner League team from Baseball Reference.

    Args:
        team_name: Partner team name (will be canonicalized)
        year: Year of the roster (e.g., 2019, 2024)
        use_cache: Whether to use cached roster if available

    Returns:
        Roster dictionary with players list, or None if not found
    """
    ps = _get_partner_stadiums()

    # Check cache first
    if use_cache:
        cached = load_cached_roster(team_name, year)
        if cached:
            print(f"Using cached roster for {team_name} ({year})")
            return cached

    # Get the bref team ID
    bref_team_id = ps['get_bref_team_id'](team_name, year)
    if not bref_team_id:
        print(f"No Baseball Reference team ID found for {team_name} ({year})")
        return None

    print(f"Fetching roster for {team_name} ({year}) from Baseball Reference (ID: {bref_team_id})")

    # Fetch the roster
    roster = fetch_roster(bref_team_id)
    if not roster:
        print(f"Failed to fetch roster for {team_name}")
        return None

    # Convert to dict for caching
    from dataclasses import asdict
    roster_dict = {
        "team_name": roster.team_name,
        "team_id": roster.team_id,
        "partner_team_name": team_name,
        "year": str(year),
        "players": [asdict(p) for p in roster.players]
    }

    # Save to cache
    cache_path = save_roster_to_cache(roster_dict, team_name, year)
    print(f"Cached roster to: {cache_path}")

    return roster_dict


def lookup_partner_player(team_name: str, year: int, player_name: str) -> Optional[str]:
    """
    Look up a player's bref_id from a Partner team roster.

    Args:
        team_name: Partner team name
        year: Year of the game
        player_name: Player name as it appears in the box score

    Returns:
        bref_id (e.g., "allgey000jak") or None if not found
    """
    roster = fetch_partner_roster(team_name, year)
    if not roster:
        return None

    player = lookup_player(roster, player_name)
    if player:
        return player.get('bref_id')

    return None


def lookup_partner_player_full(team_name: str, year: int, player_name: str) -> Optional[Dict[str, str]]:
    """
    Look up a player's bref_id and full name from a Partner team roster.

    Args:
        team_name: Partner team name
        year: Year of the game
        player_name: Player name as it appears in the box score

    Returns:
        Dict with 'bref_id' and 'full_name' keys, or None if not found
    """
    roster = fetch_partner_roster(team_name, year)
    if not roster:
        return None

    player = lookup_player(roster, player_name)
    if player:
        return {
            'bref_id': player.get('bref_id'),
            'full_name': player.get('name'),
        }

    return None


def bulk_fetch_partner_rosters(year: int, league: Optional[str] = None, delay: float = REQUEST_DELAY) -> Dict[str, Any]:
    """
    Fetch rosters for all Partner League teams for a given year.

    Args:
        year: Year to fetch rosters for
        league: Optional league filter ("Pioneer League", "Atlantic League", etc.)
        delay: Delay between requests (default: REQUEST_DELAY)

    Returns:
        Dictionary with fetch results {team_name: roster_dict or None}
    """
    ps = _get_partner_stadiums()
    results = {}
    seen_ids = set()

    for team_name, data in ps['PARTNER_TEAM_DATA'].items():
        team_id = data.get('id')
        if team_id in seen_ids:
            continue
        seen_ids.add(team_id)

        # Filter by league if specified
        if league and data.get('league') != league:
            continue

        # Check if team has bref_team_ids for this year
        bref_team_ids = data.get('bref_team_ids', {})
        if year not in bref_team_ids:
            print(f"Skipping {team_name}: no roster for {year}")
            continue

        print(f"\nFetching roster for {team_name} ({year})...")

        try:
            roster = fetch_partner_roster(team_name, year, use_cache=True)
            results[team_name] = roster
        except Exception as e:
            print(f"Error fetching {team_name}: {e}")
            results[team_name] = None

        # Rate limiting
        time.sleep(delay)

    return results


def get_all_cached_rosters() -> Dict[str, Dict]:
    """Get all cached rosters."""
    rosters = {}
    if not PARTNER_ROSTER_CACHE_DIR.exists():
        return rosters

    for roster_file in PARTNER_ROSTER_CACHE_DIR.glob("*.json"):
        try:
            with open(roster_file, 'r') as f:
                roster = json.load(f)
                team_name = roster.get('partner_team_name') or roster.get('team_name')
                year = roster.get('year')
                rosters[f"{team_name}_{year}"] = roster
        except (json.JSONDecodeError, IOError):
            continue

    return rosters


def create_player_lookup_index(rosters: Dict[str, Dict] = None) -> Dict[str, str]:
    """
    Create an index mapping normalized player names to bref_ids.

    Returns:
        Dictionary mapping "lastname_firstinitial_teamid_year" -> bref_id
    """
    if rosters is None:
        rosters = get_all_cached_rosters()

    index = {}

    for key, roster in rosters.items():
        team_name = roster.get('partner_team_name') or roster.get('team_name')
        year = roster.get('year')

        for player in roster.get('players', []):
            bref_id = player.get('bref_id')
            if not bref_id:
                continue

            last_name = player.get('last_name', '').lower()
            first_name = player.get('first_name', '')
            first_initial = first_name[0].lower() if first_name else ''

            # Create multiple lookup keys for flexible matching
            # Key format: lastname_firstinitial_teamname_year
            safe_team = team_name.lower().replace(' ', '_') if team_name else ''

            keys = [
                f"{last_name}_{first_initial}_{safe_team}_{year}",
                f"{last_name}_{safe_team}_{year}",  # Just last name (less specific)
            ]

            for lookup_key in keys:
                if lookup_key not in index:
                    index[lookup_key] = bref_id

    return index


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Partner League Roster Integration")
        print("\nUsage:")
        print("  python partner_roster_integration.py fetch <team_name> <year>")
        print("  python partner_roster_integration.py bulk <year> [league]")
        print("  python partner_roster_integration.py lookup <team_name> <year> <player_name>")
        print("  python partner_roster_integration.py list")
        print("\nExamples:")
        print('  python partner_roster_integration.py fetch "Oakland Ballers" 2024')
        print('  python partner_roster_integration.py bulk 2024 "Pioneer League"')
        print('  python partner_roster_integration.py lookup "Oakland Ballers" 2024 "Payton Harden"')
        print('  python partner_roster_integration.py list')
        sys.exit(0)

    command = sys.argv[1]

    if command == "fetch":
        if len(sys.argv) < 4:
            print("Usage: fetch <team_name> <year>")
            sys.exit(1)
        team_name = sys.argv[2]
        year = int(sys.argv[3])
        roster = fetch_partner_roster(team_name, year, use_cache=False)
        if roster:
            print(f"\nFetched {len(roster.get('players', []))} players for {team_name}")

    elif command == "bulk":
        if len(sys.argv) < 3:
            print("Usage: bulk <year> [league]")
            sys.exit(1)
        year = int(sys.argv[2])
        league = sys.argv[3] if len(sys.argv) > 3 else None
        results = bulk_fetch_partner_rosters(year, league)
        print(f"\n\nFetched {sum(1 for r in results.values() if r)} rosters")

    elif command == "lookup":
        if len(sys.argv) < 5:
            print("Usage: lookup <team_name> <year> <player_name>")
            sys.exit(1)
        team_name = sys.argv[2]
        year = int(sys.argv[3])
        player_name = sys.argv[4]
        bref_id = lookup_partner_player(team_name, year, player_name)
        if bref_id:
            print(f"Found bref_id: {bref_id}")
        else:
            print("Player not found")

    elif command == "list":
        rosters = get_all_cached_rosters()
        print(f"Cached rosters ({len(rosters)}):")
        for key in sorted(rosters.keys()):
            roster = rosters[key]
            print(f"  - {roster.get('partner_team_name')} ({roster.get('year')}): {len(roster.get('players', []))} players")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
