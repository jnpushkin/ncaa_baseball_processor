"""
MiLB Stats API client for fetching Minor League Baseball box scores.

Uses the MLB Stats API (statsapi.mlb.com) which provides data for all
affiliated minor league games and MLB Partner Leagues (independent leagues).

Partner Leagues (independent):
- Atlantic League of Professional Baseball
- American Association of Professional Baseball
- Frontier League
- Pioneer League
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


MILB_API_BASE = "https://statsapi.mlb.com/api/v1"

# MLB Partner Leagues (independent leagues)
PARTNER_LEAGUES = {
    'Atlantic League',
    'American Association',
    'Frontier League',
    'Pioneer League',
}


def fetch_game_boxscore(game_pk: int) -> Dict[str, Any]:
    """
    Fetch box score data from the MLB Stats API.

    Args:
        game_pk: Game primary key (from MiLB.com URL)

    Returns:
        Raw API response as dict

    Raises:
        requests.RequestException: If API request fails
    """
    url = f"{MILB_API_BASE}/game/{game_pk}/boxscore"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_game_content(game_pk: int) -> Dict[str, Any]:
    """
    Fetch game content/metadata from the MLB Stats API.

    Args:
        game_pk: Game primary key

    Returns:
        Raw API response as dict
    """
    url = f"{MILB_API_BASE}/game/{game_pk}/content"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_game_feed(game_pk: int) -> Dict[str, Any]:
    """
    Fetch live game feed for additional metadata.

    Args:
        game_pk: Game primary key

    Returns:
        Raw API response as dict
    """
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_batting_stats(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse batting statistics from API player data.

    Args:
        player_data: Player data from API response

    Returns:
        Dict with normalized batting stats
    """
    stats = player_data.get('stats', {}).get('batting', {})
    person = player_data.get('person', {})

    return {
        'name': person.get('fullName', ''),
        'player_id': person.get('id'),
        'position': player_data.get('position', {}).get('abbreviation', ''),
        'jersey_number': player_data.get('jerseyNumber', ''),
        'batting_order': player_data.get('battingOrder'),
        # Batting stats
        'ab': stats.get('atBats', 0),
        'r': stats.get('runs', 0),
        'h': stats.get('hits', 0),
        'rbi': stats.get('rbi', 0),
        'bb': stats.get('baseOnBalls', 0),
        'k': stats.get('strikeOuts', 0),
        'doubles': stats.get('doubles', 0),
        'triples': stats.get('triples', 0),
        'hr': stats.get('homeRuns', 0),
        'sb': stats.get('stolenBases', 0),
        'cs': stats.get('caughtStealing', 0),
        'avg': stats.get('avg', '.000'),
        'obp': stats.get('obp', '.000'),
        'slg': stats.get('slg', '.000'),
        'lob': stats.get('leftOnBase', 0),
    }


