"""
Website generator for interactive HTML output.
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

from ..engines.milestone_engine import build_extra_base_lookup, get_player_extra_stats
from ..normalization import build_player_name_aliases, normalize_game, resolve_player_name_alias
from ..utils.stadiums import STADIUM_DATA, NCAA_TEAM_LOGOS, NCAA_TEAM_NICKNAMES
from ..utils.milb_stadiums import MILB_STADIUM_DATA, HISTORIC_MILB_TEAMS, LOGO_OVERRIDES, HISTORICAL_TEAM_LOGOS
from ..utils.partner_stadiums import PARTNER_TEAM_DATA, get_partner_stadium_locations
from ..utils.constants import (CONFERENCES, get_conference, SPORT_LEVEL_MAP, LEAGUE_LEVEL_MAP,
                                PRO_LEVELS, LEVEL_ORDER, LEVEL_COLORS, resolve_level_and_league)
from ..utils.helpers import is_placeholder_player_name, normalize_team_name, resolve_player_display_name
from ..utils.player_ids import PlayerIDMapper
from .parity import collect_website_data_parity_issues
from .serializers import count_notable_milestones, df_to_list, scrub_json_value, serialize_milestones


# Map team names to local logo filenames in the logos/ directory
LOCAL_LOGO_MAP = {
    # NCAA teams without ESPN logos
    'San Francisco State': 'San_Francisco_State.png',
    'Cal Poly Pomona': 'Cal_Poly_Pomona.png',
    # Partner/Independent league teams - Pioneer League
    'Billings Mustangs': 'Billings_Mustangs.png',
    'Boise Hawks': 'Boise_Hawks.png',
    'Glacier Range Riders': 'Glacier_Range_Riders.png',
    'Great Falls Voyagers': 'Great_Falls_Voyagers.png',
    'Idaho Falls Chukars': 'Idaho_Falls_Chukars.png',
    'Long Beach Coast': 'Long_Beach_Coast.png',
    'Missoula PaddleHeads': 'Missoula_PaddleHeads.png',
    'Modesto Roadsters': 'Modesto_Roadsters.png',
    'Oakland Ballers': 'Oakland_Ballers.png',
    'Ogden Raptors': 'Ogden_Raptors.png',
    'Yuba-Sutter High Wheelers': 'Yuba_Sutter_High_Wheelers.png',
    'RedPocket Mobiles': 'RedPocket_Mobiles.png',
    # Atlantic League
    'Charleston Dirty Birds': 'Charleston_Dirty_Birds.png',
    'Gastonia Ghost Peppers': 'Gastonia_Ghost_Peppers.png',
    'Hagerstown Flying Boxcars': 'Hagerstown_Flying_Boxcars.png',
    'High Point Rockers': 'High_Point_Rockers.png',
    'Lancaster Stormers': 'Lancaster_Stormers.png',
    'Lexington Legends': 'Lexington_Legends.png',
    'Long Island Ducks': 'Long_Island_Ducks.png',
    'Southern Maryland Blue Crabs': 'Southern_Maryland_Blue_Crabs.png',
    'Staten Island FerryHawks': 'Staten_Island_FerryHawks.png',
    'York Revolution': 'York_Revolution.png',
    # American Association
    'Fargo-Moorhead RedHawks': 'Fargo_Moorhead_RedHawks.png',
    'St. Paul Saints': 'St_Paul_Saints.png',
    'Cleburne Railroaders': 'Cleburne_Railroaders.png',
    'Kansas City Monarchs': 'Kansas_City_Monarchs.png',
    'Sioux Falls Canaries': 'Sioux_Falls_Canaries.png',
    'Winnipeg Goldeyes': 'Winnipeg_Goldeyes.png',
    'Lincoln Saltdogs': 'Lincoln_Saltdogs.png',
    'Chicago Dogs': 'Chicago_Dogs.png',
    'Gary SouthShore RailCats': 'Gary_SouthShore_RailCats.png',
    'Milwaukee Milkmen': 'Milwaukee_Milkmen.png',
    'Sioux City Explorers': 'Sioux_City_Explorers.png',
    'Kane County Cougars': 'Kane_County_Cougars.png',
    'Lake Country DockHounds': 'Lake_Country_DockHounds.png',
    # Frontier League
    'Brockton Rox': 'Brockton_Rox.png',
    'Down East Bird Dawgs': 'Down_East_Bird_Dawgs.png',
    'Evansville Otters': 'Evansville_Otters.png',
    "Florence Y'alls": 'Florence_Yalls.png',
    'Gateway Grizzlies': 'Gateway_Grizzlies.png',
    'Joliet Slammers': 'Joliet_Slammers.png',
    'Lake Erie Crushers': 'Lake_Erie_Crushers.png',
    'Mississippi Mud Monsters': 'Mississippi_Mud_Monsters.png',
    'New Jersey Jackals': 'New_Jersey_Jackals.png',
    'New York Boulders': 'New_York_Boulders.png',
    'Ottawa Titans': 'Ottawa_Titans.png',
    'Quebec Capitales': 'Quebec_Capitales.png',
    'Schaumburg Boomers': 'Schaumburg_Boomers.png',
    'Sussex County Miners': 'Sussex_County_Miners.png',
    'Tri-City ValleyCats': 'Tri_City_ValleyCats.png',
    'Trois-Rivières Aigles': 'Trois_Rivieres_Aigles.png',
    'Washington Wild Things': 'Washington_Wild_Things.png',
    'Windy City ThunderBolts': 'Windy_City_ThunderBolts.png',
    # Historic
    'Savannah Sand Gnats': 'Savannah_Sand_Gnats.png',
}

def _classify_and_id_raw_game(rg: Dict[str, Any]):
    """Return (game_id, source) for a raw game dict, or (None, None) if indeterminate."""
    normalized = normalize_game(rg)
    basic = normalized.get('basic_info', {})
    if not basic.get('date_yyyymmdd'):
        return None, None
    return normalized.get('game_id'), normalized.get('source')


def _build_raw_game_index(raw_games: List[Dict]) -> Dict:
    """Build lookup: (yyyymmdd, away, home, away_score, home_score) -> game record list."""
    index = {}
    seen_game_ids = {}
    for rg in raw_games or []:
        normalized = normalize_game(rg)
        base_gid = normalized.get('game_id')
        source = normalized.get('source')
        basic = normalized.get('basic_info', {})
        ymd = basic.get('date_yyyymmdd', '')
        if not base_gid or not ymd:
            continue
        count = seen_game_ids.get(base_gid, 0) + 1
        seen_game_ids[base_gid] = count
        gid = base_gid if count == 1 else f'{base_gid}_{count}'
        away = (basic.get('away_team', '') or '').lower().strip()
        home = (basic.get('home_team', '') or '').lower().strip()
        away_score = str(basic.get('away_score_value', '')).strip()
        home_score = str(basic.get('home_score_value', '')).strip()
        index.setdefault((ymd, away, home, away_score, home_score), []).append((gid, source, rg))
    return index


def _detail_batter_row(row: Dict[str, Any], extra_stats_lookup: Dict[str, Dict[str, int]] | None = None) -> Dict[str, Any]:
    """Convert a normalized batting row to the frontend detail-row contract."""
    name = row.get('name') or row.get('full_name') or ''
    extra_stats = get_player_extra_stats(name, extra_stats_lookup or {})
    doubles = extra_stats['2b'] or row.get('2B', 0)
    triples = extra_stats['3b'] or row.get('3B', 0)
    hr = extra_stats['hr'] or row.get('HR', 0)
    sb = extra_stats['sb'] or row.get('SB', 0)
    return {
        **row,
        'name': name,
        'full_name': row.get('full_name') or name,
        'player_id': row.get('player_id', ''),
        'bref_id': row.get('bref_id', ''),
        'ab': row.get('AB', 0),
        'r': row.get('R', 0),
        'h': row.get('H', 0),
        'rbi': row.get('RBI', 0),
        'bb': row.get('BB', 0),
        'k': row.get('SO', 0),
        '2B': doubles,
        '3B': triples,
        'HR': hr,
        'SB': sb,
        'doubles': doubles,
        'triples': triples,
        'hr': hr,
        'sb': sb,
        'cs': row.get('CS', 0),
    }


def _detail_pitcher_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a normalized pitching row to the frontend detail-row contract."""
    name = row.get('name') or row.get('full_name') or ''
    decision = row.get('decision', '')
    return {
        **row,
        'name': name,
        'full_name': row.get('full_name') or name,
        'player_id': row.get('player_id', ''),
        'bref_id': row.get('bref_id', ''),
        'ip': row.get('IP', '0'),
        'h': row.get('H', 0),
        'r': row.get('R', 0),
        'er': row.get('ER', 0),
        'bb': row.get('BB', 0),
        'k': row.get('SO', 0),
        'hr': row.get('HR', 0),
        'bf': row.get('batters_faced', 0),
        'np': row.get('pitches', 0),
        'decision': decision,
        'win': decision == 'W' or bool(row.get('win')),
        'loss': decision == 'L' or bool(row.get('loss')),
        'save': decision == 'S' or bool(row.get('save')),
    }


