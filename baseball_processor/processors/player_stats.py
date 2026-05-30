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
    parse_innings_pitched, is_placeholder_player_name,
    resolve_player_display_name
)
from ..utils.constants import get_conference
from ..normalization import alias_display_name, build_player_name_aliases, normalized_raw_sections, resolve_player_name_alias
from ..player_display import best_display_name as _best_display_name, row_source_display_name as _row_source_display_name
from .milestones import normalize_player_name


COMPACT_INITIAL_TOKENS = {
    "aj", "bj", "cj", "dj", "jd", "jj", "jp", "jt", "pj", "rj", "tj", "jc",
}


def _smart_title_word(word: str) -> str:
    token = re.sub(r'[^a-z]', '', word.lower())
    if token in COMPACT_INITIAL_TOKENS:
        if "." in word:
            return ".".join(letter.upper() for letter in token) + "."
        return token.upper()
    if len(word) <= 3 and word.isupper() and word.isalpha():
        return word

    titled = word.title()
    if re.fullmatch(r"mc[a-z]+", word.lower()) and len(word) > 2:
        return "Mc" + word[2:].capitalize()
    return titled


def smart_title(name: str) -> str:
    """Title-case a name while preserving compact initial tokens like RJ, AJ, JT."""
    words = name.split()
    return ' '.join(_smart_title_word(word) for word in words)