def parse_pitching_stats(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse pitching statistics from API player data.

    Args:
        player_data: Player data from API response

    Returns:
        Dict with normalized pitching stats
    """
    stats = player_data.get('stats', {}).get('pitching', {})
    person = player_data.get('person', {})

    return {
        'name': person.get('fullName', ''),
        'player_id': person.get('id'),
        'jersey_number': player_data.get('jerseyNumber', ''),
        # Pitching stats
        'ip': stats.get('inningsPitched', '0.0'),
        'h': stats.get('hits', 0),
        'r': stats.get('runs', 0),
        'er': stats.get('earnedRuns', 0),
        'bb': stats.get('baseOnBalls', 0),
        'k': stats.get('strikeOuts', 0),
        'hr': stats.get('homeRuns', 0),
        'np': stats.get('numberOfPitches', 0),
        'era': stats.get('era', '0.00'),
        'bf': stats.get('battersFaced', 0),
        # Win/Loss/Save
        'win': stats.get('wins', 0) > 0,
        'loss': stats.get('losses', 0) > 0,
        'save': stats.get('saves', 0) > 0,
        'hold': stats.get('holds', 0) > 0,
        'blown_save': stats.get('blownSaves', 0) > 0,
    }


def parse_boxscore(boxscore_data: Dict[str, Any], game_feed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse API boxscore response into NCAA processor format.

    Args:
        boxscore_data: Raw boxscore API response
        game_feed: Optional game feed for additional metadata

    Returns:
        Game data dict in NCAA processor format
    """
    teams = boxscore_data.get('teams', {})
    away_data = teams.get('away', {})
    home_data = teams.get('home', {})

    # Extract team info
    away_team = away_data.get('team', {})
    home_team = home_data.get('team', {})

    # Get game info from feed if available
    game_info = {}
    venue_info = {}
    if game_feed:
        game_data = game_feed.get('gameData', {})
        game_info = game_data.get('game', {})
        datetime_info = game_data.get('datetime', {})
        venue_info = game_data.get('venue', {})

    # Parse date
    game_date = datetime_info.get('officialDate', '') if game_feed else ''
    if game_date:
        try:
            date_obj = datetime.strptime(game_date, '%Y-%m-%d')
            date_yyyymmdd = date_obj.strftime('%Y%m%d')
            date_display = date_obj.strftime('%m/%d/%Y')
        except ValueError:
            date_yyyymmdd = ''
            date_display = game_date
    else:
        date_yyyymmdd = ''
        date_display = ''

    # Parse batting - filter to players who actually batted
    away_batters = []
    home_batters = []

    for player_key, player_data in away_data.get('players', {}).items():
        if player_data.get('stats', {}).get('batting'):
            stats = parse_batting_stats(player_data)
            if stats.get('ab', 0) > 0 or stats.get('bb', 0) > 0:  # Had plate appearance
                away_batters.append(stats)

    for player_key, player_data in home_data.get('players', {}).items():
        if player_data.get('stats', {}).get('batting'):
            stats = parse_batting_stats(player_data)
            if stats.get('ab', 0) > 0 or stats.get('bb', 0) > 0:
                home_batters.append(stats)

    # Sort by batting order
    away_batters.sort(key=lambda x: x.get('batting_order') or 999)
    home_batters.sort(key=lambda x: x.get('batting_order') or 999)

    # Parse pitching
    away_pitchers = []
    home_pitchers = []

    for player_key, player_data in away_data.get('players', {}).items():
        if player_data.get('stats', {}).get('pitching'):
            stats = parse_pitching_stats(player_data)
            if stats.get('ip', '0.0') != '0.0' or stats.get('bf', 0) > 0:
                away_pitchers.append(stats)

    for player_key, player_data in home_data.get('players', {}).items():
        if player_data.get('stats', {}).get('pitching'):
            stats = parse_pitching_stats(player_data)
            if stats.get('ip', '0.0') != '0.0' or stats.get('bf', 0) > 0:
                home_pitchers.append(stats)

    # Get team totals
    away_batting_totals = away_data.get('teamStats', {}).get('batting', {})
    home_batting_totals = home_data.get('teamStats', {}).get('batting', {})

    # Determine if this is a Partner League game
    away_league = away_team.get('league', {}).get('name', '')
    home_league = home_team.get('league', {}).get('name', '')
    away_parent = away_team.get('parentOrgName', '')
    home_parent = home_team.get('parentOrgName', '')

    # Check if either team is from a Partner League
    is_partner = False
    for league in PARTNER_LEAGUES:
        if league in away_league or league in home_league:
            is_partner = True
            break

    # Also check if no parent org (independent team)
    if not away_parent and not home_parent:
        is_partner = True

    source = 'partner' if is_partner else 'milb'

    # Build game data in NCAA processor format
    game_data = {
        'metadata': {
            'date': date_display,
            'date_yyyymmdd': date_yyyymmdd,
            'away_team': away_team.get('name', ''),
            'away_team_short': away_team.get('abbreviation', ''),
            'away_team_id': away_team.get('id'),
            'home_team': home_team.get('name', ''),
            'home_team_short': home_team.get('abbreviation', ''),
            'home_team_id': home_team.get('id'),
            'away_team_score': away_batting_totals.get('runs', 0),
            'home_team_score': home_batting_totals.get('runs', 0),
            'venue': venue_info.get('name', ''),
            'venue_city': venue_info.get('location', {}).get('city', ''),
            'venue_state': venue_info.get('location', {}).get('state', ''),
            'attendance': boxscore_data.get('info', [{}])[0].get('value') if boxscore_data.get('info') else None,
            # MiLB-specific fields
            'parent_orgs': {
                'away': away_parent,
                'home': home_parent,
            },
            'league': {
                'away': away_league,
                'home': home_league,
            },
            'sport_level': {
                'away': away_team.get('sport', {}).get('name', ''),
                'home': home_team.get('sport', {}).get('name', ''),
            },
            'source': source,
            'game_pk': game_info.get('pk') if game_feed else None,
        },
        'box_score': {
            'away_batting': away_batters,
            'home_batting': home_batters,
            'away_pitching': away_pitchers,
            'home_pitching': home_pitchers,
        },
        'game_notes': {
            # TODO: Parse game notes from API if available
        },
        'play_by_play': {
            # TODO: Parse play by play if needed
        },
        'format': 'milb_api',
    }

    return game_data


def process_milb_game(game_pk: int, cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Fetch and process a MiLB game, with optional caching.

    Args:
        game_pk: Game primary key from MiLB.com URL
        cache_dir: Optional cache directory for storing responses

    Returns:
        Processed game data dict
    """
    # Check cache first
    if cache_dir:
        cache_file = cache_dir / f"milb_{game_pk}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

    # Fetch from API
    print(f"Fetching MiLB game {game_pk} from API...")
    boxscore = fetch_game_boxscore(game_pk)

    # Try to get additional metadata from game feed
    try:
        game_feed = fetch_game_feed(game_pk)
    except Exception:
        game_feed = None

    # Parse the data
    game_data = parse_boxscore(boxscore, game_feed)
    game_data['metadata']['game_pk'] = game_pk

    # Save to cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"milb_{game_pk}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2)
        print(f"  Cached to {cache_file}")

    return game_data


def load_game_ids(game_ids_file: Path) -> List[int]:
    """
    Load game IDs from a text file (one per line).

    Args:
        game_ids_file: Path to text file with game IDs

    Returns:
        List of game PKs as integers
    """
    if not game_ids_file.exists():
        return []

    game_ids = []
    with open(game_ids_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    game_ids.append(int(line))
                except ValueError:
                    print(f"Warning: Invalid game ID '{line}', skipping")

    return game_ids


def process_all_milb_games(
    game_ids_file: Path,
    cache_dir: Path,
) -> List[Dict[str, Any]]:
    """
    Process all MiLB games listed in the game IDs file.

    Args:
        game_ids_file: Path to text file with game IDs
        cache_dir: Cache directory for storing responses

    Returns:
        List of processed game data dicts
    """
    game_ids = load_game_ids(game_ids_file)
    if not game_ids:
        print("No MiLB game IDs found")
        return []

    print(f"Processing {len(game_ids)} MiLB games...")
    games = []

    for game_pk in game_ids:
        try:
            game_data = process_milb_game(game_pk, cache_dir)
            games.append(game_data)
            away = game_data['metadata']['away_team_short']
            home = game_data['metadata']['home_team_short']
            date = game_data['metadata']['date']
            print(f"  {date}: {away} @ {home}")
        except Exception as e:
            print(f"  Error processing game {game_pk}: {e}")

    return games


if __name__ == '__main__':
    # Test with a sample game
    import sys

    if len(sys.argv) > 1:
        game_pk = int(sys.argv[1])
    else:
        game_pk = 788401  # Default test game

    game_data = process_milb_game(game_pk)

    # Print summary
    meta = game_data['metadata']
    print(f"\nGame: {meta['away_team']} @ {meta['home_team']}")
    print(f"Date: {meta['date']}")
    print(f"Score: {meta['away_team_score']} - {meta['home_team_score']}")
    print(f"Venue: {meta['venue']}")
    print(f"Parent Orgs: {meta['parent_orgs']}")

    print(f"\nAway batters: {len(game_data['box_score']['away_batting'])}")
    print(f"Home batters: {len(game_data['box_score']['home_batting'])}")
    print(f"Away pitchers: {len(game_data['box_score']['away_pitching'])}")
    print(f"Home pitchers: {len(game_data['box_score']['home_pitching'])}")
