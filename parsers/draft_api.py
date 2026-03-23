"""
MLB Draft API client for fetching draft pick data.

Uses the MLB Stats API draft endpoint to get draft information
for cross-referencing with NCAA and MiLB player data.

API endpoint: https://statsapi.mlb.com/api/v1/draft/{year}
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from utils.http import create_retry_session, get_with_retry

_session = create_retry_session()

DRAFT_API_BASE = "https://statsapi.mlb.com/api/v1/draft"
DRAFT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "draft_cache"


def fetch_draft_year(year: int) -> Dict[str, Any]:
    """
    Fetch draft data for a given year from MLB Stats API.

    Args:
        year: Draft year (e.g., 2024)

    Returns:
        Raw API response as dict
    """
    url = f"{DRAFT_API_BASE}/{year}"
    response = get_with_retry(url, session=_session)
    return response.json()


def parse_draft_picks(raw_data: Dict[str, Any], year: int) -> List[Dict[str, Any]]:
    """
    Parse raw draft API response into structured pick records.

    Args:
        raw_data: Raw API response
        year: Draft year

    Returns:
        List of parsed draft pick dicts
    """
    picks = []

    for round_data in raw_data.get('drafts', {}).get('rounds', []):
        round_num = round_data.get('round', '')

        for pick in round_data.get('picks', []):
            person = pick.get('person', {})
            team = pick.get('team', {})
            school = pick.get('school', {})

            # Parse round number
            try:
                round_int = int(round_num)
            except (ValueError, TypeError):
                round_int = 0

            pick_data = {
                'year': year,
                'round': round_int,
                'pick_number': pick.get('pickNumber', 0),
                'pick_round': pick.get('pickRound', ''),
                'player_name': person.get('fullName', ''),
                'mlb_api_id': person.get('id'),
                'position': person.get('primaryPosition', {}).get('abbreviation', ''),
                'school': school.get('name', ''),
                'school_state': school.get('state', ''),
                'school_class': pick.get('schoolClass', ''),  # Jr, Sr, etc.
                'team': team.get('name', ''),
                'team_short': team.get('abbreviation', ''),
                'team_id': team.get('id'),
                'signed': 1 if pick.get('signingBonus') else 0,
                'bonus': pick.get('signingBonus', ''),
                'home_city': pick.get('home', {}).get('city', ''),
                'home_state': pick.get('home', {}).get('state', ''),
                'birth_date': person.get('birthDate', ''),
                'height': person.get('height', ''),
                'weight': person.get('weight', ''),
                'bat_side': person.get('batSide', {}).get('code', ''),
                'throw_hand': person.get('pitchHand', {}).get('code', ''),
                'raw': pick,  # Keep raw data for future use
            }
            picks.append(pick_data)

    return picks


def fetch_and_cache_draft(year: int, force: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch draft data for a year, using cache if available.

    Args:
        year: Draft year
        force: Force re-fetch even if cached

    Returns:
        List of parsed draft picks
    """
    DRAFT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = DRAFT_CACHE_DIR / f"draft_{year}.json"

    if not force and cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        print(f"  Draft {year}: {len(cached)} picks (cached)")
        return cached

    print(f"  Fetching draft {year} from API...")
    try:
        raw_data = fetch_draft_year(year)
        picks = parse_draft_picks(raw_data, year)

        # Cache the parsed picks
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(picks, f, indent=2, default=str)

        print(f"  Draft {year}: {len(picks)} picks fetched and cached")
        return picks
    except Exception as e:
        print(f"  Error fetching draft {year}: {e}")
        return []


def fetch_draft_range(start_year: int = 2020, end_year: int = None,
                      force: bool = False, delay: float = 1.0) -> List[Dict[str, Any]]:
    """
    Fetch draft data for a range of years.

    Args:
        start_year: First year to fetch
        end_year: Last year to fetch (default: current year)
        force: Force re-fetch
        delay: Seconds between API calls

    Returns:
        Combined list of all draft picks
    """
    if end_year is None:
        end_year = datetime.now().year

    all_picks = []
    print(f"Fetching draft data for {start_year}-{end_year}...")

    for year in range(start_year, end_year + 1):
        picks = fetch_and_cache_draft(year, force=force)
        all_picks.extend(picks)
        if year < end_year:
            time.sleep(delay)

    print(f"Total: {len(all_picks)} draft picks across {end_year - start_year + 1} years")
    return all_picks


def match_draft_to_crossover(draft_picks: List[Dict], crossover_players: List[Dict],
                              id_mapper=None) -> Dict[str, Dict]:
    """
    Match draft picks to crossover players by ID or name.

    Args:
        draft_picks: List of parsed draft pick dicts
        crossover_players: List of crossover player dicts (from PlayerCrossover.to_dataframe_data)
        id_mapper: Optional PlayerIDMapper for ID translation

    Returns:
        Dict mapping player key (bref_id or name) to draft info
    """
    # Build lookup by mlb_api_id
    draft_by_mlb_id = {}
    draft_by_name = {}

    for pick in draft_picks:
        mlb_id = pick.get('mlb_api_id')
        if mlb_id:
            draft_by_mlb_id[mlb_id] = pick
        name = pick.get('player_name', '').lower()
        if name:
            draft_by_name[name] = pick

    matched = {}

    for player in crossover_players:
        bref_id = player.get('BBRef ID', '')
        mlb_api_id = player.get('MLB API ID', '')
        name = player.get('Name', '')

        draft_info = None

        # Try MLB API ID first
        if mlb_api_id and int(mlb_api_id) in draft_by_mlb_id:
            draft_info = draft_by_mlb_id[int(mlb_api_id)]

        # Try ID mapper: bref_id -> mlb_api_id -> draft lookup
        if not draft_info and bref_id and id_mapper:
            mapped_mlb_id = id_mapper.get_mlbam_from_register(bref_id)
            if mapped_mlb_id and mapped_mlb_id in draft_by_mlb_id:
                draft_info = draft_by_mlb_id[mapped_mlb_id]

        # Fallback: name matching
        if not draft_info and name:
            draft_info = draft_by_name.get(name.lower())

        if draft_info:
            key = bref_id or name
            matched[key] = draft_info

    return matched


if __name__ == '__main__':
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    picks = fetch_and_cache_draft(year, force=True)

    print(f"\nDraft {year}: {len(picks)} picks")
    for pick in picks[:10]:
        school = pick.get('school', 'N/A')
        print(f"  Round {pick['round']}, Pick {pick['pick_number']}: "
              f"{pick['player_name']} ({pick['position']}) - {pick['team_short']} "
              f"from {school}")