def build_extra_base_lookup(game_notes: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Build a lookup of player names to their extra-base hit counts from game notes.

    Returns dict: {normalized_name: {"hr": X, "2b": Y, "3b": Z, "sb": W}}
    """
    lookup = {}

    def clean_note_name(name: str) -> str:
        if not name:
            return ""
        name = re.sub(r'\s*\([^)]*\)\s*', '', name)
        name = re.sub(r'\s*\d+\s*$', '', name)  # Remove trailing numbers
        return name.strip()

    def normalize_lookup_name(name: str) -> str:
        """Normalize player name for matching."""
        name = clean_note_name(name)
        if not name:
            return ""
        return re.sub(r'[^a-z0-9]+', ' ', normalize_player_name(name).lower()).strip()

    def note_lookup_keys(name: str) -> List[str]:
        """Build exact and comma-initial keys without unsafe surname-only guesses."""
        name = clean_note_name(name)
        if not name:
            return []
        keys = []
        if ',' in name:
            last, first = name.split(',', 1)
            last_key = re.sub(r'[^a-z0-9]+', ' ', last.lower()).strip()
            first_key = re.sub(r'[^a-z0-9]+', ' ', first.lower()).strip()
            if first_key and last_key:
                keys.append(re.sub(r'[^a-z0-9]+', ' ', f'{first_key} {last_key}').strip())
                keys.append(f'{last_key}|{first_key[0]}')
            elif last_key:
                keys.append(last_key)
        else:
            keys.append(normalize_lookup_name(name))
        return [key for key in dict.fromkeys(keys) if key]

    def add_to_lookup(name: str, stat: str, count: int):
        """Add a stat count to the lookup for a player."""
        for norm in note_lookup_keys(name):
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
            count_match = re.search(r'\((\d+)\)', name)
            count = int(count_match.group(1)) if count_match else 1
        if is_valid_player(name):
            add_to_lookup(name, 'hr', count)

    # Process doubles
    for item in game_notes.get('doubles', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count_match = re.search(r'\((\d+)\)', name)
            count = int(count_match.group(1)) if count_match else 1
        if is_valid_player(name):
            add_to_lookup(name, '2b', count)

    # Process triples
    for item in game_notes.get('triples', []):
        if isinstance(item, dict):
            name = item.get('player', '')
            count = item.get('game_count', 1)
        else:
            name = str(item)
            count_match = re.search(r'\((\d+)\)', name)
            count = int(count_match.group(1)) if count_match else 1
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
        return re.sub(r'[^a-z0-9]+', ' ', normalize_player_name(name).lower()).strip()

    # Try exact match first
    norm = normalize_lookup_name(player_name)
    if norm in lookup:
        return lookup[norm]

    # Try matching by last name only (for full names like "John Smith")
    parts = norm.split()
    if parts:
        first_initial_key = f'{parts[-1]}|{parts[0][0]}'
        if first_initial_key in lookup:
            return lookup[first_initial_key]
        if parts[-1] in lookup:
            return lookup[parts[-1]]

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
        self._bref_id_to_key = {}  # bref_id -> canonical key (for merging transfers)
        self._name_aliases = {}  # (team, abbreviated normalized name) -> full normalized name
        self._player_name_aliases = build_player_name_aliases(games)

    @staticmethod
    def _team_alias_key(team: str) -> str:
        """Return a conservative source-agnostic team key for identity aliases."""
        team = re.sub(r'\s*\(CA\)\s*$', '', str(team or '').strip(), flags=re.IGNORECASE)
        key = re.sub(r'[^a-z0-9]', '', team.lower())
        if key == 'loyolamarymount':
            return 'lmu'
        return key

    @staticmethod
    def _last_name_token(normalized_name: str) -> str:
        parts = normalized_name.split()
        if not parts:
            return ''
        return re.sub(r'[^a-z]', '', parts[-1])

    @staticmethod
    def _name_alias_key(display_name: str, team: str):
        """Return a conservative same-team initial+surname key for name aliases."""
        normalized = normalize_name(display_name)
        parts = normalized.split()
        if len(parts) < 2:
            return None, False, normalized

        first_letters = re.sub(r'[^a-z]', '', parts[0])
        last = re.sub(r'[^a-z]', '', parts[-1])
        if not first_letters or not last:
            return None, False, normalized

        is_initial_only = len(first_letters) == 1
        return (PlayerStatsProcessor._team_alias_key(team), first_letters[0], last), is_initial_only, normalized

    def _build_name_aliases(self):
        """Map abbreviated NCAA API names to a unique full same-team name."""
        initial_candidates = defaultdict(set)
        last_name_candidates = defaultdict(set)
        last_name_candidates_by_team = defaultdict(list)
        abbreviated = []
        surname_only = []

        for game in self.games:
            meta = game.get('metadata', {})
            box_score = game.get('box_score', {})
            for side in ['away', 'home']:
                team = meta.get(f'{side}_team', '')
                team_key = self._team_alias_key(team)
                for section in [f'{side}_batting', f'{side}_pitching']:
                    for player in box_score.get(section, []):
                        bref_id = player.get('bref_id') or player.get('register_id')
                        display_name = resolve_player_display_name(
                            _row_source_display_name(player),
                            bref_id,
                        )
                        display_name = normalize_player_name(display_name)
                        if is_placeholder_player_name(display_name):
                            continue
                        alias_key, is_initial_only, normalized = self._name_alias_key(display_name, team)
                        if not alias_key:
                            last = self._last_name_token(normalized)
                            if last and len(last) >= 4:
                                surname_only.append((team, normalized, team_key, last))
                            continue

                        last = self._last_name_token(normalized)
                        if is_initial_only:
                            abbreviated.append((team, normalized, alias_key))
                        else:
                            initial_candidates[alias_key].add(normalized)
                            if last:
                                last_name_candidates[(team_key, last)].add(normalized)
                                last_name_candidates_by_team[team_key].append((last, normalized))

        for team, abbreviated_name, alias_key in abbreviated:
            candidates = initial_candidates.get(alias_key, set())
            if len(candidates) == 1:
                self._name_aliases[(team, abbreviated_name)] = next(iter(candidates))

        for team, surname_name, team_key, last in surname_only:
            candidates = set(last_name_candidates.get((team_key, last), set()))
            if not candidates:
                for candidate_last, candidate_name in last_name_candidates_by_team.get(team_key, []):
                    if len(last) >= 5 and (candidate_last.startswith(last) or last.startswith(candidate_last)):
                        candidates.add(candidate_name)
            if len(candidates) == 1:
                self._name_aliases[(team, surname_name)] = next(iter(candidates))

    def _build_transfer_set(self):
        """Pre-scan all games to identify bref_ids that are genuine transfers
        vs. different players who happen to share a name/bref_id.

        A bref_id is a false merge if it appears on two different teams
        in the same game (e.g., opposing players named "Lucas Kelly").
        """
        from collections import defaultdict
        # bref_id -> set of (game_id, team) appearances
        bref_game_teams = defaultdict(list)

        for game in self.games:
            meta = game.get('metadata', {})
            box_score = game.get('box_score', {})
            game_id = f"{meta.get('date', '')}_{meta.get('away_team', '')}_{meta.get('home_team', '')}"

            for side in ['away', 'home']:
                team = meta.get(f'{side}_team', '')
                for section in [f'{side}_batting', f'{side}_pitching']:
                    for player in box_score.get(section, []):
                        bref_id = player.get('bref_id')
                        if bref_id:
                            bref_game_teams[bref_id].append((game_id, team))

        # A bref_id is a false collision if it appears on different teams
        # in the same game
        self._false_merge_bref_ids = set()
        for bref_id, appearances in bref_game_teams.items():
            games_seen = defaultdict(set)
            for game_id, team in appearances:
                games_seen[game_id].add(team)
            for game_id, teams in games_seen.items():
                if len(teams) > 1:
                    self._false_merge_bref_ids.add(bref_id)
                    break

    def _resolve_player_key(self, normalized_name: str, team: str, bref_id: str = None) -> str:
        """Resolve the canonical key for a player.

        Uses bref_id to merge players across teams (e.g., transfers).
        Falls back to name|team when no bref_id is available, or when
        the bref_id is a known false collision (different players with
        the same name appearing in the same game).
        """
        team_key = self._team_alias_key(team) or team
        if bref_id and bref_id not in self._false_merge_bref_ids:
            if bref_id in self._bref_id_to_key:
                return self._bref_id_to_key[bref_id]
            # New bref_id — create canonical key using name|first_team
            key = f"{normalized_name}|{team_key}"
            self._bref_id_to_key[bref_id] = key
            return key
        # No bref_id or false collision — fall back to name|team
        return f"{normalized_name}|{team_key}"

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
        self._build_transfer_set()
        self._build_name_aliases()

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
            batting_sections, pitching_sections = normalized_raw_sections(game, self._player_name_aliases)

            # Process batting stats
            for side in ['away', 'home']:
                team = meta.get(f'{side}_team', '')
                opponent = meta.get('home_team' if side == 'away' else 'away_team', '')
                team_score = safe_int(meta.get(f'{side}_team_score', 0))
                opp_score = safe_int(meta.get('home_team_score' if side == 'away' else 'away_team_score', 0))
                won = team_score > opp_score

                batters = batting_sections.get(side, [])
                for player in batters:
                    bref_id = player.get('bref_id') or player.get('register_id')
                    name = resolve_player_display_name(_row_source_display_name(player), bref_id)
                    name = normalize_player_name(name)
                    if is_placeholder_player_name(name):
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
                    alias = resolve_player_name_alias(name, team, self._player_name_aliases)
                    if alias:
                        name = alias_display_name(name, alias)
                        bref_id = bref_id or alias.get('bref_id', '')
                        normalized_name = normalize_name(name)
                    normalized_name = self._name_aliases.get((team, normalized_name), normalized_name)
                    # Use bref_id to merge transfers; fall back to name|team
                    key = self._resolve_player_key(normalized_name, team, bref_id)
                    if bref_id:
                        self.player_bref_ids[key] = bref_id

                    self.player_teams[key].add(team)
                    if game_year:
                        self.player_team_years[key][team].append(game_year)
                    self.batter_totals[key]['games'] += 1
                    self.batter_totals[key]['_name'] = normalized_name  # Store original name for display
                    self.batter_totals[key]['_display_name'] = _best_display_name(
                        self.batter_totals[key].get('_display_name', ''),
                        name,
                    )

                    # Get extra-base hit stats from game notes lookup
                    extra_stats = get_player_extra_stats(name, extra_stats_lookup)

                    # Aggregate batting stats
                    for stat in batting_keys:
                        # For HR, 2B, 3B, SB - prefer game notes over box score
                        if stat == 'hr':
                            val = extra_stats['hr'] or safe_int(self._stat_value(player, stat))
                        elif stat == 'doubles':
                            val = extra_stats['2b'] or safe_int(self._stat_value(player, stat))
                        elif stat == 'triples':
                            val = extra_stats['3b'] or safe_int(self._stat_value(player, stat))
                        elif stat == 'sb':
                            val = extra_stats['sb'] or safe_int(self._stat_value(player, stat))
                        else:
                            val = safe_int(self._stat_value(player, stat))
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
                            game_stats[stat] = extra_stats['hr'] or safe_int(self._stat_value(player, stat))
                        elif stat == 'doubles':
                            game_stats[stat] = extra_stats['2b'] or safe_int(self._stat_value(player, stat))
                        elif stat == 'triples':
                            game_stats[stat] = extra_stats['3b'] or safe_int(self._stat_value(player, stat))
                        elif stat == 'sb':
                            game_stats[stat] = extra_stats['sb'] or safe_int(self._stat_value(player, stat))
                        else:
                            game_stats[stat] = safe_int(self._stat_value(player, stat))
                    self.batter_games[key].append(game_stats)

                # Process pitching stats
                pitchers = pitching_sections.get(side, [])
                for player in pitchers:
                    bref_id = player.get('bref_id') or player.get('register_id')
                    name = resolve_player_display_name(_row_source_display_name(player), bref_id)
                    name = normalize_player_name(name)
                    if is_placeholder_player_name(name):
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
                    alias = resolve_player_name_alias(name, team, self._player_name_aliases)
                    if alias:
                        name = alias_display_name(name, alias)
                        bref_id = bref_id or alias.get('bref_id', '')
                        normalized_name = normalize_name(name)
                    normalized_name = self._name_aliases.get((team, normalized_name), normalized_name)
                    # Use bref_id to merge transfers; fall back to name|team
                    key = self._resolve_player_key(normalized_name, team, bref_id)
                    if bref_id:
                        self.player_bref_ids[key] = bref_id

                    self.player_teams[key].add(team)
                    if game_year:
                        self.player_team_years[key][team].append(game_year)
                    self.pitcher_totals[key]['games'] += 1
                    self.pitcher_totals[key]['_name'] = normalized_name  # Store original name for display
                    self.pitcher_totals[key]['_display_name'] = _best_display_name(
                        self.pitcher_totals[key].get('_display_name', ''),
                        name,
                    )

                    # Innings pitched needs special handling
                    ip = parse_innings_pitched(self._stat_value(player, 'ip'))
                    self.pitcher_totals[key]['ip'] += ip

                    for stat in pitching_keys:
                        if stat == 'ip':
                            continue
                        val = safe_int(self._stat_value(player, stat))
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
                        game_stats[stat] = safe_int(self._stat_value(player, stat))
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

    def _stat_value(self, player: Dict[str, Any], stat: str, default: Any = 0) -> Any:
        """Read a stat across source-specific casing and aliases."""
        keys = [stat, stat.upper(), self._stat_alias(stat)]
        if stat == 'ip':
            keys.extend(['IP', 'innings_pitched'])
        elif stat == 'doubles':
            keys.extend(['2B', '2b'])
        elif stat == 'triples':
            keys.extend(['3B', '3b'])
        for key in keys:
            if key in player and player[key] not in (None, ''):
                return player[key]
        return default

    def _display_name_for_key(self, key: str, stats: Dict[str, Any]) -> str:
        display_name = stats.get('_display_name') or stats.get('_name') or key.split('|')[0]
        return smart_title(str(display_name))

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

            display_name = self._display_name_for_key(key, stats)

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

            display_name = self._display_name_for_key(key, stats)

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
            display_name = self._display_name_for_key(key, self.batter_totals[key])
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
            display_name = self._display_name_for_key(key, self.pitcher_totals[key])
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
