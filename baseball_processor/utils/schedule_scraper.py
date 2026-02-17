"""
Schedule scraper for D1 baseball games from D1Baseball.com.

Fetches game schedules using the dynamic-scores.php endpoint,
which returns all D1 games for a given date (150+ per day).
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .constants import DATA_DIR, SCHEDULE_CACHE_FILE
from .stadiums import STADIUM_DATA


D1BASEBALL_SCORES_URL = "https://d1baseball.com/wp-content/plugins/integritive/dynamic-scores.php"


def fetch_games_for_date(date: datetime) -> List[Dict]:
    """
    Fetch and parse all D1 games for a given date from D1Baseball.

    Args:
        date: The date to fetch games for

    Returns:
        List of parsed game dicts
    """
    date_str = date.strftime('%Y%m%d')
    try:
        resp = requests.get(
            D1BASEBALL_SCORES_URL,
            params={'date': date_str, 'sport': 'baseball'},
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://d1baseball.com/scores/',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  Error fetching {date_str}: {e}")
        return []

    html = data.get('content', {}).get('d1-scores', '')
    if not html:
        return []

    return _parse_score_tiles(html, date)


def _parse_score_tiles(html: str, date: datetime) -> List[Dict]:
    """
    Parse D1Baseball score tile HTML into game dicts.

    Args:
        html: HTML string containing score tiles
        date: The date these games are for

    Returns:
        List of parsed game dicts
    """
    soup = BeautifulSoup(html, 'html.parser')
    games = []

    for tile in soup.find_all('div', class_='d1-score-tile'):
        try:
            game = _parse_single_tile(tile, date)
            if game:
                games.append(game)
        except Exception as e:
            # Skip malformed tiles
            continue

    return games


def _parse_single_tile(tile, date: datetime) -> Optional[Dict]:
    """Parse a single score tile div into a game dict."""
    home_name = tile.get('data-home-name', '').strip()
    away_name = tile.get('data-road-name', '').strip()

    if not home_name or not away_name:
        return None

    # Parse matchup time (unix timestamp)
    matchup_time = tile.get('data-matchup-time', '')
    if matchup_time and matchup_time.isdigit():
        game_dt = datetime.fromtimestamp(int(matchup_time))
    else:
        game_dt = date

    # Game status
    in_progress = tile.get('data-in-progress', '0') == '1'
    is_over = tile.get('data-is-over', '0') == '1'

    # Status text from the h5 inside .status-wrapper
    status_wrapper = tile.find('div', class_='status-wrapper')
    time_detail = ''
    if status_wrapper:
        h5 = status_wrapper.find('h5')
        if h5:
            time_detail = h5.get_text(strip=True)

    time_lower = time_detail.lower()
    if is_over:
        status = 'final'
    elif in_progress:
        status = 'in_progress'
    elif 'canceled' in time_lower or 'cancelled' in time_lower:
        status = 'canceled'
    elif 'postponed' in time_lower or 'ppd' in time_lower:
        status = 'postponed'
    else:
        status = 'scheduled'

    # Parse teams
    home_team = _parse_team_from_tile(tile, 'home')
    away_team = _parse_team_from_tile(tile, 'road')

    # Override names from data attributes (more reliable)
    home_team['name'] = home_name
    away_team['name'] = away_name

    # Venue/location from matchup-commentary
    venue_info = _parse_venue(tile)

    # Conference section
    section = tile.find_parent('section', class_='score-set')
    conference_id = section.get('data-conference', '') if section else ''

    # Use data-key from tile if available, otherwise generate one
    d1bb_key = tile.get('data-key', '')
    if not d1bb_key:
        key_str = f"{date.strftime('%Y%m%d')}_{home_name}_{away_name}_{matchup_time}"
        d1bb_key = hashlib.md5(key_str.encode()).hexdigest()

    return {
        'd1bb_key': d1bb_key,
        'date': game_dt.isoformat(),
        'date_display': game_dt.strftime('%a, %b %d %Y'),
        'home_team': home_team,
        'away_team': away_team,
        'venue': venue_info,
        'status': status,
        'time_detail': time_detail,
        'conference_id': conference_id,
    }


def _parse_team_from_tile(tile, side: str) -> Dict:
    """Parse team info from a score tile for home or road side.

    Team divs use classes: .team.team-1 (away/road) and .team.team-2 (home).
    """
    # team-1 = away/road, team-2 = home
    target_class = 'team-2' if side == 'home' else 'team-1'

    team_id = ''
    rank = None
    record = ''
    logo_url = ''

    div = tile.find('div', class_=target_class)
    if div:
        team_id = div.get('data-team-id', '')

        # Rank: <span class="team-rank">16</span>
        rank_el = div.find('span', class_='team-rank')
        if rank_el:
            rank_text = rank_el.get_text(strip=True).replace('#', '')
            try:
                rank = int(rank_text)
            except ValueError:
                rank = None

        # Record: <small>(42-16, 22-8 Big Ten)</small>
        small_el = div.find('small')
        if small_el:
            record = small_el.get_text(strip=True).strip('()')

        # Logo: img inside a.team-logo
        logo_link = div.find('a', class_='team-logo')
        if logo_link:
            img = logo_link.find('img')
            if img:
                logo_url = img.get('src', '')

    return {
        'name': '',
        'id': team_id,
        'rank': rank,
        'record': record,
        'logo_url': logo_url,
    }


def _parse_venue(tile) -> Dict:
    """Parse venue information from a score tile.

    Commentary formats observed:
    - "Ponce, Puerto Rico"
    - "Arlington, Texas, Globe Life Field"
    - "Chapel Hill, Boshamer Stadium"
    - "Chapel Hill, NC"
    - "Baton Rouge, La. (Alex Box Stadium, Skip Bertman Field)"
    - "Surprise, Ariz. (Surprise Stadium)"
    """
    venue_name = ''
    city = ''
    state = ''

    import re

    commentary = tile.find('span', class_='matchup-commentary')
    if not commentary:
        commentary = tile.find('div', class_='matchup-commentary')

    if commentary:
        text = commentary.get_text(strip=True)

        # Extract parenthetical stadium name first, before splitting on commas
        paren_match = re.search(r'\(([^)]+)\)', text)
        if paren_match:
            venue_name = paren_match.group(1).strip()
            # Remove the parenthetical from text for city/state parsing
            text = text[:paren_match.start()].strip().rstrip(',').strip()

        parts = [p.strip() for p in text.split(',') if p.strip()]

        # US state abbreviations: "NC", "S.C.", "N.C.", "La.", "Ariz.", etc.
        state_pattern = re.compile(r'^[A-Z][a-z]*\.?[A-Z]?\.?$')
        state_abbr_pattern = re.compile(r'^[A-Z]{2}$|^[A-Z][a-z]+\.$')

        us_states = {
            'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
            'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
            'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
            'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
            'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
            'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
            'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
            'Pennsylvania', 'Puerto Rico', 'Rhode Island', 'South Carolina',
            'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia',
            'Washington', 'West Virginia', 'Wisconsin', 'Wyoming',
        }

        def _is_state(s):
            """Check if string looks like a state name or abbreviation."""
            if not s:
                return False
            if s in us_states:
                return True
            # Two-letter abbrevs: NC, FL, TX, etc.
            if re.match(r'^[A-Z]{2}$', s):
                return True
            # Abbreviated state names: La., Ariz., Calif., etc.
            if re.match(r'^[A-Z][a-z]+\.$', s):
                return True
            # Dotted abbreviations: N.C., S.C., etc.
            if re.match(r'^[A-Z]\.?[A-Z]\.?$', s):
                return True
            return False

        if len(parts) == 1:
            city = parts[0]
        elif len(parts) == 2:
            city = parts[0]
            if _is_state(parts[1]):
                state = parts[1]
            elif not venue_name:
                # If no parenthetical venue, this might be a venue name
                venue_name = parts[1]
        elif len(parts) >= 3:
            city = parts[0]
            if _is_state(parts[1]):
                state = parts[1]
                if not venue_name:
                    venue_name = ', '.join(parts[2:])
            else:
                state = parts[1]
                if not venue_name:
                    venue_name = ', '.join(parts[2:])

    return {
        'name': venue_name,
        'city': city,
        'state': state,
    }


def scrape_season_schedule(
    start_date: datetime,
    end_date: datetime,
    delay: float = 0.5,
) -> List[Dict]:
    """
    Scrape games for a date range, deduplicating by d1bb_key.

    Args:
        start_date: First date to scrape
        end_date: Last date to scrape (inclusive)
        delay: Seconds to wait between requests

    Returns:
        List of all unique games found
    """
    games_by_key = {}
    current = start_date
    total_days = (end_date - start_date).days + 1

    print(f"Scraping schedule from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({total_days} days)")

    day_num = 0
    while current <= end_date:
        day_num += 1
        date_str = current.strftime('%Y-%m-%d')
        games = fetch_games_for_date(current)

        if games:
            print(f"  [{day_num}/{total_days}] {date_str}: {len(games)} games")
            for g in games:
                games_by_key[g['d1bb_key']] = g
        else:
            print(f"  [{day_num}/{total_days}] {date_str}: no games")

        current += timedelta(days=1)
        if current <= end_date:
            time.sleep(delay)

    result = list(games_by_key.values())
    print(f"Total: {len(result)} unique games scraped")
    return result


def save_schedule_cache(games: List[Dict]) -> None:
    """Save games to schedule cache file, merging with existing cache by key."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing cache and merge by key
    merged = {}
    if SCHEDULE_CACHE_FILE.exists():
        try:
            with open(SCHEDULE_CACHE_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            for g in existing.get('games', []):
                key = g.get('d1bb_key')
                if key:
                    merged[key] = g
        except (json.JSONDecodeError, IOError):
            pass

    # New games overwrite existing ones with the same key
    for g in games:
        key = g.get('d1bb_key')
        if key:
            merged[key] = g

    all_games = list(merged.values())

    cache_data = {
        'updated': datetime.now().isoformat(),
        'game_count': len(all_games),
        'games': all_games,
    }

    with open(SCHEDULE_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)

    print(f"Schedule cache saved: {len(all_games)} games -> {SCHEDULE_CACHE_FILE}")


def load_schedule_cache() -> List[Dict]:
    """Load games from schedule cache file, deduplicating by d1bb_key."""
    if not SCHEDULE_CACHE_FILE.exists():
        return []

    try:
        with open(SCHEDULE_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        raw_games = cache_data.get('games', [])
        updated = cache_data.get('updated', 'unknown')

        # Defensive dedup by d1bb_key
        seen = {}
        for g in raw_games:
            key = g.get('d1bb_key')
            if key:
                seen[key] = g
            else:
                seen[id(g)] = g
        games = list(seen.values())

        print(f"Schedule cache loaded: {len(games)} unique games (updated: {updated})")
        return games
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading schedule cache: {e}")
        return []


def get_schedule(
    force_refresh: bool = False,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict]:
    """
    Cache-aware entry point for schedule data.

    Uses 1-day TTL on cache. If cache is fresh, returns cached data.
    Otherwise fetches fresh data.

    Args:
        force_refresh: If True, always re-fetch
        start_date: Start of date range (default: today)
        end_date: End of date range (default: 7 days from now)

    Returns:
        List of game dicts
    """
    # Check cache freshness
    if not force_refresh and SCHEDULE_CACHE_FILE.exists():
        try:
            with open(SCHEDULE_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            updated_str = cache_data.get('updated', '')
            if updated_str:
                updated = datetime.fromisoformat(updated_str)
                age = datetime.now() - updated
                if age < timedelta(days=1):
                    games = cache_data.get('games', [])
                    print(f"Using cached schedule ({len(games)} games, {age.seconds // 3600}h old)")
                    return games
        except (json.JSONDecodeError, IOError, ValueError):
            pass

    # Fetch fresh data — always start from today (past games are kept in cache)
    if start_date is None:
        start_date = datetime.now()
    if end_date is None:
        end_date = datetime(start_date.year, 6, 30)

    games = scrape_season_schedule(start_date, end_date)
    if games:
        save_schedule_cache(games)
    return games


def filter_upcoming_games(
    games: List[Dict],
    visited_venues: Optional[set] = None,
) -> List[Dict]:
    """
    Filter games to future, scheduled games at unvisited venues.

    Args:
        games: List of game dicts
        visited_venues: Set of venue names already visited (from STADIUM_DATA keys)

    Returns:
        Filtered list of upcoming games
    """
    now = datetime.now()
    upcoming = []

    for game in games:
        # Only scheduled games (not final/canceled)
        if game.get('status') not in ('scheduled', 'in_progress'):
            continue

        # Only future games
        try:
            game_dt = datetime.fromisoformat(game['date'])
            if game_dt < now:
                continue
        except (ValueError, KeyError):
            continue

        # If we have a visited venues list, filter to unvisited
        if visited_venues is not None:
            home_team = game.get('home_team', {}).get('name', '')
            if not _is_unvisited_venue(home_team, visited_venues):
                continue

        upcoming.append(game)

    # Sort by date
    upcoming.sort(key=lambda g: g.get('date', ''))
    return upcoming


def _is_unvisited_venue(home_team: str, visited_venues: set) -> bool:
    """
    Check if a home team's venue is unvisited.

    Matches against STADIUM_DATA keys using fuzzy matching.
    """
    if not home_team:
        return True  # Include if we can't determine

    # Direct match against STADIUM_DATA
    if home_team in STADIUM_DATA:
        return home_team not in visited_venues

    # Try common name variations
    for stadium_team in STADIUM_DATA:
        if venue_matches(home_team, stadium_team):
            return stadium_team not in visited_venues

    # Unknown venue - include it
    return True


def venue_matches(d1bb_name: str, stadium_name: str) -> bool:
    """
    Fuzzy match a D1Baseball team name against a STADIUM_DATA key.

    Handles common variations like abbreviations and alternate names.
    """
    if not d1bb_name or not stadium_name:
        return False

    # Exact match
    if d1bb_name == stadium_name:
        return True

    # Normalize for comparison
    d1_lower = d1bb_name.lower().strip()
    std_lower = stadium_name.lower().strip()

    if d1_lower == std_lower:
        return True

    # Common abbreviation patterns
    abbreviations = {
        'unc': 'north carolina',
        'usc': 'south carolina',
        'lsu': 'lsu',
        'tcu': 'tcu',
        'ucf': 'ucf',
        'fau': 'fau',
        'fiu': 'fiu',
        'uab': 'uab',
        'usf': 'usf',
        'vcu': 'vcu',
        'wku': 'wku',
        'fgcu': 'fgcu',
        'etsu': 'etsu',
    }

    for abbr, full in abbreviations.items():
        if d1_lower == abbr and std_lower == full:
            return True
        if std_lower == abbr and d1_lower == full:
            return True

    return False
