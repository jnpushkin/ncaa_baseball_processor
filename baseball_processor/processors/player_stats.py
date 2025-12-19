"""
Player statistics aggregation processor for baseball.
"""

import re
from typing import Dict, List, Any
import pandas as pd
from collections import defaultdict

from ..utils.helpers import (
    safe_int, safe_float, normalize_name,
    calculate_batting_average, calculate_era, calculate_whip,
    parse_innings_pitched
)
from ..utils.constants import get_conference


def build_extra_base_lookup(game_notes: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Build a lookup of player names to their extra-base hit counts from game notes.

    Returns dict: {normalized_name: {"hr": X, "2b": Y, "3b": Z, "sb": W}}
    """
    lookup = {}

    def normalize_lookup_name(name: str) -> str:
        """Normalize player name for matching (lowercase, remove punctuation)."""
        if not name:
            return ""
        # Remove parenthetical content like "(19)" and common suffixes
        name = re.sub(r'\s*\([^)]*\)\s*', '', name)
        name = re.sub(r'\s*\d+\s*$', '', name)  # Remove trailing numbers
        return name.lower().strip().replace(',', '').replace('.', '')

    def add_to_lookup(name: str, stat: str, count: int):
        """Add a stat count to the lookup for a player."""
        norm = normalize_lookup_name(name)
        if not norm:
            return
        if norm not in lookup:
            lookup[norm] = {"hr": 0, "2b": 0, "3b": 0, "sb": 0}
        lookup[norm][stat] += count

    def is_valid_player(name: str) -> bool:
        """Check if a name is a valid player (not a stat prefix)."""
        if not name:
            return False
        invalid_prefixes = ['SH', 'SF', 'SFA', 'HBP', 'CS', 'SB', 'GDP', 'LOB', 'DP', 'WP', 'PB', 'BK', 'IBB', 'E', 'PO']
        name_upper = name.upper().strip()
        for prefix in invalid_prefixes:
            if name_upper.startswith(prefix + ' ') or name_upper.startswith(prefix + '-') or name_upper.startswith(prefix + ':'):
                return False
            if name_upper == prefix:
                return False
        return True

    # Process home runs
    for item in game_notes.get('home_runs', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count = 1
        if is_valid_player(name):
            add_to_lookup(name, 'hr', count)

    # Process doubles
    for item in game_notes.get('doubles', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count = 1
        if is_valid_player(name):
            add_to_lookup(name, '2b', count)

    # Process triples
    for item in game_notes.get('triples', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count = 1
        if is_valid_player(name):
            add_to_lookup(name, '3b', count)

    # Process stolen bases
    for item in game_notes.get('stolen_bases', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count_match = re.search(r'\((\d+)\)', name)
            count = int(count_match.group(1)) if count_match else 1
        if is_valid_player(name):
            add_to_lookup(name, 'sb', count)

    return lookup


def get_player_extra_stats(player_name: str, lookup: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    """Get extra-base hit stats for a player from the lookup.

    Tries to match by last name since game notes typically only have last names.
    """
    def normalize_lookup_name(name: str) -> str:
        if not name:
            return ""
        return name.lower().strip().replace(',', '').replace('.', '')

    # Try exact match first
    norm = normalize_lookup_name(player_name)
    if norm in lookup:
        return lookup[norm]

    # Try matching by last name only (for full names like "John Smith")
    parts = player_name.split()
    if parts:
        last_name = normalize_lookup_name(parts[-1])
        if last_name in lookup:
            return lookup[last_name]

        # Try first part if it looks like "LastName, First"
        if ',' in player_name:
            last_name = normalize_lookup_name(parts[0].rstrip(','))
            if last_name in lookup:
                return lookup[last_name]

    return {"hr": 0, "2b": 0, "3b": 0, "sb": 0}


class PlayerStatsProcessor:
    """Process and aggregate player statistics across games."""

    def __init__(self, games: List[Dict[str, Any]]):
        self.games = games
        self.batter_totals = defaultdict(lambda: defaultdict(int))
        self.pitcher_totals = defaultdict(lambda: defaultdict(float))
        self.batter_games = defaultdict(list)
        self.pitcher_games = defaultdict(list)
        self.player_teams = defaultdict(set)
        self.player_team_years = defaultdict(lambda: defaultdict(list))  # key -> team -> [years]
        self.player_bref_ids = {}

    def process_all_stats(self) -> Dict[str, pd.DataFrame]:
        """
        Process all player statistics.

        Returns:
            Dictionary with 'batters', 'pitchers', 'batter_games', 'pitcher_games'
        """
        self._aggregate_stats()

        return {
            'batters': self._create_batters_dataframe(),
            'pitchers': self._create_pitchers_dataframe(),
            'batter_games': self._create_batter_games_dataframe(),
            'pitcher_games': self._create_pitcher_games_dataframe(),
        }

    def _aggregate_stats(self):
        """Aggregate statistics for each player across all games."""

        batting_keys = ['ab', 'r', 'h', 'rbi', 'bb', 'k', 'po', 'a', 'lob',
                        'doubles', 'triples', 'hr', 'sb', 'cs', 'hbp', 'sf', 'sh']
        pitching_keys = ['ip', 'h', 'r', 'er', 'bb', 'k', 'bf', 'np', 'hr']

        for game in self.games:
            meta = game.get('metadata', {})
            box_score = game.get('box_score', {})
            game_notes = game.get('game_notes', {})

            game_id = f"{meta.get('date', 'unknown')}_{meta.get('away_team', '')}_{meta.get('home_team', '')}"
            date = meta.get('date', '')

            # Extract year from date for conference lookup
            game_year = None
            if date:
                try:
                    if '/' in date:
                        parts = date.split('/')
                        game_year = int(parts[-1]) if len(parts[-1]) == 4 else int(parts[0])
                    elif '-' in date:
                        game_year = int(date.split('-')[0])
                except (ValueError, IndexError):
                    pass

            # Build lookup for extra-base hits from game notes
            extra_stats_lookup = build_extra_base_lookup(game_notes)

            # Process batting stats
            for side in ['away', 'home']:
                team = meta.get(f'{side}_team', '')
                opponent = meta.get('home_team' if side == 'away' else 'away_team', '')
                team_score = safe_int(meta.get(f'{side}_team_score', 0))
                opp_score = safe_int(meta.get('home_team_score' if side == 'away' else 'away_team_score', 0))
                won = team_score > opp_score

                batters = box_score.get(f'{side}_batting', [])
                for player in batters:
                    name = player.get('full_name') or player.get('name', '')
                    if not name:
                        continue

                    # Skip totals and game notes rows
                    name_lower = name.lower()
                    if 'totals' in name_lower:
                        continue
                    # Skip game notes that got parsed as players (SB:, 2B:, 3B:, HR:, E:, CS:, etc.)
                    if any(name_lower.startswith(prefix) for prefix in ['sb:', '2b:', '3b:', 'hr:', 'e:', 'cs:', 'hbp:', 'sf:', 'sh:', 'dp:', 'lob:', 'wp:', 'pb:', 'bk:']):
                        continue
                    # Skip if name contains "(1)" type patterns indicating game notes
                    if re.search(r'\(\d+\)\s*$', name):
                        continue

                    normalized_name = normalize_name(name)
                    # Use name + team as key to prevent merging different players with same name
                    key = f"{normalized_name}|{team}"
                    bref_id = player.get('bref_id')
                    if bref_id:
                        self.player_bref_ids[key] = bref_id

                    self.player_teams[key].add(team)
                    if game_year:
                        self.player_team_years[key][team].append(game_year)
                    self.batter_totals[key]['games'] += 1
                    self.batter_totals[key]['_name'] = normalized_name  # Store original name for display

                    # Get extra-base hit stats from game notes lookup
                    extra_stats = get_player_extra_stats(name, extra_stats_lookup)

                    # Aggregate batting stats
                    for stat in batting_keys:
                        # For HR, 2B, 3B, SB - prefer game notes over box score
                        if stat == 'hr':
                            val = extra_stats['hr'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        elif stat == 'doubles':
                            val = extra_stats['2b'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        elif stat == 'triples':
                            val = extra_stats['3b'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        elif stat == 'sb':
                            val = extra_stats['sb'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        else:
                            val = safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        self.batter_totals[key][stat] += val

                    # Track game-by-game
                    game_stats = {
                        'date': date,
                        'team': team,
                        'opponent': opponent,
                        'won': won,
                        'game_id': game_id,
                    }
                    for stat in batting_keys:
                        if stat == 'hr':
                            game_stats[stat] = extra_stats['hr'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        elif stat == 'doubles':
                            game_stats[stat] = extra_stats['2b'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        elif stat == 'triples':
                            game_stats[stat] = extra_stats['3b'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        elif stat == 'sb':
                            game_stats[stat] = extra_stats['sb'] or safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        else:
                            game_stats[stat] = safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                    self.batter_games[key].append(game_stats)

                # Process pitching stats
                pitchers = box_score.get(f'{side}_pitching', [])
                for player in pitchers:
                    name = player.get('full_name') or player.get('name', '')
                    if not name:
                        continue

                    # Skip totals and game notes rows
                    name_lower = name.lower()
                    if 'totals' in name_lower:
                        continue
                    # Skip game notes
                    if any(name_lower.startswith(prefix) for prefix in ['w:', 'l:', 's:', 'wp:', 'lp:', 'sv:', 'hbp:', 'wp:', 'pb:', 'bk:']):
                        continue
                    if re.search(r'\(\d+[-/]\d+\)\s*$', name):  # Win-loss records like (3-2)
                        continue

                    normalized_name = normalize_name(name)
                    # Use name + team as key to prevent merging different players with same name
                    key = f"{normalized_name}|{team}"
                    bref_id = player.get('bref_id')
                    if bref_id:
                        self.player_bref_ids[key] = bref_id

                    self.player_teams[key].add(team)
                    if game_year:
                        self.player_team_years[key][team].append(game_year)
                    self.pitcher_totals[key]['games'] += 1
                    self.pitcher_totals[key]['_name'] = normalized_name  # Store original name for display

                    # Innings pitched needs special handling
                    ip = parse_innings_pitched(player.get('innings_pitched', 0))
                    self.pitcher_totals[key]['ip'] += ip

                    for stat in pitching_keys:
                        if stat == 'ip':
                            continue
                        val = safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                        self.pitcher_totals[key][stat] += val

                    # Track game-by-game
                    # Format IP in baseball notation (6.2 = 6 and 2/3 innings)
                    ip_formatted = f"{int(ip)}.{int((ip % 1) * 3)}"
                    game_stats = {
                        'date': date,
                        'team': team,
                        'opponent': opponent,
                        'won': won,
                        'game_id': game_id,
                        'ip': ip_formatted,
                    }
                    for stat in pitching_keys:
                        if stat == 'ip':
                            continue
                        game_stats[stat] = safe_int(player.get(stat, player.get(self._stat_alias(stat), 0)))
                    self.pitcher_games[key].append(game_stats)

    def _stat_alias(self, stat: str) -> str:
        """Map stat names to possible aliases."""
        aliases = {
            'ab': 'at_bats',
            'r': 'runs',
            'h': 'hits',
            'bb': 'walks',
            'k': 'strikeouts',
            'po': 'put_outs',
            'a': 'assists',
            'lob': 'left_on_base',
            'hr': 'home_runs',
            'sb': 'stolen_bases',
            'er': 'earned_runs',
            'bf': 'batters_faced',
            'np': 'pitches',
        }
        return aliases.get(stat, stat)

    def _get_player_conference(self, key: str) -> str:
        """Get conference for a player based on their team(s) and year(s)."""
        team_years = self.player_team_years.get(key, {})
        conferences = set()

        for team, years in team_years.items():
            # Use most recent year for this team
            if years:
                year = max(years)
                conf = get_conference(team, year)
                if conf != 'Other':
                    conferences.add(conf)

        # If no conference found from year data, try without year
        if not conferences:
            for team in self.player_teams.get(key, []):
                conf = get_conference(team)
                if conf != 'Other':
                    conferences.add(conf)

        return ', '.join(sorted(conferences)) if conferences else 'Other'

    def _create_batters_dataframe(self) -> pd.DataFrame:
        """Create aggregated batters DataFrame."""
        rows = []

        for key, stats in self.batter_totals.items():
            games = stats.get('games', 0)
            if games == 0:
                continue

            ab = stats.get('ab', 0)
            h = stats.get('h', 0)
            bb = stats.get('bb', 0)
            hbp = stats.get('hbp', 0)
            sf = stats.get('sf', 0)

            # Calculate rate stats
            avg = h / ab if ab > 0 else 0
            pa = ab + bb + hbp + sf
            obp = (h + bb + hbp) / pa if pa > 0 else 0

            # Slugging
            singles = h - stats.get('doubles', 0) - stats.get('triples', 0) - stats.get('hr', 0)
            tb = singles + (2 * stats.get('doubles', 0)) + (3 * stats.get('triples', 0)) + (4 * stats.get('hr', 0))
            slg = tb / ab if ab > 0 else 0
            ops = obp + slg

            # Get display name from stored _name or parse from key
            display_name = stats.get('_name', key.split('|')[0]).title()

            rows.append({
                'Name': display_name,
                'Team': ', '.join(sorted(self.player_teams.get(key, []))),
                'Conference': self._get_player_conference(key),
                'G': games,
                'PA': pa,
                'AB': ab,
                'R': stats.get('r', 0),
                'H': h,
                '2B': stats.get('doubles', 0),
                '3B': stats.get('triples', 0),
                'HR': stats.get('hr', 0),
                'RBI': stats.get('rbi', 0),
                'BB': bb,
                'K': stats.get('k', 0),
                'SB': stats.get('sb', 0),
                'AVG': f"{avg:.3f}".lstrip('0') if avg > 0 else '.000',
                'OBP': f"{obp:.3f}".lstrip('0') if obp > 0 else '.000',
                'SLG': f"{slg:.3f}" if slg >= 1 else (f"{slg:.3f}".lstrip('0') if slg > 0 else '.000'),
                'OPS': f"{ops:.3f}" if ops >= 1 else (f"{ops:.3f}".lstrip('0') if ops > 0 else '.000'),
                'bref_id': self.player_bref_ids.get(key, ''),
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(['PA', 'H'], ascending=[False, False])
        return df

    def _create_pitchers_dataframe(self) -> pd.DataFrame:
        """Create aggregated pitchers DataFrame."""
        rows = []

        for key, stats in self.pitcher_totals.items():
            games = stats.get('games', 0)
            if games == 0:
                continue

            ip = stats.get('ip', 0)
            er = stats.get('er', 0)
            h = stats.get('h', 0)
            bb = stats.get('bb', 0)
            k = stats.get('k', 0)

            # Calculate rate stats
            era = (er * 9) / ip if ip > 0 else 0
            whip = (bb + h) / ip if ip > 0 else 0
            k_per_9 = (k * 9) / ip if ip > 0 else 0
            bb_per_9 = (bb * 9) / ip if ip > 0 else 0

            # Get display name from stored _name or parse from key
            display_name = stats.get('_name', key.split('|')[0]).title()

            rows.append({
                'Name': display_name,
                'Team': ', '.join(sorted(self.player_teams.get(key, []))),
                'Conference': self._get_player_conference(key),
                'G': games,
                'IP': f"{int(ip)}.{int((ip % 1) * 3)}",
                'H': h,
                'R': stats.get('r', 0),
                'ER': er,
                'BB': bb,
                'K': k,
                'HR': stats.get('hr', 0),
                'ERA': f"{era:.2f}" if ip > 0 else '-',
                'WHIP': f"{whip:.2f}" if ip > 0 else '-',
                'K/9': f"{k_per_9:.1f}" if ip > 0 else '-',
                'BB/9': f"{bb_per_9:.1f}" if ip > 0 else '-',
                'bref_id': self.player_bref_ids.get(key, ''),
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values('IP', ascending=False, key=lambda x: pd.to_numeric(x.str.replace('.', ''), errors='coerce'))
        return df

    def _create_batter_games_dataframe(self) -> pd.DataFrame:
        """Create game-by-game batting DataFrame."""
        rows = []
        for key, games in self.batter_games.items():
            # Get display name from stored stats or parse from key
            display_name = self.batter_totals[key].get('_name', key.split('|')[0]).title()
            for game in games:
                row = {'Name': display_name, **game}
                rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty and 'date' in df.columns:
            # Parse dates properly for sorting (M/D/YYYY format)
            df['_date_sort'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')
            df = df.sort_values('_date_sort', ascending=True)
            df = df.drop(columns=['_date_sort'])
        return df

    def _create_pitcher_games_dataframe(self) -> pd.DataFrame:
        """Create game-by-game pitching DataFrame."""
        rows = []
        for key, games in self.pitcher_games.items():
            # Get display name from stored stats or parse from key
            display_name = self.pitcher_totals[key].get('_name', key.split('|')[0]).title()
            for game in games:
                row = {'Name': display_name, **game}
                rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty and 'date' in df.columns:
            # Parse dates properly for sorting (M/D/YYYY format)
            df['_date_sort'] = pd.to_datetime(df['date'], format='%m/%d/%Y', errors='coerce')
            df = df.sort_values('_date_sort', ascending=True)
            df = df.drop(columns=['_date_sort'])
        return df
