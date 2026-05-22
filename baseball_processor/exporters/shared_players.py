"""
Cross-project player export/import for linking NCAA and MLB processor websites.

Generates a shared_players.json with player IDs, summary stats, and website URLs
that the other processor can read to build cross-reference tabs.

Export format:
{
    "processor": "ncaa",
    "generated_at": "2024-01-15T10:30:00",
    "website_url": "https://ncaa-baseball.surge.sh",
    "players": [
        {
            "name": "John Smith",
            "bref_id": "smithj001",
            "mlb_api_id": 123456,
            "levels": ["NCAA", "Double-A"],
            "ncaa_teams": ["Oregon State"],
            "pro_teams": ["Hartford Yard Goats"],
            "ncaa_stats": {"G": 50, "AB": 180, "H": 55, "HR": 8, "AVG": ".306"},
            "pro_stats": {"G": 30, "AB": 110, "H": 30, "HR": 5, "AVG": ".273"},
            "draft_info": {"year": 2023, "round": 3, "pick": 85, "team": "Colorado Rockies"}
        }
    ]
}
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


def generate_shared_export(
    crossover_data,
    draft_matches: Optional[Dict] = None,
    website_url: str = "https://ncaa-baseball.surge.sh",
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Generate shared_players.json for cross-project linking.

    Args:
        crossover_data: PlayerCrossover instance with loaded data
        draft_matches: Optional dict mapping player keys to draft info
        website_url: URL of the generated website
        output_dir: Output directory (default: project data/ dir)

    Returns:
        Path to generated JSON file
    """
    if output_dir is None:
        from ..utils.constants import DATA_DIR
        output_dir = DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    players = []

    # Load MLB processor export to detect NCAA->MLB players (even without MiLB)
    mlb_export = load_mlb_processor_export()
    mlb_bref_ids = set()
    if mlb_export:
        for p in mlb_export.get('players', []):
            if p.get('bref_id'):
                mlb_bref_ids.add(p['bref_id'])

    # Load Chadwick Register for minors->MLB bref ID mapping
    _register_map = {}
    try:
        from ..utils.player_ids import PlayerIDMapper
        mapper = PlayerIDMapper(auto_download=False)
        mapper.ensure_data()
        _register_map = mapper.register_to_mlb
    except Exception:
        pass

    for key, player in crossover_data.players.items():
        # Check if this NCAA player also appeared in MLB games or reached MLB
        has_mlb = False  # Seen at user's MLB games
        reached_mlb = False  # Has an MLB bref_id in Chadwick Register
        mlb_bref_id = None
        if player.ncaa_appearances and player.bref_id:
            # Check via Chadwick Register mapping (minors bref_id -> MLB bref_id)
            mlb_bref_id = _register_map.get(player.bref_id)
            if mlb_bref_id:
                reached_mlb = True
                if mlb_bref_id in mlb_bref_ids:
                    has_mlb = True
            # Check direct bref_id match
            elif player.bref_id in mlb_bref_ids:
                has_mlb = True
                reached_mlb = True
                mlb_bref_id = player.bref_id

        # Export ALL players so the MLB processor can check any
        # college/minor league player against MLB appearances

        # Aggregate NCAA batting stats
        ncaa_stats = _aggregate_stats(player.ncaa_appearances)
        # Aggregate pro batting stats
        pro_stats = _aggregate_stats(player.milb_appearances)

        # Get draft info if available
        draft_info = None
        if draft_matches:
            draft_key = player.bref_id or player.name
            match = draft_matches.get(draft_key)
            if match:
                draft_info = {
                    'year': match.get('year'),
                    'round': match.get('round'),
                    'pick': match.get('pick_number'),
                    'team': match.get('team', ''),
                    'position': match.get('position', ''),
                }

        ncaa_teams = set()
        pro_teams = set()
        for a in player.ncaa_appearances:
            if a.get('team'):
                ncaa_teams.add(a['team'])
        for a in player.milb_appearances:
            if a.get('team'):
                pro_teams.add(a['team'])

        levels = player.levels_seen()
        if reached_mlb and 'MLB' not in levels:
            levels.append('MLB')

        player_data = {
            'name': player.name,
            'bref_id': player.bref_id or '',
            'mlb_bref_id': mlb_bref_id or '',
            'mlb_api_id': player.mlb_api_id,
            'levels': levels,
            'ncaa_teams': sorted(ncaa_teams),
            'pro_teams': sorted(pro_teams),
            'ncaa_stats': ncaa_stats,
            'pro_stats': pro_stats,
            'seen_in_mlb': has_mlb,
        }

        if draft_info:
            player_data['draft_info'] = draft_info

        players.append(player_data)

    # Sort by total appearances
    players.sort(key=lambda p: (
        p['ncaa_stats'].get('G', 0) + p['pro_stats'].get('G', 0)
    ), reverse=True)

    export = {
        'processor': 'ncaa',
        'generated_at': datetime.now().isoformat(),
        'website_url': website_url,
        'player_count': len(players),
        'players': players,
    }

    output_path = output_dir / 'shared_players.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export, f, indent=2)

    print(f"Shared player export: {len(players)} crossover players -> {output_path}")
    return output_path


