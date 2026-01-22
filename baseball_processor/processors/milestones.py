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

    # All milestone keys for programmatic access
    MILESTONE_KEYS = [
        # Batting milestones (21)
        'three_hr_games', 'multi_hr_games', 'hr_games',
        'five_hit_games', 'four_hit_games', 'three_hit_games',
        'cycles', 'cycle_watch',
        'six_rbi_games', 'five_rbi_games', 'four_rbi_games', 'three_rbi_games',
        'multi_double_games', 'multi_triple_games', 'multi_sb_games',
        'four_walk_games', 'perfect_batting_games',
        'four_run_games', 'three_run_games',
        'hit_for_extra_bases', 'three_total_bases_games',
        # Pitching milestones (22)
        'perfect_games', 'no_hitters', 'one_hitters', 'two_hitters',
        'shutouts', 'cgso_no_walks', 'complete_games', 'low_hit_cg',
        'seven_inning_shutouts', 'maddux_games',
        'fifteen_k_games', 'twelve_k_games', 'ten_k_games', 'eight_k_games',
        'quality_starts', 'dominant_starts', 'efficient_starts',
        'high_k_low_bb', 'no_walk_starts', 'scoreless_relief',
        'win_games', 'save_games',
    ]

    def __init__(self, games: List[Dict[str, Any]]):
        self.games = games

    def process_all_milestones(self) -> Dict[str, pd.DataFrame]:
        """
        Process all milestones from all games.

        Returns:
            Dictionary of milestone type -> DataFrame
        """
        # Initialize all milestone lists
        milestones = {key: [] for key in self.MILESTONE_KEYS}

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

                    r = safe_int(player.get('runs', player.get('r', 0)))
                    bb = safe_int(player.get('walks', player.get('bb', 0)))
                    so = safe_int(player.get('strikeouts', player.get('so', player.get('k', 0))))
                    ab = safe_int(player.get('at_bats', player.get('ab', 0)))
                    singles = max(0, h - doubles - triples - hr)
                    total_bases = singles + (2 * doubles) + (3 * triples) + (4 * hr)

                    base_info = {
                        'Date': date,
                        'Player': name,
                        'Team': team,
                        'Opponent': opponent,
                        'Score': f"{team_score}-{opp_score}",
                        'GameID': game_id,
                    }

                    # HR milestones (tiered - highest first)
                    if hr >= 3:
                        milestones['three_hr_games'].append({
                            **base_info, 'HR': hr, 'H': h, 'RBI': rbi,
                        })
                    elif hr >= 2:
                        milestones['multi_hr_games'].append({
                            **base_info, 'HR': hr, 'H': h, 'RBI': rbi,
                        })
                    elif hr >= 1:
                        milestones['hr_games'].append({
                            **base_info, 'HR': hr, 'H': h, 'RBI': rbi,
                        })

                    # Hit milestones (tiered)
                    if h >= 5:
                        milestones['five_hit_games'].append({
                            **base_info, 'H': h, 'R': r, 'RBI': rbi,
                        })
                    elif h >= 4:
                        milestones['four_hit_games'].append({
                            **base_info, 'H': h, 'R': r, 'RBI': rbi,
                        })
                    elif h >= 3:
                        milestones['three_hit_games'].append({
                            **base_info, 'H': h, 'R': r, 'RBI': rbi,
                        })

                    # Cycle detection
                    hit_types = sum([1 for x in [singles, doubles, triples, hr] if x > 0])
                    if singles >= 1 and doubles >= 1 and triples >= 1 and hr >= 1:
                        milestones['cycles'].append({
                            **base_info, 'H': h, '1B': singles, '2B': doubles, '3B': triples, 'HR': hr,
                        })
                    elif hit_types >= 3 and h >= 3:
                        milestones['cycle_watch'].append({
                            **base_info, 'H': h, '1B': singles, '2B': doubles, '3B': triples, 'HR': hr,
                        })

                    # RBI milestones (tiered)
                    if rbi >= 6:
                        milestones['six_rbi_games'].append({
                            **base_info, 'RBI': rbi, 'H': h, 'HR': hr,
                        })
                    elif rbi >= 5:
                        milestones['five_rbi_games'].append({
                            **base_info, 'RBI': rbi, 'H': h, 'HR': hr,
                        })
                    elif rbi >= 4:
                        milestones['four_rbi_games'].append({
                            **base_info, 'RBI': rbi, 'H': h, 'HR': hr,
                        })
                    elif rbi >= 3:
                        milestones['three_rbi_games'].append({
                            **base_info, 'RBI': rbi, 'H': h, 'HR': hr,
                        })

                    # Extra-base hit milestones
                    if doubles >= 2:
                        milestones['multi_double_games'].append({
                            **base_info, '2B': doubles, 'H': h, 'TB': total_bases,
                        })
                    if triples >= 2:
                        milestones['multi_triple_games'].append({
                            **base_info, '3B': triples, 'H': h, 'TB': total_bases,
                        })
                    if sb >= 2:
                        milestones['multi_sb_games'].append({
                            **base_info, 'SB': sb, 'H': h, 'R': r,
                        })

                    # Walk milestones
                    if bb >= 4:
                        milestones['four_walk_games'].append({
                            **base_info, 'BB': bb, 'H': h, 'R': r,
                        })

                    # Perfect batting (3+ H, 0 K, AB > 0)
                    if h >= 3 and so == 0 and ab > 0:
                        milestones['perfect_batting_games'].append({
                            **base_info, 'H': h, 'AB': ab, 'K': so, 'AVG': f"{h/ab:.3f}",
                        })

                    # Run milestones (tiered)
                    if r >= 4:
                        milestones['four_run_games'].append({
                            **base_info, 'R': r, 'H': h, 'BB': bb,
                        })
                    elif r >= 3:
                        milestones['three_run_games'].append({
                            **base_info, 'R': r, 'H': h, 'BB': bb,
                        })

                    # Hit for extra bases (2+ XBH)
                    xbh = doubles + triples + hr
                    if xbh >= 2:
                        milestones['hit_for_extra_bases'].append({
                            **base_info, 'XBH': xbh, '2B': doubles, '3B': triples, 'HR': hr, 'TB': total_bases,
                        })

                    # Total bases milestone
                    if total_bases >= 8:
                        milestones['three_total_bases_games'].append({
                            **base_info, 'TB': total_bases, 'H': h, '2B': doubles, '3B': triples, 'HR': hr,
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
                    r = safe_int(player.get('runs', player.get('r', 0)))
                    h = safe_int(player.get('hits', player.get('h', 0)))
                    bb = safe_int(player.get('walks', player.get('bb', 0)))
                    pitches = safe_int(player.get('pitches', player.get('np', 0)))
                    decision = player.get('decision', '').upper()

                    ip_str = f"{int(ip)}.{int((ip % 1) * 3)}"
                    base_info = {
                        'Date': date,
                        'Player': name,
                        'Team': team,
                        'Opponent': opponent,
                        'Score': f"{team_score}-{opp_score}",
                        'GameID': game_id,
                    }

                    # Complete game milestones (9+ IP or 7+ for 7-inning games)
                    is_complete_game = ip >= 9
                    is_seven_inning_cg = ip >= 7 and ip < 9

                    # Perfect game (CG, 0 H, 0 BB, 0 errors)
                    if is_complete_game and h == 0 and bb == 0:
                        milestones['perfect_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb,
                        })
                    # No-hitter (CG, 0 H)
                    elif is_complete_game and h == 0:
                        milestones['no_hitters'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })
                    # One-hitter (CG, 1 H)
                    elif is_complete_game and h == 1:
                        milestones['one_hitters'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })
                    # Two-hitter (CG, 2 H)
                    elif is_complete_game and h == 2:
                        milestones['two_hitters'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })

                    # Shutout milestones
                    if is_complete_game and er == 0:
                        if bb == 0:
                            milestones['cgso_no_walks'].append({
                                **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb,
                            })
                        else:
                            milestones['shutouts'].append({
                                **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb,
                            })
                    elif is_seven_inning_cg and er == 0:
                        milestones['seven_inning_shutouts'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb,
                        })

                    # Complete game categories
                    if is_complete_game:
                        if h <= 3:
                            milestones['low_hit_cg'].append({
                                **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                            })
                        else:
                            milestones['complete_games'].append({
                                **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                            })

                    # Maddux (CG with under 100 pitches)
                    if is_complete_game and pitches > 0 and pitches < 100:
                        milestones['maddux_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'Pitches': pitches, 'H': h, 'BB': bb,
                        })

                    # Strikeout milestones (tiered)
                    if k >= 15:
                        milestones['fifteen_k_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })
                    elif k >= 12:
                        milestones['twelve_k_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })
                    elif k >= 10:
                        milestones['ten_k_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })
                    elif k >= 8:
                        milestones['eight_k_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })

                    # Quality starts (6+ IP, 3 or fewer ER)
                    if ip >= 6 and er <= 3:
                        milestones['quality_starts'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })

                    # Dominant start (7+ IP, 10+ K)
                    if ip >= 7 and k >= 10:
                        milestones['dominant_starts'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })

                    # Efficient start (6+ IP, 80 or fewer pitches)
                    if ip >= 6 and pitches > 0 and pitches <= 80:
                        milestones['efficient_starts'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'Pitches': pitches, 'H': h, 'BB': bb,
                        })

                    # High K, low BB (8+ K, 2 or fewer BB)
                    if k >= 8 and bb <= 2:
                        milestones['high_k_low_bb'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'BB': bb, 'H': h, 'ER': er,
                        })

                    # No walk start (5+ IP, 0 BB)
                    if ip >= 5 and bb == 0:
                        milestones['no_walk_starts'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'BB': bb, 'H': h, 'ER': er,
                        })

                    # Scoreless relief (3+ IP, 0 ER, not a starter)
                    if ip >= 3 and ip < 6 and er == 0:
                        milestones['scoreless_relief'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb,
                        })

                    # Win games
                    if decision == 'W':
                        milestones['win_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
                        })

                    # Save games
                    if decision == 'S' or decision == 'SV':
                        milestones['save_games'].append({
                            **base_info, 'IP': ip_str, 'K': k, 'H': h, 'BB': bb, 'ER': er,
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
