"""
NCAA Stats API client for fetching NCAA Division I baseball box scores.

Uses the free ncaa-api (https://github.com/henrygd/ncaa-api) which wraps
ncaa.com data into JSON endpoints. Public instance at ncaa-api.henrygd.me
with 5 req/sec rate limit. Can be self-hosted via Docker.

Endpoints used:
- /scoreboard/baseball/d1/{year}/{month}/{day}  -> game list
- /game/{gameID}/boxscore                       -> full player box scores
- /game/{gameID}/play-by-play                   -> play-by-play data
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add parent dir for shared utils
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from utils.http import create_retry_session, get_with_retry


NCAA_API_BASE = "https://ncaa-api.henrygd.me"

_session = create_retry_session()
_RATE_LIMIT_DELAY = 0.25  # 5 req/sec max


# --- Regex patterns for play-by-play extraction ---

_HR_PATTERN = re.compile(r'^(.+?)\s+homered\b', re.IGNORECASE)
_DOUBLE_PATTERN = re.compile(r'^(.+?)\s+doubled\b', re.IGNORECASE)
_TRIPLE_PATTERN = re.compile(r'^(.+?)\s+tripled\b', re.IGNORECASE)
_SB_PATTERN = re.compile(r'^(.+?)\s+stole\s+', re.IGNORECASE)

_NON_PLAY_TEXT = {'', 'null', 'none', 'no play', 'no play.'}


def _clean_team_name(short_name: str, full_name: str = '') -> str:
    """Build a clean display name from API team name fields.

    The API's nameShort often has abbreviations like 'St.', 'Ill.'.
    The nameFull has the full university name which is too long.
    This function picks the best display name.
    """
    if not short_name:
        return full_name or 'Unknown'

    # Expand common abbreviations in short names
    name = short_name
    name = re.sub(r'\bSt\.\s*$', 'State', name)       # "Murray St." -> "Murray State"
    name = re.sub(r'\bSt\.\s+', 'State ', name)        # "San Diego St." -> "San Diego State"
    name = re.sub(r'\bIll\.\s*$', 'Illinois', name)    # "Western Ill." -> "Western Illinois"
    name = re.sub(r'\bIll\.\s+', 'Illinois ', name)
    name = re.sub(r'\bMiss\.\s*$', 'Mississippi', name)
    name = re.sub(r'\bMiss\.\s+', 'Mississippi ', name)
    name = re.sub(r'\bMich\.\s*$', 'Michigan', name)
    name = re.sub(r'\bMich\.\s+', 'Michigan ', name)
    name = re.sub(r'\bMinn\.\s*$', 'Minnesota', name)
    name = re.sub(r'\bMinn\.\s+', 'Minnesota ', name)
    name = re.sub(r'\bWis\.\s*$', 'Wisconsin', name)
    name = re.sub(r'\bWis\.\s+', 'Wisconsin ', name)
    name = re.sub(r'\bInd\.\s*$', 'Indiana', name)
    name = re.sub(r'\bInd\.\s+', 'Indiana ', name)
    name = re.sub(r'\bConn\.\s*$', 'Connecticut', name)
    name = re.sub(r'\bConn\.\s+', 'Connecticut ', name)
    name = re.sub(r'\bTenn\.\s*$', 'Tennessee', name)
    name = re.sub(r'\bTenn\.\s+', 'Tennessee ', name)
    name = re.sub(r'\bFla\.\s*$', 'Florida', name)
    name = re.sub(r'\bFla\.\s+', 'Florida ', name)
    name = re.sub(r'\bGa\.\s*$', 'Georgia', name)
    name = re.sub(r'\bGa\.\s+', 'Georgia ', name)
    name = re.sub(r'\bAla\.\s*$', 'Alabama', name)
    name = re.sub(r'\bAla\.\s+', 'Alabama ', name)
    name = re.sub(r'\bOre\.\s*$', 'Oregon', name)
    name = re.sub(r'\bOre\.\s+', 'Oregon ', name)
    name = re.sub(r'\bArk\.\s*$', 'Arkansas', name)
    name = re.sub(r'\bArk\.\s+', 'Arkansas ', name)
    name = re.sub(r'\bMo\.\s*$', 'Missouri', name)
    name = re.sub(r'\bMo\.\s+', 'Missouri ', name)

    # Handle specific short names
    if name == 'FDU':
        name = 'Fairleigh Dickinson'

    # Strip trailing periods/whitespace
    return name.strip().rstrip('.')


# --- API fetch functions ---

def fetch_scoreboard(year: int, month: int, day: int) -> Dict[str, Any]:
    """Fetch D1 baseball scoreboard for a specific date."""
    url = f"{NCAA_API_BASE}/scoreboard/baseball/d1/{year}/{month:02d}/{day:02d}"
    response = get_with_retry(url, session=_session)
    time.sleep(_RATE_LIMIT_DELAY)
    return response.json()


def fetch_boxscore(game_id: str) -> Dict[str, Any]:
    """Fetch box score for a specific game."""
    url = f"{NCAA_API_BASE}/game/{game_id}/boxscore"
    response = get_with_retry(url, session=_session)
    time.sleep(_RATE_LIMIT_DELAY)
    return response.json()


def fetch_play_by_play(game_id: str) -> Dict[str, Any]:
    """Fetch play-by-play for a specific game."""
    url = f"{NCAA_API_BASE}/game/{game_id}/play-by-play"
    response = get_with_retry(url, session=_session)
    time.sleep(_RATE_LIMIT_DELAY)
    return response.json()


def fetch_game_info(game_id: str) -> Dict[str, Any]:
    """Fetch basic game info (date, teams, venue) from /game/{id} endpoint."""
    url = f"{NCAA_API_BASE}/game/{game_id}"
    response = get_with_retry(url, session=_session)
    time.sleep(_RATE_LIMIT_DELAY)
    data = response.json()
    contests = data.get('contests', [])
    return contests[0] if contests else {}


# --- Stat parsing ---

def _safe_int(val) -> int:
    """Convert string or numeric value to int, defaulting to 0."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    """Convert string or numeric value to float, defaulting to 0.0."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _is_meaningful_play_text(value: Any) -> bool:
    text = str(value or '').strip().lower()
    return text not in _NON_PLAY_TEXT


