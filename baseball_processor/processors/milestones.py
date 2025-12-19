"""
Milestones processor for baseball.
"""

import re
from typing import Dict, List, Any
import pandas as pd

from ..utils.helpers import safe_int, safe_float, parse_innings_pitched, normalize_team_name


def is_valid_player_name(name: str) -> bool:
    """Check if a name is a valid player name (not a game note or totals row)."""
    if not name:
        return False

    name_lower = name.lower()

    # Skip totals
    if 'totals' in name_lower:
        return False

    # Skip game notes (SB:, 2B:, HR:, E:, etc.)
    note_prefixes = ['sb:', '2b:', '3b:', 'hr:', 'e:', 'cs:', 'hbp:', 'sf:', 'sh:',
                     'dp:', 'lob:', 'wp:', 'pb:', 'bk:', 'w:', 'l:', 's:', 'sv:', 'lp:']
    if any(name_lower.startswith(prefix) for prefix in note_prefixes):
        return False

    # Skip if name ends with (1), (2), etc. - game note counts
    if re.search(r'\(\d+\)\s*$', name):
        return False

    # Skip win-loss records like (3-2)
    if re.search(r'\(\d+[-/]\d+\)\s*$', name):
        return False

    return True


def is_valid_stat_player(name: str) -> bool:
    """Check if a name from game notes is a valid player (not a stat prefix)."""
    if not name:
        return False
    # Skip entries that are clearly stat prefixes, not player names
    invalid_prefixes = ['SH', 'SF', 'SFA', 'HBP', 'CS', 'SB', 'GDP', 'LOB', 'DP', 'WP', 'PB', 'BK', 'IBB', 'E', 'PO']
    name_upper = name.upper().strip()
    for prefix in invalid_prefixes:
        if name_upper.startswith(prefix + ' ') or name_upper.startswith(prefix + '-') or name_upper.startswith(prefix + ':'):
            return False
        if name_upper == prefix:
            return False
    # Skip entries that look like "DP: 2" or similar
    if re.match(r'^[A-Z]+\s*:\s*\d+$', name_upper):
        return False
    return True