def load_mlb_processor_export(mlb_data_dir: Optional[Path] = None) -> Optional[Dict]:
    """
    Load the MLB processor's shared_players.json.

    Args:
        mlb_data_dir: Path to MLB processor's data directory
                      Default: ~/mlb_processor/data/

    Returns:
        Parsed export dict, or None if not found
    """
    if mlb_data_dir is None:
        mlb_data_dir = Path.home() / 'mlb_processor' / 'data'

    export_path = mlb_data_dir / 'shared_players.json'

    if not export_path.exists():
        # Also try the project root
        alt_path = Path.home() / 'mlb_processor' / 'shared_players.json'
        if alt_path.exists():
            export_path = alt_path
        else:
            return None

    try:
        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data.get('processor') != 'mlb':
            # It's not from the MLB processor, skip
            return None

        print(f"MLB processor export loaded: {data.get('player_count', 0)} players")
        return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading MLB processor export: {e}")
        return None


def build_cross_reference(
    ncaa_crossover_data,
    mlb_export: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Build cross-reference data combining NCAA crossover players with MLB processor data.

    Args:
        ncaa_crossover_data: PlayerCrossover instance
        mlb_export: Optional MLB processor shared export

    Returns:
        List of cross-reference player dicts for website display
    """
    cross_ref = []

    # Build MLB lookup by bref_id and mlb_api_id
    mlb_by_bref = {}
    mlb_by_mlb_id = {}
    if mlb_export:
        for player in mlb_export.get('players', []):
            if player.get('bref_id'):
                mlb_by_bref[player['bref_id']] = player
            if player.get('mlb_api_id'):
                mlb_by_mlb_id[player['mlb_api_id']] = player

    for key, player in ncaa_crossover_data.players.items():
        if not player.is_crossover():
            continue

        # Try to find in MLB export
        mlb_data = None
        if player.bref_id and player.bref_id in mlb_by_bref:
            mlb_data = mlb_by_bref[player.bref_id]
        elif player.mlb_api_id and player.mlb_api_id in mlb_by_mlb_id:
            mlb_data = mlb_by_mlb_id[player.mlb_api_id]

        entry = {
            'name': player.name,
            'bref_id': player.bref_id or '',
            'mlb_api_id': player.mlb_api_id,
            'levels': player.levels_seen(),
            'ncaa_games': len(player.ncaa_appearances),
            'pro_games': len(player.milb_appearances),
        }

        if mlb_data:
            entry['mlb_processor'] = {
                'website_url': mlb_export.get('website_url', ''),
                'mlb_stats': mlb_data.get('mlb_stats', {}),
                'mlb_teams': mlb_data.get('mlb_teams', []),
            }

        cross_ref.append(entry)

    return cross_ref


def _aggregate_stats(appearances: list) -> Dict[str, Any]:
    """Aggregate batting/pitching stats from a list of appearances."""
    batting = {'G': 0, 'AB': 0, 'H': 0, 'R': 0, 'RBI': 0, 'HR': 0, 'BB': 0, 'K': 0}
    pitching = {'G': 0, 'IP': 0, 'H': 0, 'R': 0, 'ER': 0, 'BB': 0, 'K': 0}

    seen_games = set()
    has_batting = False
    has_pitching = False
    for a in appearances:
        game_key = f"{a.get('date_yyyymmdd', '')}_{a.get('team', '')}"
        s = a.get('stats', {})

        if a.get('type') == 'batting':
            has_batting = True
            if game_key not in seen_games:
                batting['G'] += 1
                seen_games.add(game_key)
            for key in ['AB', 'H', 'R', 'RBI', 'HR', 'BB', 'K']:
                try:
                    batting[key] += int(s.get(key, 0))
                except (ValueError, TypeError):
                    pass
        elif a.get('type') == 'pitching':
            has_pitching = True
            if game_key not in seen_games:
                pitching['G'] += 1
                seen_games.add(game_key)
            for key in ['H', 'R', 'ER', 'BB', 'K']:
                try:
                    pitching[key] += int(s.get(key, 0))
                except (ValueError, TypeError):
                    pass
            try:
                pitching['IP'] += float(s.get('IP', 0))
            except (ValueError, TypeError):
                pass

    # Return batting stats if available, otherwise pitching
    if has_batting and batting['AB'] > 0:
        if batting['AB'] > 0:
            batting['AVG'] = f".{int((batting['H'] / batting['AB']) * 1000):03d}"
        else:
            batting['AVG'] = '.000'
        batting['is_pitcher'] = False
        return batting
    elif has_pitching:
        # Format IP in baseball notation
        whole = int(pitching['IP'])
        frac = pitching['IP'] - whole
        thirds = round(frac * 3)
        pitching['IP_display'] = f"{whole}.{thirds}"
        pitching['AVG'] = '.000'
        pitching['AB'] = 0
        pitching['is_pitcher'] = True
        # Use pitching games count
        pitching['G'] = pitching['G'] or len(seen_games)
        return pitching
    else:
        batting['AVG'] = '.000'
        batting['is_pitcher'] = False
        return batting