def _player_name(player: Dict[str, Any]) -> str:
    """Build player name from API fields. firstName is often blank."""
    first = (player.get('firstName') or '').strip()
    last = (player.get('lastName') or '').strip()
    if first and last:
        return f"{first} {last}"
    return last or first or 'Unknown'


def _is_pitcher_stat_echo(player: Dict[str, Any], batter_stats: Dict[str, Any]) -> bool:
    """Detect NCAA API pitcher rows whose batterStats mirror pitching stats."""
    pitcher_stats = player.get('pitcherStats') or {}
    if not pitcher_stats:
        return False
    if (player.get('position') or '').strip():
        return False
    if _safe_int(batter_stats.get('atBats')) > 0:
        return False
    if _safe_float(pitcher_stats.get('inningsPitched')) <= 0 and _safe_int(pitcher_stats.get('battersFaced')) <= 0:
        return False

    mirror_fields = (
        ('hits', 'hitsAllowed'),
        ('runsScored', 'runsAllowed'),
        ('walks', 'walksAllowed'),
    )
    return any(
        _safe_int(batter_stats.get(batter_key)) == _safe_int(pitcher_stats.get(pitcher_key)) > 0
        for batter_key, pitcher_key in mirror_fields
    )


def parse_ncaa_api_batting(player_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse batting stats from NCAA API boxscore playerStats.

    Returns list of batter dicts in canonical format, ordered:
    starters first (by array position), then substitutes.
    """
    batters = []
    for player in player_stats:
        batter_stats = player.get('batterStats')
        if not batter_stats:
            continue
        if not player.get('participated', False):
            continue
        if _is_pitcher_stat_echo(player, batter_stats):
            continue

        field_stats = player.get('fieldStats') or {}

        batter = {
            'name': _player_name(player),
            'full_name': _player_name(player),
            'position': (player.get('position') or '').upper(),
            'number': str(player.get('number', '')),
            'ab': _safe_int(batter_stats.get('atBats')),
            'r': _safe_int(batter_stats.get('runsScored')),
            'h': _safe_int(batter_stats.get('hits')),
            'rbi': _safe_int(batter_stats.get('runsBattedIn')),
            'bb': _safe_int(batter_stats.get('walks')),
            'k': _safe_int(batter_stats.get('strikeouts')),
            'po': _safe_int(field_stats.get('putouts')),
            'a': _safe_int(field_stats.get('assists')),
            'lob': 0,  # not provided by API
            # Extra-base / baserunning — filled from PBP later
            'doubles': 0,
            'triples': 0,
            'hr': 0,
            'sb': 0,
            # Ordering metadata
            '_starter': player.get('starter', False),
        }

        # Only include players with plate appearances
        if batter['ab'] > 0 or batter['bb'] > 0:
            batters.append(batter)

    # Starters first (preserve API order which is lineup order), then subs
    starters = [b for b in batters if b.get('_starter')]
    subs = [b for b in batters if not b.get('_starter')]
    for b in starters + subs:
        b.pop('_starter', None)
    return starters + subs


def parse_ncaa_api_pitching(player_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse pitching stats from NCAA API boxscore playerStats.

    Returns list of pitcher dicts in canonical format, preserving API order
    (which is appearance order).
    """
    pitchers = []
    for player in player_stats:
        pitcher_stats = player.get('pitcherStats')
        if not pitcher_stats:
            continue

        ip_raw = pitcher_stats.get('inningsPitched', '0.0')

        pitcher = {
            'name': _player_name(player),
            'full_name': _player_name(player),
            'number': str(player.get('number', '')),
            'ip': str(ip_raw),
            'h': _safe_int(pitcher_stats.get('hitsAllowed')),
            'r': _safe_int(pitcher_stats.get('runsAllowed')),
            'er': _safe_int(pitcher_stats.get('earnedRunsAllowed')),
            'bb': _safe_int(pitcher_stats.get('walksAllowed')),
            'k': _safe_int(pitcher_stats.get('strikeouts')),
            'bf': _safe_int(pitcher_stats.get('battersFaced')),
            'np': _safe_int(pitcher_stats.get('strikes')),  # best available proxy for pitch count
            'hr': 0,  # not in pitcher stats; could extract from PBP
            # Win/Loss/Save
            'win': str(pitcher_stats.get('win', '')).lower() in ('true', '1', 'yes'),
            'loss': str(pitcher_stats.get('loss', '')).lower() in ('true', '1', 'yes'),
            'save': str(pitcher_stats.get('save', '')).lower() in ('true', '1', 'yes'),
        }

        # Only include pitchers who actually pitched
        if pitcher['ip'] != '0.0' or pitcher['bf'] > 0:
            pitchers.append(pitcher)

    return pitchers


# --- Play-by-play extraction ---

def _normalize_pbp_name(name: str) -> str:
    """Normalize a player name from play-by-play text for matching."""
    name = name.strip().rstrip(',').lower()
    name = re.sub(r'\s+', ' ', name)
    return name


def extract_game_notes_from_pbp(pbp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract home runs, doubles, triples, stolen bases from play-by-play text.

    Returns dict in the same format as parsers/game_notes.py output:
    {
        "home_runs": [{"player": "Name", "game_count": N, "season_total": None}],
        "doubles": [...],
        "triples": [...],
        "stolen_bases": [...],
    }
    """
    hr_counts = Counter()
    double_counts = Counter()
    triple_counts = Counter()
    sb_counts = Counter()

    for period in pbp_data.get('periods', []):
        for stat_entry in period.get('playbyplayStats', []):
            for play in stat_entry.get('plays', []):
                text = play.get('playText', '')
                if not text:
                    continue

                m = _HR_PATTERN.match(text)
                if m:
                    hr_counts[_normalize_pbp_name(m.group(1))] += 1
                    continue

                m = _DOUBLE_PATTERN.match(text)
                if m:
                    double_counts[_normalize_pbp_name(m.group(1))] += 1
                    continue

                m = _TRIPLE_PATTERN.match(text)
                if m:
                    triple_counts[_normalize_pbp_name(m.group(1))] += 1
                    continue

                m = _SB_PATTERN.match(text)
                if m:
                    sb_counts[_normalize_pbp_name(m.group(1))] += 1

    def _to_notes_list(counts: Counter) -> List[Dict[str, Any]]:
        return [
            {'player': name, 'game_count': count, 'season_total': None}
            for name, count in counts.items()
        ]

    return {
        'home_runs': _to_notes_list(hr_counts),
        'doubles': _to_notes_list(double_counts),
        'triples': _to_notes_list(triple_counts),
        'stolen_bases': _to_notes_list(sb_counts),
    }


def _name_tokens(name: str) -> List[str]:
    return re.findall(r'[a-z0-9]+', (name or '').lower())


def _batter_match_keys(name: str) -> Dict[str, Any]:
    tokens = _name_tokens(name)
    if not tokens:
        return {'exact': '', 'first_initial': '', 'last_keys': []}

    suffixes = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
    first_initial = tokens[0][0]
    last_keys = [tokens[-1]]
    if tokens[-1] in suffixes and len(tokens) >= 2:
        last_keys.insert(0, f"{tokens[-2]} {tokens[-1]}")
        last_keys.append(tokens[-2])
    return {
        'exact': ' '.join(tokens),
        'first_initial': first_initial,
        'last_keys': last_keys,
    }


def _build_batter_note_indexes(batters: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_exact = {}
    by_last: Dict[str, List[Dict[str, Any]]] = {}
    by_last_initial: Dict[tuple[str, str], List[Dict[str, Any]]] = {}

    for batter in batters:
        keys = _batter_match_keys(batter.get('name', ''))
        if keys['exact']:
            by_exact[keys['exact']] = batter
        for last_key in keys['last_keys']:
            by_last.setdefault(last_key, []).append(batter)
            if keys['first_initial']:
                by_last_initial.setdefault((last_key, keys['first_initial']), []).append(batter)

    return {
        'by_exact': by_exact,
        'by_last': by_last,
        'by_last_initial': by_last_initial,
    }


def _unique_match(matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return matches[0] if len(matches) == 1 else None


def _match_pbp_note_to_batter(note_player: str, indexes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Match a PBP note name to one batter without guessing on duplicate surnames."""
    note_player = note_player or ''
    tokens = _name_tokens(note_player)
    if not tokens:
        return None

    if ',' in note_player:
        last_part, initial_part = note_player.split(',', 1)
        last_key = ' '.join(_name_tokens(last_part))
        initial_tokens = _name_tokens(initial_part)
        initial = initial_tokens[0][0] if initial_tokens and initial_tokens[0] else ''
        if last_key and initial:
            return _unique_match(indexes['by_last_initial'].get((last_key, initial), []))

    exact = ' '.join(tokens)
    if exact in indexes['by_exact']:
        return indexes['by_exact'][exact]

    return _unique_match(indexes['by_last'].get(exact, []))


def _enrich_batters_from_pbp(batters: List[Dict[str, Any]], game_notes: Dict[str, Any]):
    """Set per-batter HR/2B/3B/SB from PBP-extracted game notes.

    Matches exact names, comma-initial names like "Aloy, W.", or unique surnames.
    """
    indexes = _build_batter_note_indexes(batters)
    note_to_stat = {
        'home_runs': 'hr',
        'doubles': 'doubles',
        'triples': 'triples',
        'stolen_bases': 'sb',
    }
    for note_key, stat_key in note_to_stat.items():
        for note in game_notes.get(note_key, []):
            batter = _match_pbp_note_to_batter(str(note.get('player', '')), indexes)
            if batter:
                batter[stat_key] += _safe_int(note.get('game_count'),)


def parse_play_by_play_canonical(
    pbp_data: Dict[str, Any],
    home_team_id: int,
) -> Dict[str, Any]:
    """Convert NCAA API play-by-play to canonical innings format.

    Returns:
        {1: {"top": [{"description": "...", "rbi": 0}], "bottom": [...]}, ...}
    """
    innings = {}

    for period in pbp_data.get('periods', []):
        inning_num = period.get('periodNumber', 0)
        if not inning_num:
            continue

        top_plays = []
        bottom_plays = []

        for stat_entry in period.get('playbyplayStats', []):
            team_id = stat_entry.get('teamId')
            is_home = (team_id == home_team_id)

            for play in stat_entry.get('plays', []):
                play_dict = {
                    'description': play.get('playText', ''),
                    'pitch_count': None,
                    'rbi': 0,
                }
                # Extract RBI count from text like "2 RBI" or ", RBI"
                rbi_match = re.search(r'(\d+)\s*RBI', play.get('playText', ''))
                if rbi_match:
                    play_dict['rbi'] = int(rbi_match.group(1))
                elif ', RBI' in play.get('playText', ''):
                    play_dict['rbi'] = 1

                if is_home:
                    bottom_plays.append(play_dict)
                else:
                    top_plays.append(play_dict)

        innings[inning_num] = {
            'top': top_plays,
            'bottom': bottom_plays,
        }

    return innings


# --- Core boxscore assembly ---

def parse_boxscore(
    boxscore_data: Dict[str, Any],
    pbp_data: Optional[Dict[str, Any]] = None,
    scoreboard_game: Optional[Dict[str, Any]] = None,
    game_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Parse NCAA API boxscore into canonical game JSON format.

    Args:
        boxscore_data: Raw /game/{id}/boxscore response
        pbp_data: Raw /game/{id}/play-by-play response (for game_notes extraction)
        scoreboard_game: Scoreboard entry for this game (for enriched metadata)
        game_info: Raw /game/{id} contest data (for date/venue when no scoreboard)

    Returns:
        Game data dict in canonical processor format.
    """
    # Identify home/away teams from boxscore isHome flag
    teams = boxscore_data.get('teams', [])
    team_map = {}  # teamId -> team info
    home_team_id = None
    away_team_id = None
    for t in teams:
        tid = int(t.get('teamId', 0))
        team_map[tid] = t
        if t.get('isHome'):
            home_team_id = tid
        else:
            away_team_id = tid

    # Correct home/away using PBP: the team that bats first (top of 1st) is away.
    # The API's isHome flag is sometimes wrong.
    if pbp_data and home_team_id and away_team_id:
        first_period = None
        for period in pbp_data.get('periods', []):
            if period.get('periodNumber') == 1:
                first_period = period
                break
        if first_period:
            first_batter_team_id = None
            for stat_entry in first_period.get('playbyplayStats', []):
                meaningful_plays = [
                    play
                    for play in stat_entry.get('plays', [])
                    if _is_meaningful_play_text(play.get('playText'))
                ]
                if meaningful_plays:
                    first_batter_team_id = stat_entry.get('teamId')
                    break
            if first_batter_team_id is not None:
                first_batter_team_id = int(first_batter_team_id)
                # The team that bats first is the away team
                if first_batter_team_id == home_team_id:
                    # isHome flag was wrong — swap
                    home_team_id, away_team_id = away_team_id, home_team_id

    # Parse box scores by team
    away_batters = []
    home_batters = []
    away_pitchers = []
    home_pitchers = []

    for team_box in boxscore_data.get('teamBoxscore', []):
        tid = int(team_box.get('teamId', 0))
        players = team_box.get('playerStats', [])

        batters = parse_ncaa_api_batting(players)
        pitchers = parse_ncaa_api_pitching(players)

        if tid == home_team_id:
            home_batters = batters
            home_pitchers = pitchers
        else:
            away_batters = batters
            away_pitchers = pitchers

    # Extract game notes from play-by-play
    game_notes = {}
    play_by_play = {}
    if pbp_data:
        game_notes = extract_game_notes_from_pbp(pbp_data)
        # Enrich individual batter records with PBP-extracted stats
        _enrich_batters_from_pbp(away_batters, game_notes)
        _enrich_batters_from_pbp(home_batters, game_notes)
        # Parse canonical play-by-play
        if home_team_id:
            play_by_play = parse_play_by_play_canonical(pbp_data, home_team_id)

    # Build metadata from scoreboard entry if available, else from boxscore
    home_info = team_map.get(home_team_id, {})
    away_info = team_map.get(away_team_id, {})

    if scoreboard_game:
        sg = scoreboard_game
        home_data = sg.get('home', {})
        away_data = sg.get('away', {})
        date_str = sg.get('startDate', '')
        away_team_name = away_data.get('names', {}).get('short', away_info.get('nameShort', ''))
        home_team_name = home_data.get('names', {}).get('short', home_info.get('nameShort', ''))
        away_score = _safe_int(away_data.get('score'))
        home_score = _safe_int(home_data.get('score'))
        away_conf = (away_data.get('conferences', [{}])[0].get('conferenceSeo', '')
                     if away_data.get('conferences') else '')
        home_conf = (home_data.get('conferences', [{}])[0].get('conferenceSeo', '')
                     if home_data.get('conferences') else '')
    else:
        # Try to get date from game_info endpoint (startTimeEpoch)
        date_str = ''
        if game_info and game_info.get('startTimeEpoch'):
            try:
                epoch = int(game_info['startTimeEpoch'])
                # Epoch is midnight UTC; use US Eastern offset (+4h) to get correct date
                date_obj = datetime.utcfromtimestamp(epoch + 4 * 3600)
                date_str = date_obj.strftime('%m/%d/%Y')
            except (ValueError, TypeError, OSError):
                pass

        away_team_name = away_info.get('nameShort', away_info.get('nameFull', ''))
        home_team_name = home_info.get('nameShort', home_info.get('nameFull', ''))
        # Calculate scores from batting stats
        away_score = sum(b.get('r', 0) for b in away_batters)
        home_score = sum(b.get('r', 0) for b in home_batters)
        away_conf = ''
        home_conf = ''

    # Parse date
    date_display = date_str
    date_yyyymmdd = ''
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            date_yyyymmdd = date_obj.strftime('%Y%m%d')
            date_display = date_str
        except ValueError:
            pass

    game_data = {
        'metadata': {
            'date': date_display,
            'date_yyyymmdd': date_yyyymmdd,
            'away_team': away_team_name,
            'away_team_short': away_info.get('name6Char', ''),
            'away_team_id': away_team_id,
            'home_team': home_team_name,
            'home_team_short': home_info.get('name6Char', ''),
            'home_team_id': home_team_id,
            'away_team_score': away_score,
            'home_team_score': home_score,
            'away_team_record': '',
            'home_team_record': '',
            'venue': '',
            'conference': {
                'away': away_conf,
                'home': home_conf,
            },
            'source': 'ncaa_api',
        },
        'box_score': {
            'away_batting': away_batters,
            'home_batting': home_batters,
            'away_pitching': away_pitchers,
            'home_pitching': home_pitchers,
        },
        'game_notes': game_notes,
        'play_by_play': play_by_play,
        'format': 'ncaa_api',
    }

    return game_data


# --- Processing with caching ---

def process_ncaa_api_game(
    game_id: str,
    cache_dir: Optional[Path] = None,
    scoreboard_game: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fetch and process a single NCAA API game, with optional caching.

    Args:
        game_id: NCAA game ID (numeric string from scoreboard)
        cache_dir: Optional cache directory
        scoreboard_game: Optional scoreboard entry for metadata enrichment

    Returns:
        Processed game data dict in canonical format
    """
    # Check cache first
    if cache_dir:
        cache_file = cache_dir / f"ncaa_api_{game_id}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

    print(f"  Fetching NCAA API game {game_id}...")
    boxscore = fetch_boxscore(game_id)

    # Fetch play-by-play for extra-base hit extraction
    pbp_data = None
    try:
        pbp_data = fetch_play_by_play(game_id)
    except Exception as e:
        print(f"    Warning: Could not fetch play-by-play for {game_id}: {e}")

    # Fetch game info for date/venue when no scoreboard entry provided
    game_info = None
    if not scoreboard_game:
        try:
            game_info = fetch_game_info(game_id)
        except Exception as e:
            print(f"    Warning: Could not fetch game info for {game_id}: {e}")

    game_data = parse_boxscore(boxscore, pbp_data, scoreboard_game, game_info)
    game_data['metadata']['game_id'] = game_id

    # Save to cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"ncaa_api_{game_id}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2)

    return game_data


def load_game_ids(game_ids_file: Path) -> List[str]:
    """Load game IDs from a text file (one per line, # comments)."""
    if not game_ids_file.exists():
        return []

    game_ids = []
    with open(game_ids_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Strip inline comments
            if '#' in line:
                line = line[:line.index('#')].strip()
            if line:
                game_ids.append(line)

    return game_ids


def process_all_ncaa_api_games(
    game_ids_file: Path,
    cache_dir: Path,
) -> List[Dict[str, Any]]:
    """Process all NCAA API games listed in the game IDs file."""
    game_ids = load_game_ids(game_ids_file)
    if not game_ids:
        return []

    print(f"Processing {len(game_ids)} NCAA API games...")
    games = []

    for game_id in game_ids:
        try:
            game_data = process_ncaa_api_game(game_id, cache_dir)
            games.append(game_data)
            meta = game_data['metadata']
            print(f"  {meta.get('date', '?')}: {meta['away_team']} @ {meta['home_team']} "
                  f"({meta['away_team_score']}-{meta['home_team_score']})")
        except Exception as e:
            print(f"  Error processing NCAA API game {game_id}: {e}")

    return games


# --- Date-range discovery ---

def discover_games_for_date(year: int, month: int, day: int) -> List[Dict[str, Any]]:
    """Fetch scoreboard and return list of completed game entries.

    Returns list of scoreboard game dicts (each has 'gameID' and team info).
    """
    try:
        data = fetch_scoreboard(year, month, day)
    except Exception as e:
        print(f"  Warning: Could not fetch scoreboard for {year}-{month:02d}-{day:02d}: {e}")
        return []

    completed = []
    for entry in data.get('games', []):
        game = entry.get('game', entry)
        if game.get('gameState', '').lower() == 'final':
            completed.append(game)

    return completed


def discover_games_for_date_range(
    start_date: datetime,
    end_date: datetime,
) -> List[Dict[str, Any]]:
    """Discover completed games for a date range by scraping scoreboards."""
    all_games = []
    current = start_date

    while current <= end_date:
        print(f"  Checking scoreboard: {current.strftime('%Y-%m-%d')}...")
        day_games = discover_games_for_date(current.year, current.month, current.day)
        all_games.extend(day_games)
        current += timedelta(days=1)

    print(f"  Found {len(all_games)} completed games in date range")
    return all_games


def process_ncaa_api_date_range(
    start_date: datetime,
    end_date: datetime,
    cache_dir: Path,
) -> List[Dict[str, Any]]:
    """Discover games for date range, then process each.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        cache_dir: Cache directory

    Returns:
        List of processed game data dicts
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    scoreboard_games = discover_games_for_date_range(start_date, end_date)

    print(f"Processing {len(scoreboard_games)} NCAA API games...")
    games = []
    errors = 0

    for sg in scoreboard_games:
        game_id = str(sg.get('gameID', ''))
        if not game_id:
            continue

        try:
            game_data = process_ncaa_api_game(game_id, cache_dir, scoreboard_game=sg)
            games.append(game_data)
            meta = game_data['metadata']
            print(f"    {meta.get('date', '?')}: {meta['away_team']} @ {meta['home_team']} "
                  f"({meta['away_team_score']}-{meta['home_team_score']})")
        except Exception as e:
            print(f"    Error processing game {game_id}: {e}")
            errors += 1

    if errors:
        print(f"  {errors} games failed to process")

    return games


# --- Standalone usage ---

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='NCAA API game fetcher')
    parser.add_argument('game_id', nargs='?', help='Single game ID to fetch')
    parser.add_argument('--date', help='Fetch all games for a date (YYYY-MM-DD)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                        help='Fetch games for date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--cache-dir', default=None, help='Cache directory')

    args = parser.parse_args()
    cache = Path(args.cache_dir) if args.cache_dir else None

    if args.date:
        dt = datetime.strptime(args.date, '%Y-%m-%d')
        games = process_ncaa_api_date_range(dt, dt, cache or Path('ncaa_api/cache'))
        print(f"\nProcessed {len(games)} games")

    elif args.date_range:
        start = datetime.strptime(args.date_range[0], '%Y-%m-%d')
        end = datetime.strptime(args.date_range[1], '%Y-%m-%d')
        games = process_ncaa_api_date_range(start, end, cache or Path('ncaa_api/cache'))
        print(f"\nProcessed {len(games)} games")

    elif args.game_id:
        game_data = process_ncaa_api_game(args.game_id, cache)
        meta = game_data['metadata']
        print(f"\nGame: {meta['away_team']} @ {meta['home_team']}")
        print(f"Date: {meta['date']}")
        print(f"Score: {meta['away_team_score']} - {meta['home_team_score']}")
        print(f"\nAway batters: {len(game_data['box_score']['away_batting'])}")
        print(f"Home batters: {len(game_data['box_score']['home_batting'])}")
        print(f"Away pitchers: {len(game_data['box_score']['away_pitching'])}")
        print(f"Home pitchers: {len(game_data['box_score']['home_pitching'])}")

        # Show game notes
        notes = game_data.get('game_notes', {})
        if notes.get('home_runs'):
            print(f"\nHome Runs: {', '.join(n['player'] + (' x' + str(n['game_count']) if n['game_count'] > 1 else '') for n in notes['home_runs'])}")
        if notes.get('doubles'):
            print(f"Doubles: {', '.join(n['player'] for n in notes['doubles'])}")
        if notes.get('stolen_bases'):
            print(f"Stolen Bases: {', '.join(n['player'] for n in notes['stolen_bases'])}")

        # Print JSON for inspection
        print(f"\n--- Full JSON ({len(json.dumps(game_data))} chars) ---")
        print(json.dumps(game_data, indent=2)[:2000])

    else:
        parser.print_help()