def _serialize_detail_box_score(normalized_game: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Serialize normalized game rows for the per-game detail JSON files."""
    batting = normalized_game.get('batting', {}) or {}
    pitching = normalized_game.get('pitching', {}) or {}
    extra_stats_lookup = build_extra_base_lookup(normalized_game.get('game_notes', {}) or {})

    def has_player_identity(row: Dict[str, Any]) -> bool:
        return not is_placeholder_player_name(row.get('full_name') or row.get('name'))

    return {
        'away_batting': [_detail_batter_row(row, extra_stats_lookup) for row in batting.get('away', []) if has_player_identity(row)],
        'home_batting': [_detail_batter_row(row, extra_stats_lookup) for row in batting.get('home', []) if has_player_identity(row)],
        'away_pitching': [_detail_pitcher_row(row) for row in pitching.get('away', []) if has_player_identity(row)],
        'home_pitching': [_detail_pitcher_row(row) for row in pitching.get('home', []) if has_player_identity(row)],
    }


def _build_per_game_details(raw_game_index: Dict, player_name_aliases: Dict | None = None) -> Dict[str, Dict[str, Any]]:
    """Build the game-detail payloads used by the modal and static JSON files."""
    details: Dict[str, Dict[str, Any]] = {}
    for records in raw_game_index.values():
        for (gid, source, rg) in records:
            normalized = normalize_game(rg, player_name_aliases=player_name_aliases)
            basic = normalized.get('basic_info', {}) or {}
            meta = rg.get('metadata', {}) or {}
            level = basic.get('level')
            sl = meta.get('sport_level')
            if not level and isinstance(sl, dict):
                level = sl.get('home') or sl.get('away')
            elif not level and isinstance(sl, str):
                level = sl

            detail = {
                'game_id': gid,
                'source': source,
                'date': basic.get('date', ''),
                'date_yyyymmdd': basic.get('date_yyyymmdd', ''),
                'away_team': basic.get('away_team', ''),
                'home_team': basic.get('home_team', ''),
                'away_team_id': meta.get('away_team_id'),
                'home_team_id': meta.get('home_team_id'),
                'away_score': basic.get('away_score_value', 0),
                'home_score': basic.get('home_score_value', 0),
                'venue': basic.get('venue', ''),
                'attendance': basic.get('attendance'),
                'weather': meta.get('weather'),
                'duration': meta.get('duration'),
                'start_time': meta.get('start_time'),
                'umpires': meta.get('umpires'),
                'league': meta.get('league') or basic.get('league'),
                'level': level,
                'box_score': _serialize_detail_box_score(normalized),
                'game_notes': normalized.get('game_notes', {}),
                'play_by_play': normalized.get('play_by_play', {}),
                'data_quality': rg.get('data_quality', {}),
            }
            details[gid] = detail
    return details


def _write_per_game_details(game_details: Dict[str, Dict[str, Any]], web_dir: Path) -> int:
    """Write one JSON file per game to web/public/games/ for lazy loading by the modal."""
    games_dir = web_dir / 'public' / 'games'
    games_dir.mkdir(parents=True, exist_ok=True)
    for existing in games_dir.glob('*.json'):
        existing.unlink()

    written = 0
    for gid, detail in game_details.items():
        out = games_dir / f'{gid}.json'
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(detail, f, separators=(',', ':'), default=str)
        written += 1
    return written


def _load_local_logos() -> Dict[str, str]:
    """Load local logo files from logos/ directory and return base64 data URIs."""
    logos_dir = Path(__file__).resolve().parent.parent.parent / 'logos'
    result = {}
    for team_name, filename in LOCAL_LOGO_MAP.items():
        logo_path = logos_dir / filename
        if logo_path.exists():
            data = logo_path.read_bytes()
            ext = filename.rsplit('.', 1)[-1].lower()
            mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'svg': 'image/svg+xml', 'webp': 'image/webp', 'gif': 'image/gif'}.get(ext, 'image/png')
            b64 = base64.b64encode(data).decode('ascii')
            result[team_name] = f'data:{mime};base64,{b64}'
    return result


def _team_id_for_name(team_name: str):
    """Return MiLB/Partner team id for a display team name."""
    for info in MILB_STADIUM_DATA.values():
        if info[2] == team_name:
            return info[4]
    if team_name in PARTNER_TEAM_DATA:
        return PARTNER_TEAM_DATA[team_name].get('id')
    return None


# Common D1 baseball venue cities → (lat, lng) for neutral-site / tournament games
VENUE_CITY_COORDS = {
    # Spring training / tournament hubs
    ('Surprise', 'AZ'): (33.6292, -112.3677),
    ('Surprise', 'Ariz.'): (33.6292, -112.3677),
    ('Surprise', 'Arizona'): (33.6292, -112.3677),
    ('Scottsdale', 'AZ'): (33.4942, -111.9261),
    ('Scottsdale', 'Ariz.'): (33.4942, -111.9261),
    ('Scottsdale', 'Arizona'): (33.4942, -111.9261),
    ('Mesa', 'AZ'): (33.4152, -111.8315),
    ('Mesa', 'Ariz.'): (33.4152, -111.8315),
    ('Mesa', 'Arizona'): (33.4152, -111.8315),
    ('Phoenix', 'AZ'): (33.4484, -112.0740),
    ('Phoenix', 'Ariz.'): (33.4484, -112.0740),
    ('Phoenix', 'Arizona'): (33.4484, -112.0740),
    ('Tempe', 'AZ'): (33.4255, -111.9400),
    ('Tempe', 'Ariz.'): (33.4255, -111.9400),
    ('Tempe', 'Arizona'): (33.4255, -111.9400),
    ('Glendale', 'AZ'): (33.5387, -112.1860),
    ('Glendale', 'Ariz.'): (33.5387, -112.1860),
    ('Glendale', 'Arizona'): (33.5387, -112.1860),
    ('Peoria', 'AZ'): (33.5806, -112.2374),
    ('Peoria', 'Ariz.'): (33.5806, -112.2374),
    ('Peoria', 'Arizona'): (33.5806, -112.2374),
    ('Goodyear', 'AZ'): (33.4353, -112.3577),
    ('Goodyear', 'Ariz.'): (33.4353, -112.3577),
    ('Goodyear', 'Arizona'): (33.4353, -112.3577),
    ('Tucson', 'AZ'): (32.2226, -110.9747),
    ('Tucson', 'Ariz.'): (32.2226, -110.9747),
    ('Tucson', 'Arizona'): (32.2226, -110.9747),
    # Florida tournament sites
    ('DeLand', 'FL'): (29.0283, -81.3031),
    ('DeLand', 'Fla.'): (29.0283, -81.3031),
    ('DeLand', 'Florida'): (29.0283, -81.3031),
    ('Lakeland', 'FL'): (28.0395, -81.9498),
    ('Lakeland', 'Fla.'): (28.0395, -81.9498),
    ('Lakeland', 'Florida'): (28.0395, -81.9498),
    ('Port Charlotte', 'FL'): (26.9767, -82.0906),
    ('Port Charlotte', 'Fla.'): (26.9767, -82.0906),
    ('Port Charlotte', 'Florida'): (26.9767, -82.0906),
    ('Clearwater', 'FL'): (27.9659, -82.8001),
    ('Clearwater', 'Fla.'): (27.9659, -82.8001),
    ('Clearwater', 'Florida'): (27.9659, -82.8001),
    ('Jupiter', 'FL'): (26.9342, -80.0942),
    ('Jupiter', 'Fla.'): (26.9342, -80.0942),
    ('Jupiter', 'Florida'): (26.9342, -80.0942),
    ('Fort Myers', 'FL'): (26.6406, -81.8723),
    ('Fort Myers', 'Fla.'): (26.6406, -81.8723),
    ('Fort Myers', 'Florida'): (26.6406, -81.8723),
    ('Bradenton', 'FL'): (27.4989, -82.5748),
    ('Bradenton', 'Fla.'): (27.4989, -82.5748),
    ('Bradenton', 'Florida'): (27.4989, -82.5748),
    ('Sarasota', 'FL'): (27.3364, -82.5307),
    ('Sarasota', 'Fla.'): (27.3364, -82.5307),
    ('Sarasota', 'Florida'): (27.3364, -82.5307),
    ('Kissimmee', 'FL'): (28.2920, -81.4076),
    ('Kissimmee', 'Fla.'): (28.2920, -81.4076),
    ('Kissimmee', 'Florida'): (28.2920, -81.4076),
    ('Dunedin', 'FL'): (28.0197, -82.7718),
    ('Dunedin', 'Fla.'): (28.0197, -82.7718),
    ('Dunedin', 'Florida'): (28.0197, -82.7718),
    ('Tampa', 'FL'): (27.9506, -82.4572),
    ('Tampa', 'Fla.'): (27.9506, -82.4572),
    ('Tampa', 'Florida'): (27.9506, -82.4572),
    ('Orlando', 'FL'): (28.5383, -81.3792),
    ('Orlando', 'Fla.'): (28.5383, -81.3792),
    ('Orlando', 'Florida'): (28.5383, -81.3792),
    ('Jacksonville', 'FL'): (30.3322, -81.6557),
    ('Jacksonville', 'Fla.'): (30.3322, -81.6557),
    ('Jacksonville', 'Florida'): (30.3322, -81.6557),
    ('Gainesville', 'FL'): (29.6516, -82.3248),
    ('Gainesville', 'Fla.'): (29.6516, -82.3248),
    ('Gainesville', 'Florida'): (29.6516, -82.3248),
    ('Tallahassee', 'FL'): (30.4383, -84.2807),
    ('Tallahassee', 'Fla.'): (30.4383, -84.2807),
    ('Tallahassee', 'Florida'): (30.4383, -84.2807),
    ('Miami', 'FL'): (25.7617, -80.1918),
    ('Miami', 'Fla.'): (25.7617, -80.1918),
    ('Miami', 'Florida'): (25.7617, -80.1918),
    # Texas tournament sites
    ('Arlington', 'TX'): (32.7357, -97.1081),
    ('Arlington', 'Texas'): (32.7357, -97.1081),
    ('Arlington', 'Tex.'): (32.7357, -97.1081),
    ('Houston', 'TX'): (29.7604, -95.3698),
    ('Houston', 'Texas'): (29.7604, -95.3698),
    ('Houston', 'Tex.'): (29.7604, -95.3698),
    ('San Antonio', 'TX'): (29.4241, -98.4936),
    ('San Antonio', 'Texas'): (29.4241, -98.4936),
    ('San Antonio', 'Tex.'): (29.4241, -98.4936),
    ('Dallas', 'TX'): (32.7767, -96.7970),
    ('Dallas', 'Texas'): (32.7767, -96.7970),
    ('Dallas', 'Tex.'): (32.7767, -96.7970),
    ('Round Rock', 'TX'): (30.5083, -97.6789),
    ('Round Rock', 'Texas'): (30.5083, -97.6789),
    ('Round Rock', 'Tex.'): (30.5083, -97.6789),
    ('Frisco', 'TX'): (33.1507, -96.8236),
    ('Frisco', 'Texas'): (33.1507, -96.8236),
    ('Frisco', 'Tex.'): (33.1507, -96.8236),
    ('Sugar Land', 'TX'): (29.6197, -95.6349),
    ('Sugar Land', 'Texas'): (29.6197, -95.6349),
    ('Sugar Land', 'Tex.'): (29.6197, -95.6349),
    ('Corpus Christi', 'TX'): (27.8006, -97.3964),
    ('Corpus Christi', 'Texas'): (27.8006, -97.3964),
    ('Corpus Christi', 'Tex.'): (27.8006, -97.3964),
    ('College Station', 'TX'): (30.6280, -96.3344),
    ('College Station', 'Texas'): (30.6280, -96.3344),
    ('College Station', 'Tex.'): (30.6280, -96.3344),
    # Puerto Rico
    ('Ponce', 'Puerto Rico'): (18.0111, -66.6141),
    ('San Juan', 'Puerto Rico'): (18.4655, -66.1057),
    ('Carolina', 'Puerto Rico'): (18.3811, -65.9574),
    ('Bayamon', 'Puerto Rico'): (18.3989, -66.1553),
    # Other common tournament / neutral sites
    ('Omaha', 'NE'): (41.2565, -95.9345),
    ('Omaha', 'Neb.'): (41.2565, -95.9345),
    ('Omaha', 'Nebraska'): (41.2565, -95.9345),
    ('Minneapolis', 'MN'): (44.9778, -93.2650),
    ('Minneapolis', 'Minn.'): (44.9778, -93.2650),
    ('Minneapolis', 'Minnesota'): (44.9778, -93.2650),
    ('Nashville', 'TN'): (36.1627, -86.7816),
    ('Nashville', 'Tenn.'): (36.1627, -86.7816),
    ('Nashville', 'Tennessee'): (36.1627, -86.7816),
    ('Charlotte', 'NC'): (35.2271, -80.8431),
    ('Charlotte', 'N.C.'): (35.2271, -80.8431),
    ('Charlotte', 'North Carolina'): (35.2271, -80.8431),
    ('Atlanta', 'GA'): (33.7490, -84.3880),
    ('Atlanta', 'Ga.'): (33.7490, -84.3880),
    ('Atlanta', 'Georgia'): (33.7490, -84.3880),
    ('Baton Rouge', 'LA'): (30.4515, -91.1871),
    ('Baton Rouge', 'La.'): (30.4515, -91.1871),
    ('Baton Rouge', 'Louisiana'): (30.4515, -91.1871),
    ('Hattiesburg', 'MS'): (31.3271, -89.2903),
    ('Hattiesburg', 'Miss.'): (31.3271, -89.2903),
    ('Hattiesburg', 'Mississippi'): (31.3271, -89.2903),
    ('Starkville', 'MS'): (33.4504, -88.8184),
    ('Starkville', 'Miss.'): (33.4504, -88.8184),
    ('Starkville', 'Mississippi'): (33.4504, -88.8184),
    ('Greenville', 'SC'): (34.8526, -82.3940),
    ('Greenville', 'S.C.'): (34.8526, -82.3940),
    ('Greenville', 'South Carolina'): (34.8526, -82.3940),
    ('Myrtle Beach', 'SC'): (33.6891, -78.8867),
    ('Myrtle Beach', 'S.C.'): (33.6891, -78.8867),
    ('Myrtle Beach', 'South Carolina'): (33.6891, -78.8867),
    ('Conway', 'SC'): (33.8360, -79.0478),
    ('Conway', 'S.C.'): (33.8360, -79.0478),
    ('Conway', 'South Carolina'): (33.8360, -79.0478),
    ('Fayetteville', 'AR'): (36.0626, -94.1574),
    ('Fayetteville', 'Ark.'): (36.0626, -94.1574),
    ('Fayetteville', 'Arkansas'): (36.0626, -94.1574),
    ('Norman', 'OK'): (35.2226, -97.4395),
    ('Norman', 'Okla.'): (35.2226, -97.4395),
    ('Norman', 'Oklahoma'): (35.2226, -97.4395),
    ('Stillwater', 'OK'): (36.1156, -97.0584),
    ('Stillwater', 'Okla.'): (36.1156, -97.0584),
    ('Stillwater', 'Oklahoma'): (36.1156, -97.0584),
    ('Corvallis', 'OR'): (44.5646, -123.2620),
    ('Corvallis', 'Ore.'): (44.5646, -123.2620),
    ('Corvallis', 'Oregon'): (44.5646, -123.2620),
    ('Eugene', 'OR'): (44.0521, -123.0868),
    ('Eugene', 'Ore.'): (44.0521, -123.0868),
    ('Eugene', 'Oregon'): (44.0521, -123.0868),
    ('Seattle', 'WA'): (47.6062, -122.3321),
    ('Seattle', 'Wash.'): (47.6062, -122.3321),
    ('Seattle', 'Washington'): (47.6062, -122.3321),
    ('Los Angeles', 'CA'): (34.0522, -118.2437),
    ('Los Angeles', 'Calif.'): (34.0522, -118.2437),
    ('Los Angeles', 'California'): (34.0522, -118.2437),
    ('San Diego', 'CA'): (32.7157, -117.1611),
    ('San Diego', 'Calif.'): (32.7157, -117.1611),
    ('San Diego', 'California'): (32.7157, -117.1611),
    ('Honolulu', 'HI'): (21.3069, -157.8583),
    ('Honolulu', 'Hawaii'): (21.3069, -157.8583),
    # College towns commonly appearing
    ('Chapel Hill', 'NC'): (35.9132, -79.0558),
    ('Chapel Hill', 'N.C.'): (35.9132, -79.0558),
    ('Charlottesville', 'VA'): (38.0293, -78.4767),
    ('Charlottesville', 'Va.'): (38.0293, -78.4767),
    ('Blacksburg', 'VA'): (37.2296, -80.4139),
    ('Blacksburg', 'Va.'): (37.2296, -80.4139),
    ('Clemson', 'SC'): (34.6834, -82.8374),
    ('Clemson', 'S.C.'): (34.6834, -82.8374),
    ('Knoxville', 'TN'): (35.9606, -83.9207),
    ('Knoxville', 'Tenn.'): (35.9606, -83.9207),
    ('Lexington', 'KY'): (38.0406, -84.5037),
    ('Lexington', 'Ky.'): (38.0406, -84.5037),
    ('Tuscaloosa', 'AL'): (33.2098, -87.5692),
    ('Tuscaloosa', 'Ala.'): (33.2098, -87.5692),
    ('Auburn', 'AL'): (32.6099, -85.4808),
    ('Auburn', 'Ala.'): (32.6099, -85.4808),
    ('Oxford', 'MS'): (34.3665, -89.5192),
    ('Oxford', 'Miss.'): (34.3665, -89.5192),
    ('Lubbock', 'TX'): (33.5779, -101.8552),
    ('Lubbock', 'Texas'): (33.5779, -101.8552),
    ('Lubbock', 'Tex.'): (33.5779, -101.8552),
    ('Austin', 'TX'): (30.2672, -97.7431),
    ('Austin', 'Texas'): (30.2672, -97.7431),
    ('Austin', 'Tex.'): (30.2672, -97.7431),
    ('Waco', 'TX'): (31.5493, -97.1467),
    ('Waco', 'Texas'): (31.5493, -97.1467),
    ('Waco', 'Tex.'): (31.5493, -97.1467),
    ('Fort Worth', 'TX'): (32.7555, -97.3308),
    ('Fort Worth', 'Texas'): (32.7555, -97.3308),
    ('Fort Worth', 'Tex.'): (32.7555, -97.3308),
    ('Raleigh', 'NC'): (35.7796, -78.6382),
    ('Raleigh', 'N.C.'): (35.7796, -78.6382),
    ('Durham', 'NC'): (35.9940, -78.8986),
    ('Durham', 'N.C.'): (35.9940, -78.8986),
    ('Columbia', 'SC'): (34.0007, -81.0348),
    ('Columbia', 'S.C.'): (34.0007, -81.0348),
    ('Gainesville', 'GA'): (34.2979, -83.8241),
    ('Gainesville', 'Ga.'): (34.2979, -83.8241),
    ('Athens', 'GA'): (33.9519, -83.3576),
    ('Athens', 'Ga.'): (33.9519, -83.3576),
    ('Hoover', 'AL'): (33.4054, -86.8114),
    ('Hoover', 'Ala.'): (33.4054, -86.8114),
    ('Birmingham', 'AL'): (33.5207, -86.8025),
    ('Birmingham', 'Ala.'): (33.5207, -86.8025),
}


def generate_nextjs_data(processed_data: Dict[str, Any], raw_games: List[Dict] = None, schedule_games: List[Dict] = None):
    """
    Generate JSON data file and copy logos for the Next.js website.

    Writes web/src/data/site-data.json and copies logo PNGs to web/public/logos/.
    """
    web_dir = Path(__file__).resolve().parent.parent.parent / 'web'
    data_dir = web_dir / 'src' / 'data'
    public_data_dir = web_dir / 'public' / 'data'
    logos_dest = web_dir / 'public' / 'logos'
    logos_src = Path(__file__).resolve().parent.parent.parent / 'logos'

    data_dir.mkdir(parents=True, exist_ok=True)
    public_data_dir.mkdir(parents=True, exist_ok=True)
    logos_dest.mkdir(parents=True, exist_ok=True)

    # Build the data dict (same as legacy HTML path)
    data = _serialize_data(processed_data, raw_games or [])

    # Write per-game detail JSON files (lazy-loaded by the game details modal)
    player_name_aliases = build_player_name_aliases(raw_games or [])
    game_index = _build_raw_game_index(raw_games or [])
    game_details = _build_per_game_details(game_index, player_name_aliases)
    games_written = _write_per_game_details(game_details, web_dir)
    data['gameDetails'] = game_details
    print(f"Per-game details written: {games_written} files to {web_dir / 'public' / 'games'}")

    # Add D1 schedule metadata. The full schedule is written as daily chunks so
    # the deployed app does not need to load the whole season on first paint.
    schedule_index = _write_schedule_chunks(schedule_games or [], web_dir)
    data['scheduleGames'] = []
    data['scheduleIndex'] = schedule_index
    print(f"Schedule chunks written: {len(schedule_index)} files to {web_dir / 'public' / 'data' / 'schedule'}")

    parity_issues = collect_website_data_parity_issues(processed_data, data)
    for issue in parity_issues[:10]:
        print(f"Website parity warning: {issue['message']}")
    if len(parity_issues) > 10:
        print(f"Website parity warning: {len(parity_issues) - 10} additional issue(s) suppressed")

    # Strip rawGames — too large and not needed by Next.js frontend
    data.pop('rawGames', None)

    # Replace base64 localLogos with file paths and copy PNGs
    file_logos: Dict[str, str] = {}
    for team_name, filename in LOCAL_LOGO_MAP.items():
        src_path = logos_src / filename
        if src_path.exists():
            import shutil
            shutil.copy2(src_path, logos_dest / filename)
            file_logos[team_name] = f'/logos/{filename}'
    data['localLogos'] = file_logos

    # Also copy any logos referenced in historicalTeamLogos that are local base64
    # (historicalTeamLogos may reference mlbstatic URLs — keep those as-is)
    cleaned_historical = {}
    for team, url in data.get('historicalTeamLogos', {}).items():
        if isinstance(url, str) and url.startswith('data:'):
            # This was a base64 logo from localLogos — replace with file path
            logo_file = LOCAL_LOGO_MAP.get(team)
            if logo_file:
                cleaned_historical[team] = f'/logos/{logo_file}'
            else:
                cleaned_historical[team] = url  # keep as-is if no mapping
        else:
            cleaned_historical[team] = url
    data['historicalTeamLogos'] = cleaned_historical

    cleaned_partner_logos = {}
    for team, url in data.get('partnerLogos', {}).items():
        if isinstance(url, str) and url.startswith('data:'):
            logo_file = LOCAL_LOGO_MAP.get(team)
            cleaned_partner_logos[team] = f'/logos/{logo_file}' if logo_file else url
        else:
            cleaned_partner_logos[team] = url
    data['partnerLogos'] = cleaned_partner_logos

    data = scrub_json_value(data)

    json_path = data_dir / 'site-data.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, default=str, separators=(',', ':'))
    public_json_path = public_data_dir / 'site-data.json'
    with open(public_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, default=str, separators=(',', ':'))

    print(f"Next.js data written: {json_path} ({json_path.stat().st_size / 1024:.0f} KB)")
    print(f"Public data written: {public_json_path} ({public_json_path.stat().st_size / 1024:.0f} KB)")
    print(f"Logos copied to: {logos_dest} ({len(file_logos)} files)")
    return json_path


def _write_schedule_chunks(schedule_games: List[Dict], web_dir: Path) -> List[Dict[str, Any]]:
    """Write D1 schedule games as lazy-loaded daily chunks."""
    import shutil

    src_schedule_dir = web_dir / 'src' / 'data' / 'schedule'
    public_schedule_dir = web_dir / 'public' / 'data' / 'schedule'
    for schedule_dir in (src_schedule_dir, public_schedule_dir):
        if schedule_dir.exists():
            shutil.rmtree(schedule_dir)
        schedule_dir.mkdir(parents=True, exist_ok=True)

    grouped: Dict[str, List[Dict]] = {}
    for game in schedule_games or []:
        date_key = str(game.get('date') or '')[:10]
        if not date_key:
            date_key = 'unknown'
        grouped.setdefault(date_key, []).append(game)

    schedule_index: List[Dict[str, Any]] = []
    for date_key in sorted(grouped):
        games = scrub_json_value(grouped[date_key])
        filename = f'{date_key}.json'
        for schedule_dir in (src_schedule_dir, public_schedule_dir):
            with open(schedule_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(games, f, default=str, separators=(',', ':'))
        schedule_index.append({
            'date': date_key,
            'path': f'/data/schedule/{filename}',
            'count': len(games),
        })

    return schedule_index


def _build_data_quality_report(raw_games: List[Dict]) -> Dict[str, Any]:
    """Summarize generated-data provenance and source disagreement signals."""
    source_merge_games: list[Dict[str, Any]] = []
    source_merge_issues: list[Dict[str, Any]] = []
    source_candidates: list[Dict[str, Any]] = []
    merged_source_games = 0
    source_merge_warnings = 0
    source_merge_infos = 0

    for raw_game in raw_games or []:
        normalized = normalize_game(raw_game)
        basic = normalized.get('basic_info', {}) or {}
        game_context = {
            'game_id': normalized.get('game_id'),
            'date': basic.get('date', ''),
            'date_yyyymmdd': basic.get('date_yyyymmdd', ''),
            'away_team': basic.get('away_team', ''),
            'home_team': basic.get('home_team', ''),
            'away_score': basic.get('away_score_value', 0),
            'home_score': basic.get('home_score_value', 0),
        }

        quality = raw_game.get('data_quality') or {}
        source_candidate = quality.get('source_candidate')
        if isinstance(source_candidate, dict):
            source_candidates.append({
                **game_context,
                'confidence': source_candidate.get('confidence'),
                'reason': source_candidate.get('reason'),
                'pdf_score': source_candidate.get('pdf_score'),
                'api_score': source_candidate.get('api_score'),
                'api_game_id': source_candidate.get('api_game_id'),
            })

        source_merge = quality.get('source_merge')
        if not isinstance(source_merge, dict):
            continue

        merged_source_games += 1
        game_context = {
            **game_context,
            'confidence': source_merge.get('confidence', 'high'),
            'warning_count': int(source_merge.get('warning_count') or 0),
            'info_count': int(source_merge.get('info_count') or 0),
            'issue_count': int(source_merge.get('issue_count') or 0),
        }

        source_merge_warnings += game_context['warning_count']
        source_merge_infos += game_context['info_count']

        game_issues = []
        for issue in source_merge.get('issues', []) or []:
            if not isinstance(issue, dict):
                continue
            issue_record = {**game_context, **issue}
            game_issues.append(issue_record)
            source_merge_issues.append(issue_record)

        source_merge_games.append({
            **game_context,
            'sources': source_merge.get('sources', []),
            'stats_source': source_merge.get('stats_source'),
            'identity_source': source_merge.get('identity_source'),
            'api_game_id': source_merge.get('api_game_id'),
            'sections': source_merge.get('sections', {}),
            'issues': game_issues[:25],
        })

    source_merge_issues.sort(
        key=lambda issue: (
            0 if issue.get('severity') == 'warning' else 1,
            str(issue.get('date_yyyymmdd') or ''),
            str(issue.get('game_id') or ''),
        )
    )
    source_merge_games.sort(
        key=lambda game: (
            0 if game.get('warning_count') else 1,
            str(game.get('date_yyyymmdd') or ''),
            str(game.get('game_id') or ''),
        )
    )

    return {
        'summary': {
            'mergedSourceGames': merged_source_games,
            'unmergedSourceCandidates': len(source_candidates),
            'sourceMergeWarnings': source_merge_warnings,
            'sourceMergeInfos': source_merge_infos,
            'sourceMergeIssues': source_merge_warnings + source_merge_infos,
            'sourceMergeReviewGames': sum(1 for game in source_merge_games if game.get('warning_count')),
        },
        'sourceMerge': {
            'games': source_merge_games[:100],
            'issues': source_merge_issues[:500],
            'unmergedCandidates': source_candidates[:100],
        },
    }


def _serialize_data(processed_data: Dict[str, Any], raw_games: List[Dict]) -> Dict[str, Any]:
    """Convert DataFrames to JSON-serializable format."""
    player_name_aliases = build_player_name_aliases(raw_games or [])

    # Calculate summary stats
    game_log = processed_data.get('game_log', pd.DataFrame())
    batters = processed_data.get('batters', pd.DataFrame())
    pitchers = processed_data.get('pitchers', pd.DataFrame())
    team_records = processed_data.get('team_records', pd.DataFrame())

    total_games = len(game_log) if isinstance(game_log, pd.DataFrame) else 0
    total_batters = len(batters) if isinstance(batters, pd.DataFrame) else 0
    total_pitchers = len(pitchers) if isinstance(pitchers, pd.DataFrame) else 0
    total_teams = len(team_records) if isinstance(team_records, pd.DataFrame) else 0

    # MiLB stats
    milb_game_log = processed_data.get('milb_game_log', pd.DataFrame())
    milb_batters = processed_data.get('milb_batters', pd.DataFrame())
    milb_pitchers = processed_data.get('milb_pitchers', pd.DataFrame())
    crossover_players = processed_data.get('crossover_players', pd.DataFrame())

    milb_games_count = len(milb_game_log) if isinstance(milb_game_log, pd.DataFrame) else 0
    milb_batters_count = len(milb_batters) if isinstance(milb_batters, pd.DataFrame) else 0
    milb_pitchers_count = len(milb_pitchers) if isinstance(milb_pitchers, pd.DataFrame) else 0
    crossover_count = len(crossover_players) if isinstance(crossover_players, pd.DataFrame) else 0

    milestones = processed_data.get('milestones', {})
    total_milestones = count_notable_milestones(milestones)

    # Build stadium locations for map
    stadium_locations = {}
    for team, info in STADIUM_DATA.items():
        lat, lng, stadium_name = info
        stadium_locations[team] = {'lat': lat, 'lng': lng, 'stadium': stadium_name, 'type': 'ncaa'}

    # Build MiLB stadium locations (includes defunct teams for historical visits)
    milb_stadium_locations = {}
    for venue_name, info in MILB_STADIUM_DATA.items():
        lat, lng, team_name, level_code, team_id, league_name = info
        resolved_level = SPORT_LEVEL_MAP.get(level_code, level_code)
        # Check for logo override, otherwise use mlbstatic
        logo_url = LOGO_OVERRIDES.get(team_id, f'https://www.mlbstatic.com/team-logos/{team_id}.svg')
        milb_stadium_locations[venue_name] = {
            'lat': lat, 'lng': lng, 'stadium': venue_name,
            'team': team_name, 'level': resolved_level, 'league': league_name, 'type': 'milb',
            'teamId': team_id, 'logo': logo_url
        }

    # Build Partner (independent league) stadium locations
    partner_stadium_locations = get_partner_stadium_locations()

    # Build partner logos mapping (team name -> logo URL)
    partner_logos = {team_name: data.get('logo') for team_name, data in PARTNER_TEAM_DATA.items() if data.get('logo')}

    # Load local logos (base64 data URIs) and override partner/historical logos
    local_logos = _load_local_logos()
    partner_logos.update({k: v for k, v in local_logos.items() if k in partner_logos or k in PARTNER_TEAM_DATA})

    # MiLB venue name mappings (old names -> current names)
    milb_venue_aliases = {
        'Calvin Falwell Field': 'Bank of the James Stadium',  # Lynchburg Hillcats
        'Perfect Game Field': 'Veterans Memorial Stadium',  # Cedar Rapids Kernels
    }

    # Track MiLB and Partner venues visited
    milb_venues_visited = set()
    partner_venues_visited = set()
    for game in raw_games:
        if game.get('format') == 'milb_api':
            venue = game.get('metadata', {}).get('venue', '')
            if venue:
                # Map old venue names to current names
                mapped_venue = milb_venue_aliases.get(venue, venue)
                milb_venues_visited.add(mapped_venue)
        elif game.get('metadata', {}).get('source') == 'partner':
            # Partner league games - track both teams' stadiums as "visited"
            metadata = game.get('metadata', {})
            home_team = metadata.get('home_team', '')
            if home_team and home_team in PARTNER_TEAM_DATA:
                stadium = PARTNER_TEAM_DATA[home_team].get('stadium')
                if stadium:
                    partner_venues_visited.add(stadium)

    # Build checklist data - track which teams/venues have been seen
    teams_seen_home = set()  # Teams seen at their actual home stadium
    teams_seen_away = set()  # Teams seen but not at their home stadium
    venues_visited = set()    # Venues we've been to

    def normalize_venue(name):
        """Normalize venue name for matching."""
        name = name.lower()
        # Common abbreviations
        name = name.replace('muni ', 'municipal ')
        name = name.replace(' at ', ' ')
        # Remove parenthetical city/state info
        if '(' in name:
            name = name.split('(')[0].strip()
        return name

    def venues_match(stadium_name, venue_name):
        """Check if a venue matches a stadium name."""
        stadium = normalize_venue(stadium_name)
        venue = normalize_venue(venue_name)

        # Direct containment check
        if stadium in venue or venue in stadium:
            return True

        # Check if key words match (for partial names like "Benedetti Diamond")
        stadium_words = set(stadium.split())
        venue_words = set(venue.split())
        # Remove common words
        common = {'field', 'stadium', 'park', 'ballpark', 'diamond', 'at', 'the'}
        stadium_key = stadium_words - common
        venue_key = venue_words - common

        # If 2+ key words match, consider it a match
        if len(stadium_key & venue_key) >= 2:
            return True

        # Check if the main distinctive word matches
        for word in stadium_key:
            if len(word) > 4 and word in venue:  # Significant word
                return True

        return False

    # Build a mapping of team -> home stadium name for matching
    team_stadiums = {}
    for team, info in STADIUM_DATA.items():
        stadium_name = info[2] if len(info) > 2 else ''
        team_stadiums[team] = stadium_name

    for game in raw_games:
        meta = game.get('metadata', {})
        home_team = normalize_team_name(meta.get('home_team', ''))
        away_team = normalize_team_name(meta.get('away_team', ''))
        venue = meta.get('venue', '')

        if venue:
            venues_visited.add(venue)

        # Check if venue matches the team's actual stadium
        home_stadium = team_stadiums.get(home_team, '')
        away_stadium = team_stadiums.get(away_team, '')

        # A team is "visited" only if we were at their actual home stadium
        if home_team:
            if home_stadium and venues_match(home_stadium, venue):
                teams_seen_home.add(home_team)
            else:
                # Neutral site - just mark as seen (away)
                teams_seen_away.add(home_team)

        if away_team:
            if away_stadium and venues_match(away_stadium, venue):
                teams_seen_home.add(away_team)
            else:
                teams_seen_away.add(away_team)

    # Build conference checklist
    checklist = {}
    for conf, teams in CONFERENCES.items():
        seen = len([t for t in teams if t in teams_seen_home or t in teams_seen_away])
        visited = len([t for t in teams if t in teams_seen_home])
        checklist[conf] = {
            'teams': teams,
            'total': len(teams),
            'seen': seen,
            'visited': visited,
            'teamStatus': {t: 'home' if t in teams_seen_home else ('away' if t in teams_seen_away else 'none') for t in teams}
        }

    road_only_partner_teams = {
        team_name
        for team_name, data in PARTNER_TEAM_DATA.items()
        if data.get('road_only')
    }

    # Build MiLB/Partner checklist organized by level/league
    milb_teams_seen_home = set()  # Teams at venues we visited
    milb_teams_seen_away = set()  # Teams we saw play (as away team at a venue we visited)

    for game in raw_games:
        if game.get('format') == 'milb_api':
            metadata = game.get('metadata', {})
            home_team = metadata.get('home_team', '')
            away_team = metadata.get('away_team', '')
            if home_team:
                milb_teams_seen_home.add(home_team)
            if away_team:
                milb_teams_seen_away.add(away_team)
        elif game.get('metadata', {}).get('source') == 'partner':
            metadata = game.get('metadata', {})
            home_team = metadata.get('home_team', '')
            away_team = metadata.get('away_team', '')
            if home_team:
                milb_teams_seen_home.add(home_team)
            if away_team:
                if away_team in road_only_partner_teams:
                    milb_teams_seen_home.add(away_team)
                else:
                    milb_teams_seen_away.add(away_team)

    # Organize MiLB teams by level → league
    milb_by_level = {}
    for level in LEVEL_ORDER[1:]:  # Skip 'NCAA'
        milb_by_level[level] = {}
        for league in PRO_LEVELS.get(level, []):
            milb_by_level[level][league] = []

    # Add active MiLB teams (skip defunct/historic teams)
    for venue_name, info in MILB_STADIUM_DATA.items():
        lat, lng, team_name, level_code, team_id, league_name = info
        if team_name in HISTORIC_MILB_TEAMS:
            continue
        mapped_level = SPORT_LEVEL_MAP.get(level_code, level_code)
        logo_url = LOGO_OVERRIDES.get(team_id, f'https://www.mlbstatic.com/team-logos/{team_id}.svg')
        team_entry = {
            'team': team_name,
            'venue': venue_name,
            'teamId': team_id,
            'logo': logo_url,
            'league': league_name,
            'historic': False,
        }
        if mapped_level in milb_by_level:
            if league_name in milb_by_level[mapped_level]:
                milb_by_level[mapped_level][league_name].append(team_entry)
            else:
                milb_by_level[mapped_level][league_name] = [team_entry]

    # Track team names already added from MILB_STADIUM_DATA to avoid duplicates
    # Only include non-historic teams; historic teams may also appear in PARTNER_TEAM_DATA
    seen_milb_team_names = set()
    for venue_info in MILB_STADIUM_DATA.values():
        team_name = venue_info[2]
        if team_name not in HISTORIC_MILB_TEAMS:
            seen_milb_team_names.add(team_name)

    # Add Partner (independent league) teams
    seen_partner_ids = set()
    for team_name, data in PARTNER_TEAM_DATA.items():
        team_id = data.get('id')
        if team_id in seen_partner_ids or team_name in seen_milb_team_names:
            continue
        seen_partner_ids.add(team_id)
        league_name = data.get('league', '')
        team_entry = {
            'team': team_name,
            'venue': 'Road-only team' if data.get('road_only') else data.get('stadium', ''),
            'teamId': team_id,
            'logo': data.get('logo', ''),
            'league': league_name,
            'historic': False,
            'roadOnly': bool(data.get('road_only')),
        }
        if 'Independent' in milb_by_level:
            if league_name in milb_by_level['Independent']:
                milb_by_level['Independent'][league_name].append(team_entry)
            else:
                milb_by_level['Independent'][league_name] = [team_entry]

    # Build flat milb_checklist per level (with league breakdown)
    milb_checklist = {}
    for level, leagues in milb_by_level.items():
        all_teams = []
        league_data = {}
        for league_name, teams in leagues.items():
            all_teams.extend(teams)
            team_names = [t['team'] for t in teams]
            seen = len([t for t in team_names if t in milb_teams_seen_home or t in milb_teams_seen_away])
            visited = len([t for t in team_names if t in milb_teams_seen_home])
            league_data[league_name] = {
                'teams': sorted(teams, key=lambda x: x['team']),
                'total': len(teams),
                'seen': seen,
                'visited': visited,
                'teamStatus': {t['team']: 'home' if t['team'] in milb_teams_seen_home else ('away' if t['team'] in milb_teams_seen_away else 'none') for t in teams}
            }
        all_team_names = [t['team'] for t in all_teams]
        total_seen = len([t for t in all_team_names if t in milb_teams_seen_home or t in milb_teams_seen_away])
        total_visited = len([t for t in all_team_names if t in milb_teams_seen_home])
        if len(all_teams) > 0:
            milb_checklist[level] = {
                'teams': sorted(all_teams, key=lambda x: x['team']),
                'total': len(all_teams),
                'seen': total_seen,
                'visited': total_visited,
                'teamStatus': {t['team']: 'home' if t['team'] in milb_teams_seen_home else ('away' if t['team'] in milb_teams_seen_away else 'none') for t in all_teams},
                'leagues': league_data,
            }

    # Initialize player ID mapper for bref_id lookups on MiLB players (needed for game enrichment too)
    try:
        id_mapper = PlayerIDMapper(auto_download=True)
    except Exception:
        id_mapper = None

    # Get game-by-game data for players and enrich with level + bref_id
    batter_games_df = processed_data.get('batter_games', pd.DataFrame())
    pitcher_games_df = processed_data.get('pitcher_games', pd.DataFrame())

    # Build bref_id lookup from NCAA batters/pitchers DataFrames
    ncaa_batter_bref = {}
    if isinstance(batters, pd.DataFrame) and not batters.empty:
        for _, row in batters.iterrows():
            name = row.get('Name', '')
            team = row.get('Team', '')
            bid = row.get('bref_id', '')
            if name and bid:
                ncaa_batter_bref[f"{name}|{team}"] = bid
                ncaa_batter_bref[name] = bid

    ncaa_pitcher_bref = {}
    if isinstance(pitchers, pd.DataFrame) and not pitchers.empty:
        for _, row in pitchers.iterrows():
            name = row.get('Name', '')
            team = row.get('Team', '')
            bid = row.get('bref_id', '')
            if name and bid:
                ncaa_pitcher_bref[f"{name}|{team}"] = bid
                ncaa_pitcher_bref[name] = bid

    # Convert NCAA batter_games to enriched list
    enriched_batter_games = []
    for bg in df_to_list(batter_games_df):
        name = bg.get('Name', '')
        team = bg.get('team', '')
        bref_id = ncaa_batter_bref.get(f"{name}|{team}", ncaa_batter_bref.get(name, ''))
        enriched_batter_games.append({**bg, 'level': 'NCAA', 'bref_id': bref_id})

    # Convert NCAA pitcher_games to enriched list
    enriched_pitcher_games = []
    for pg in df_to_list(pitcher_games_df):
        name = pg.get('Name', '')
        team = pg.get('team', '')
        bref_id = ncaa_pitcher_bref.get(f"{name}|{team}", ncaa_pitcher_bref.get(name, ''))
        enriched_pitcher_games.append({**pg, 'level': 'NCAA', 'bref_id': bref_id})

    # Extract MiLB/Partner per-player game records from raw_games
    for game in raw_games:
        if game.get('format') != 'milb_api' and game.get('metadata', {}).get('source') != 'partner':
            continue
        meta = game.get('metadata', {})
        box_score = game.get('box_score', {})
        date = meta.get('date', '')
        home_team = meta.get('home_team', '')
        game_level, game_league = resolve_level_and_league(meta, home_team)

        for side in ['away', 'home']:
            team = meta.get(f'{side}_team', '')
            opponent = meta.get('home_team' if side == 'away' else 'away_team', '')

            # Batting records
            for player in box_score.get(f'{side}_batting', []):
                pname = player.get('full_name') or player.get('name', '')
                if not pname or 'total' in pname.lower():
                    continue
                pid = player.get('player_id', '')
                bref_id = player.get('bref_id') or player.get('register_id') or ''
                if pid and id_mapper and str(pid).isdigit():
                    bref_id = id_mapper.get_register_from_mlbam(int(pid)) or bref_id
                elif pid and not bref_id:
                    bref_id = str(pid)
                pname = resolve_player_display_name(pname, bref_id)
                alias = resolve_player_name_alias(pname, team, player_name_aliases)
                if alias:
                    pname = alias.get('display_name') or pname
                    bref_id = bref_id or alias.get('bref_id', '')
                enriched_batter_games.append({
                    'Name': pname, 'name': pname,
                    'date': date, 'team': team, 'opponent': opponent,
                    'level': game_level, 'league': game_league,
                    'bref_id': bref_id, 'player_id': str(pid) if pid else '',
                    'ab': player.get('ab', 0), 'r': player.get('r', 0),
                    'h': player.get('h', 0), 'doubles': player.get('doubles', 0),
                    'triples': player.get('triples', 0), 'hr': player.get('hr', 0),
                    'rbi': player.get('rbi', 0), 'bb': player.get('bb', 0),
                    'k': player.get('k', 0), 'sb': player.get('sb', 0),
                })

            # Pitching records
            for player in box_score.get(f'{side}_pitching', []):
                pname = player.get('full_name') or player.get('name', '')
                if not pname or 'total' in pname.lower():
                    continue
                pid = player.get('player_id', '')
                bref_id = player.get('bref_id') or player.get('register_id') or ''
                if pid and id_mapper and str(pid).isdigit():
                    bref_id = id_mapper.get_register_from_mlbam(int(pid)) or bref_id
                elif pid and not bref_id:
                    bref_id = str(pid)
                pname = resolve_player_display_name(pname, bref_id)
                alias = resolve_player_name_alias(pname, team, player_name_aliases)
                if alias:
                    pname = alias.get('display_name') or pname
                    bref_id = bref_id or alias.get('bref_id', '')
                enriched_pitcher_games.append({
                    'Name': pname, 'name': pname,
                    'date': date, 'team': team, 'opponent': opponent,
                    'level': game_level, 'league': game_league,
                    'bref_id': bref_id, 'player_id': str(pid) if pid else '',
                    'ip': player.get('ip', 0), 'h': player.get('h', 0),
                    'r': player.get('r', 0), 'er': player.get('er', 0),
                    'bb': player.get('bb', 0), 'k': player.get('k', 0),
                    'hr': player.get('hr', 0),
                })

    # Build lookup from raw_games so we can attach stable game_id + source to each entry
    raw_game_index = _build_raw_game_index(raw_games)

    lookup_offsets = {}

    def _lookup_game(date_sort, away, home, away_score=None, home_score=None):
        key = (
            date_sort or '',
            (away or '').lower().strip(),
            (home or '').lower().strip(),
            str(away_score if away_score is not None else '').strip(),
            str(home_score if home_score is not None else '').strip(),
        )
        bucket = raw_game_index.get(key) or []
        if bucket:
            index = lookup_offsets.get(key, 0)
            hit = bucket[index] if index < len(bucket) else bucket[-1]
            lookup_offsets[key] = index + 1
            return hit[0], hit[1]
        return None, None

    # Build unified game log (all levels)
    unified_game_log = []

    # Add NCAA games
    ncaa_log = df_to_list(game_log)
    for game in ncaa_log:
        # Convert DateSort from "2025-06-16" to "20250616" for consistent sorting
        date_sort = game.get('DateSort', game.get('Date', ''))
        if date_sort and '-' in date_sort:
            date_sort = date_sort.replace('-', '')
        gid, src = _lookup_game(
            date_sort,
            game.get('Away', ''),
            game.get('Home', ''),
            game.get('Away Score', 0),
            game.get('Home Score', 0),
        )
        unified_game_log.append({
            'date': game.get('Date', ''),
            'date_sort': date_sort,
            'away_team': game.get('Away', ''),
            'home_team': game.get('Home', ''),
            'away_score': game.get('Away Score', 0),
            'home_score': game.get('Home Score', 0),
            'venue': game.get('Venue', ''),
            'level': 'NCAA',
            'conference': game.get('Conference', ''),
            'game_id': gid,
            'source': src,
        })

    # Add MiLB games
    milb_log = df_to_list(milb_game_log)
    for game in milb_log:
        # Find team IDs for logos - use capitalized column names from DataFrame
        home_team = game.get('Home Team', '')
        away_team = game.get('Away Team', '')
        home_team_id = _team_id_for_name(home_team)
        away_team_id = _team_id_for_name(away_team)

        # Parse score from combined "X-Y" format
        score_str = game.get('Score', '0-0')
        try:
            away_score, home_score = score_str.split('-')
            away_score = int(away_score)
            home_score = int(home_score)
        except:
            away_score, home_score = 0, 0

        # Use resolved level from pipeline
        resolved_level = game.get('Level', '')
        league = game.get('League', '')

        milb_date_sort = game.get('date_yyyymmdd', game.get('Date', ''))
        gid, src = _lookup_game(milb_date_sort, away_team, home_team, away_score, home_score)
        unified_game_log.append({
            'date': game.get('Date', ''),
            'date_sort': milb_date_sort,
            'away_team': away_team,
            'home_team': home_team,
            'away_score': away_score,
            'home_score': home_score,
            'venue': game.get('Venue', ''),
            'level': resolved_level,
            'league': league,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'parent_orgs': {'away': game.get('Away Parent', ''), 'home': game.get('Home Parent', '')},
            'game_id': gid,
            'source': src,
        })

    # Sort by date (most recent first)
    unified_game_log.sort(key=lambda x: x.get('date_sort', ''), reverse=True)

    # Build scorigami data
    scorigami = {}
    for game in unified_game_log:
        a = game.get('away_score', 0) or 0
        h = game.get('home_score', 0) or 0
        try:
            a, h = int(a), int(h)
        except (ValueError, TypeError):
            continue
        if a == 0 and h == 0:
            continue
        lo, hi = min(a, h), max(a, h)
        key = f"{lo}-{hi}"
        if key not in scorigami:
            scorigami[key] = {'count': 0, 'games': []}
        scorigami[key]['count'] += 1
        scorigami[key]['games'].append({
            'date': game.get('date', ''),
            'away': game.get('away_team', ''),
            'home': game.get('home_team', ''),
            'away_score': a,
            'home_score': h,
            'level': game.get('level', ''),
        })

    # Build unified batters list (all levels)
    unified_batters = []

    # Add NCAA batters
    ncaa_batters = df_to_list(batters)
    for b in ncaa_batters:
        unified_batters.append({
            'name': b.get('Name', ''),
            'team': b.get('Team', ''),
            'level': 'NCAA',
            'league': b.get('Conference', ''),
            'conference': b.get('Conference', ''),
            'g': b.get('G', 0),
            'ab': b.get('AB', 0),
            'r': b.get('R', 0),
            'h': b.get('H', 0),
            'doubles': b.get('2B', 0),
            'triples': b.get('3B', 0),
            'hr': b.get('HR', 0),
            'rbi': b.get('RBI', 0),
            'bb': b.get('BB', 0),
            'k': b.get('K', 0),
            'sb': b.get('SB', 0),
            'avg': b.get('AVG', '.000'),
            'obp': b.get('OBP', '.000'),
            'slg': b.get('SLG', '.000'),
            'bref_id': b.get('bref_id', ''),
        })

    # id_mapper already initialized above (before game enrichment)

    # Add MiLB batters
    milb_batters_list = df_to_list(milb_batters)
    for b in milb_batters_list:
        team_name = b.get('Team', '')
        team_id = _team_id_for_name(team_name)
        # Look up bref_id from MLBAM player_id via Chadwick register
        bref_id = ''
        pid = b.get('Player ID', '') or b.get('player_id', '')
        if pid and id_mapper and str(pid).isdigit():
            bref_id = id_mapper.get_register_from_mlbam(int(pid)) or ''
        elif pid and isinstance(pid, str) and not str(pid).isdigit():
            bref_id = pid
        resolved_level = b.get('Level', '')
        league = b.get('League', '')
        unified_batters.append({
            'name': b.get('Name', ''),
            'team': team_name,
            'level': resolved_level,
            'league': league,
            'team_id': team_id,
            'g': b.get('G', 0),
            'ab': b.get('AB', 0),
            'r': b.get('R', 0),
            'h': b.get('H', 0),
            'doubles': b.get('2B', 0),
            'triples': b.get('3B', 0),
            'hr': b.get('HR', 0),
            'rbi': b.get('RBI', 0),
            'bb': b.get('BB', 0),
            'k': b.get('K', 0),
            'sb': b.get('SB', 0),
            'avg': b.get('AVG', '.000'),
            'obp': b.get('OBP', '.000'),
            'slg': b.get('SLG', '.000'),
            'player_id': pid,
            'bref_id': bref_id,
        })

    # Build unified pitchers list (all levels)
    unified_pitchers = []

    # Add NCAA pitchers
    ncaa_pitchers = df_to_list(pitchers)
    for p in ncaa_pitchers:
        unified_pitchers.append({
            'name': p.get('Name', ''),
            'team': p.get('Team', ''),
            'level': 'NCAA',
            'league': p.get('Conference', ''),
            'conference': p.get('Conference', ''),
            'g': p.get('G', 0),
            'ip': p.get('IP', 0),
            'h': p.get('H', 0),
            'r': p.get('R', 0),
            'er': p.get('ER', 0),
            'bb': p.get('BB', 0),
            'k': p.get('K', 0),
            'hr': p.get('HR', 0),
            'era': p.get('ERA', '0.00'),
            'bref_id': p.get('bref_id', ''),
        })

    # Add MiLB pitchers
    milb_pitchers_list = df_to_list(milb_pitchers)
    for p in milb_pitchers_list:
        team_name = p.get('Team', '')
        team_id = _team_id_for_name(team_name)
        # Look up bref_id from MLBAM player_id via Chadwick register
        bref_id = ''
        pid = p.get('Player ID', '') or p.get('player_id', '')
        if pid and id_mapper and str(pid).isdigit():
            bref_id = id_mapper.get_register_from_mlbam(int(pid)) or ''
        elif pid and isinstance(pid, str) and not str(pid).isdigit():
            bref_id = pid
        resolved_level = p.get('Level', '')
        league = p.get('League', '')
        unified_pitchers.append({
            'name': p.get('Name', ''),
            'team': team_name,
            'level': resolved_level,
            'league': league,
            'team_id': team_id,
            'g': p.get('G', 0),
            'ip': p.get('IP', 0),
            'h': p.get('H', 0),
            'r': p.get('R', 0),
            'er': p.get('ER', 0),
            'bb': p.get('BB', 0),
            'k': p.get('K', 0),
            'hr': p.get('HR', 0),
            'era': p.get('ERA', '0.00'),
            'player_id': pid,
            'bref_id': bref_id,
        })

    return {
        'summary': {
            'totalGames': total_games,
            'totalBatters': total_batters,
            'totalPitchers': total_pitchers,
            'totalTeams': total_teams,
            'totalMilestones': total_milestones,
            'milbGames': milb_games_count,
            'milbBatters': milb_batters_count,
            'milbPitchers': milb_pitchers_count,
            'crossoverPlayers': crossover_count,
            'allGames': len(unified_game_log),
            'unifiedBatters': len(unified_batters),
            'unifiedPitchers': len(unified_pitchers),
        },
        'levelColors': LEVEL_COLORS,
        'levelOrder': LEVEL_ORDER,
        'batterGames': enriched_batter_games,
        'pitcherGames': enriched_pitcher_games,
        'teamRecords': df_to_list(team_records),
        'milestones': serialize_milestones(milestones),
        'unifiedGameLog': unified_game_log,
        'scorigami': scorigami,
        'crossoverPlayers': df_to_list(crossover_players),
        'rawGames': raw_games,
        'stadiumLocations': stadium_locations,
        'milbStadiumLocations': milb_stadium_locations,
        'partnerStadiumLocations': partner_stadium_locations,
        'milbVenuesVisited': list(milb_venues_visited),
        'partnerVenuesVisited': list(partner_venues_visited),
        'checklist': checklist,
        'milbChecklist': milb_checklist,
        'teamsSeenHome': list(teams_seen_home),
        'teamsSeenAway': list(teams_seen_away),
        'unifiedBatters': unified_batters,
        'unifiedPitchers': unified_pitchers,
        'historicalTeamLogos': {**HISTORICAL_TEAM_LOGOS, **{k: v for k, v in local_logos.items() if k in HISTORICAL_TEAM_LOGOS}},
        'ncaaTeamLogos': NCAA_TEAM_LOGOS,
        'ncaaTeamNicknames': NCAA_TEAM_NICKNAMES,
        'venueCityCoords': {f"{city},{state}": {'lat': lat, 'lng': lng} for (city, state), (lat, lng) in VENUE_CITY_COORDS.items()},
        'partnerLogos': partner_logos,
        'localLogos': local_logos,
        'dataQuality': _build_data_quality_report(raw_games),
    }