def build_extra_base_lookup(game_notes: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Build a lookup of player names to their extra-base hit counts from game notes.

    Game notes contain:
    - home_runs: [{"player": "LastName", "game_count": X, "season_total": Y}, ...]
    - doubles: [{"player": "LastName", "game_count": X, "season_total": Y}, ...]
    - triples: ["LastName", ...] or [{"player": "LastName", ...}, ...]
    - stolen_bases: ["LastName (count)", ...]

    Returns dict: {normalized_name: {"hr": X, "2b": Y, "3b": Z, "sb": W}}
    """
    lookup = {}

    def normalize_name(name: str) -> str:
        """Normalize player name for matching (lowercase, remove punctuation)."""
        if not name:
            return ""
        # Remove parenthetical content like "(19)" and common suffixes
        name = re.sub(r'\s*\([^)]*\)\s*', '', name)
        name = re.sub(r'\s*\d+\s*$', '', name)  # Remove trailing numbers
        return name.lower().strip().replace(',', '').replace('.', '')

    def add_to_lookup(name: str, stat: str, count: int):
        """Add a stat count to the lookup for a player."""
        norm = normalize_name(name)
        if not norm:
            return
        if norm not in lookup:
            lookup[norm] = {"hr": 0, "2b": 0, "3b": 0, "sb": 0}
        lookup[norm][stat] += count

    # Process home runs
    for item in game_notes.get('home_runs', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count = 1
        # Validate that this is actually a player name, not a stat prefix
        if is_valid_stat_player(name):
            add_to_lookup(name, 'hr', count)

    # Process doubles
    for item in game_notes.get('doubles', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count = 1
        # Validate that this is actually a player name, not a stat prefix
        if is_valid_stat_player(name):
            add_to_lookup(name, '2b', count)

    # Process triples
    for item in game_notes.get('triples', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count = 1
        # Validate that this is actually a player name, not a stat prefix
        if is_valid_stat_player(name):
            add_to_lookup(name, '3b', count)

    # Process stolen bases - format: "LastName (count)" or just "LastName"
    for item in game_notes.get('stolen_bases', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            # Try to extract count from format like "Player (5)"
            count_match = re.search(r'\((\d+)\)', name)
            count = int(count_match.group(1)) if count_match else 1
        # Validate that this is actually a player name, not a stat prefix
        if is_valid_stat_player(name):
            add_to_lookup(name, 'sb', count)

    return lookup


def get_player_extra_stats(player_name: str, lookup: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    """Get extra-base hit stats for a player from the lookup.

    Tries to match by last name since game notes typically only have last names.
    """
    def normalize_name(name: str) -> str:
        if not name:
            return ""
        return name.lower().strip().replace(',', '').replace('.', '')

    # Try exact match first
    norm = normalize_name(player_name)
    if norm in lookup:
        return lookup[norm]

    # Try matching by last name only (for full names like "John Smith")
    parts = player_name.split()
    if parts:
        last_name = normalize_name(parts[-1])
        if last_name in lookup:
            return lookup[last_name]

        # Try first part if it looks like "LastName, First"
        if ',' in player_name:
            last_name = normalize_name(parts[0].rstrip(','))
            if last_name in lookup:
                return lookup[last_name]

    return {"hr": 0, "2b": 0, "3b": 0, "sb": 0}


class MilestonesProcessor:
    """Process and compile baseball milestones across games."""

    def __init__(self, games: List[Dict[str, Any]]):
        self.games = games

    def process_all_milestones(self) -> Dict[str, pd.DataFrame]:
        """
        Process all milestones from all games.

        Returns:
            Dictionary of milestone type -> DataFrame
        """
        milestones = {
            # Batting milestones
            'multi_hr_games': [],
            'hr_games': [],
            'four_hit_games': [],
            'three_hit_games': [],
            'five_rbi_games': [],
            'four_rbi_games': [],
            'three_rbi_games': [],
            'cycle_watch': [],
            'multi_sb_games': [],

            # Pitching milestones
            'ten_k_games': [],
            'quality_starts': [],
            'complete_games': [],
            'shutouts': [],
            'no_hitters': [],
        }

        for game in self.games:
            meta = game.get('metadata', {})
            box_score = game.get('box_score', {})
            game_notes = game.get('game_notes', {})

            date = meta.get('date', '')
            game_id = f"{date}_{meta.get('away_team', '')}_{meta.get('home_team', '')}"

            # Build lookup for extra-base hits from game notes
            extra_stats_lookup = build_extra_base_lookup(game_notes)

            # Process batting milestones
            for side in ['away', 'home']:
                team = normalize_team_name(meta.get(f'{side}_team', ''))
                opponent = normalize_team_name(meta.get('home_team' if side == 'away' else 'away_team', ''))
                team_score = safe_int(meta.get(f'{side}_team_score', 0))
                opp_score = safe_int(meta.get('home_team_score' if side == 'away' else 'away_team_score', 0))

                batters = box_score.get(f'{side}_batting', [])
                for player in batters:
                    name = player.get('full_name') or player.get('name', '')
                    if not is_valid_player_name(name):
                        continue

                    # Get extra-base hit stats from game notes lookup
                    extra_stats = get_player_extra_stats(name, extra_stats_lookup)

                    h = safe_int(player.get('hits', player.get('h', 0)))
                    rbi = safe_int(player.get('rbi', 0))

                    # Use game notes for HR, 2B, 3B, SB (more reliable than box score columns)
                    hr = extra_stats['hr'] or safe_int(player.get('hr', player.get('home_runs', 0)))
                    doubles = extra_stats['2b'] or safe_int(player.get('doubles', player.get('2b', 0)))
                    triples = extra_stats['3b'] or safe_int(player.get('triples', player.get('3b', 0)))
                    sb = extra_stats['sb'] or safe_int(player.get('sb', player.get('stolen_bases', 0)))

                    base_info = {
                        'Date': date,
                        'Player': name,
                        'Team': team,
                        'Opponent': opponent,
                        'Score': f"{team_score}-{opp_score}",
                        'GameID': game_id,
                    }

                    # Check HR milestones
                    if hr >= 2:
                        milestones['multi_hr_games'].append({
                            **base_info,
                            'HR': hr,
                            'H': h,
                            'RBI': rbi,
                        })
                    if hr >= 1:
                        milestones['hr_games'].append({
                            **base_info,
                            'HR': hr,
                            'H': h,
                            'RBI': rbi,
                        })

                    # Check hit milestones
                    if h >= 4:
                        milestones['four_hit_games'].append({
                            **base_info,
                            'H': h,
                            'R': safe_int(player.get('runs', player.get('r', 0))),
                            'RBI': rbi,
                        })
                    if h >= 3:
                        milestones['three_hit_games'].append({
                            **base_info,
                            'H': h,
                            'R': safe_int(player.get('runs', player.get('r', 0))),
                            'RBI': rbi,
                        })

                    # Check RBI milestones
                    if rbi >= 5:
                        milestones['five_rbi_games'].append({
                            **base_info,
                            'RBI': rbi,
                            'H': h,
                            'HR': hr,
                        })
                    if rbi >= 4:
                        milestones['four_rbi_games'].append({
                            **base_info,
                            'RBI': rbi,
                            'H': h,
                            'HR': hr,
                        })
                    if rbi >= 3:
                        milestones['three_rbi_games'].append({
                            **base_info,
                            'RBI': rbi,
                            'H': h,
                            'HR': hr,
                        })

                    # Check for cycle watch (3 of 4 types of hits)
                    singles = h - doubles - triples - hr
                    hit_types = sum([1 for x in [singles, doubles, triples, hr] if x > 0])
                    if hit_types >= 3 and h >= 3:
                        milestones['cycle_watch'].append({
                            **base_info,
                            'H': h,
                            '1B': singles,
                            '2B': doubles,
                            '3B': triples,
                            'HR': hr,
                        })

                    # Check SB milestones
                    if sb >= 2:
                        milestones['multi_sb_games'].append({
                            **base_info,
                            'SB': sb,
                            'H': h,
                            'R': safe_int(player.get('runs', player.get('r', 0))),
                        })

                # Process pitching milestones
                pitchers = box_score.get(f'{side}_pitching', [])
                for player in pitchers:
                    name = player.get('full_name') or player.get('name', '')
                    if not is_valid_player_name(name):
                        continue

                    ip = parse_innings_pitched(player.get('innings_pitched', 0))
                    k = safe_int(player.get('strikeouts', player.get('k', 0)))
                    er = safe_int(player.get('earned_runs', player.get('er', 0)))
                    h = safe_int(player.get('hits', player.get('h', 0)))
                    bb = safe_int(player.get('walks', player.get('bb', 0)))

                    base_info = {
                        'Date': date,
                        'Player': name,
                        'Team': team,
                        'Opponent': opponent,
                        'Score': f"{team_score}-{opp_score}",
                        'GameID': game_id,
                    }

                    # 10+ K games
                    if k >= 10:
                        milestones['ten_k_games'].append({
                            **base_info,
                            'IP': f"{int(ip)}.{int((ip % 1) * 3)}",
                            'K': k,
                            'H': h,
                            'ER': er,
                            'BB': bb,
                        })

                    # Quality starts (6+ IP, 3 or fewer ER)
                    if ip >= 6 and er <= 3:
                        milestones['quality_starts'].append({
                            **base_info,
                            'IP': f"{int(ip)}.{int((ip % 1) * 3)}",
                            'K': k,
                            'H': h,
                            'ER': er,
                            'BB': bb,
                        })

                    # Complete games (9+ IP)
                    if ip >= 9:
                        milestones['complete_games'].append({
                            **base_info,
                            'IP': f"{int(ip)}.{int((ip % 1) * 3)}",
                            'K': k,
                            'H': h,
                            'ER': er,
                            'BB': bb,
                        })

                    # Shutouts (9+ IP, 0 ER)
                    if ip >= 9 and er == 0:
                        milestones['shutouts'].append({
                            **base_info,
                            'IP': f"{int(ip)}.{int((ip % 1) * 3)}",
                            'K': k,
                            'H': h,
                            'ER': er,
                            'BB': bb,
                        })

                    # No-hitters (9+ IP, 0 H)
                    if ip >= 9 and h == 0:
                        milestones['no_hitters'].append({
                            **base_info,
                            'IP': f"{int(ip)}.{int((ip % 1) * 3)}",
                            'K': k,
                            'H': h,
                            'ER': er,
                            'BB': bb,
                        })

        # Convert to DataFrames
        result = {}
        for key, entries in milestones.items():
            if entries:
                df = pd.DataFrame(entries)
                if 'Date' in df.columns:
                    df = df.sort_values('Date', ascending=False)
                result[key] = df
            else:
                result[key] = pd.DataFrame()

        return result
