"""
Player crossover tracking across NCAA baseball, MiLB, and MLB.

This module tracks which players have been seen at multiple levels,
enabling a "player journey" view of athletes as they progress through
the baseball development pipeline.

Uses the Chadwick Bureau Register to unify player IDs across:
- key_bbref_minors (NCAA/register format): e.g., "fielde001pri"
- key_bbref (MLB format): e.g., "fieldpr01"
- key_mlbam (MLB Stats API): e.g., 425902
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

# Import player ID mapper (lazy load to avoid circular imports)
_id_mapper = None

def get_id_mapper():
    """Get or create the PlayerIDMapper instance."""
    global _id_mapper
    if _id_mapper is None:
        try:
            from baseball_processor.utils.player_ids import PlayerIDMapper
            _id_mapper = PlayerIDMapper(auto_download=True)
        except Exception as e:
            print(f"Warning: Could not load player ID mapper: {e}")
            _id_mapper = False  # Mark as failed to avoid retrying
    return _id_mapper if _id_mapper else None


@dataclass
class PlayerRecord:
    """Unified player record across all levels."""
    name: str
    bref_id: Optional[str] = None  # Baseball Reference register ID (e.g., "fielde001pri")
    mlb_bref_id: Optional[str] = None  # Baseball Reference MLB ID (e.g., "fieldpr01")
    mlb_api_id: Optional[int] = None  # MLB Stats API ID (e.g., 425902)
    ncaa_appearances: List[Dict[str, Any]] = field(default_factory=list)
    milb_appearances: List[Dict[str, Any]] = field(default_factory=list)
    mlb_appearances: List[Dict[str, Any]] = field(default_factory=list)
    teams: Set[str] = field(default_factory=set)

    def levels_seen(self) -> List[str]:
        """Return list of levels where player was seen."""
        levels = []
        if self.ncaa_appearances:
            levels.append('NCAA')
        if self.milb_appearances:
            levels.append('MiLB')
        if self.mlb_appearances:
            levels.append('MLB')
        return levels

    def total_appearances(self) -> int:
        """Total number of game appearances."""
        return len(self.ncaa_appearances) + len(self.milb_appearances) + len(self.mlb_appearances)

    def is_crossover(self) -> bool:
        """Return True if player was seen at multiple levels."""
        return len(self.levels_seen()) > 1


def normalize_name(name: str) -> str:
    """
    Normalize player name for matching.

    Args:
        name: Raw player name

    Returns:
        Normalized lowercase name
    """
    if not name:
        return ''

    # Handle "Last, First" or "Last, Initial" format
    if ',' in name:
        parts = name.split(',')
        if len(parts) == 2:
            first_part = parts[1].strip()
            last_part = parts[0].strip()
            # Check if it's just an initial (e.g., "K" or "K.")
            if len(first_part.rstrip('.')) <= 2:
                # Keep as "Initial Last" for partial matching
                name = f"{first_part.rstrip('.')} {last_part}"
            else:
                name = f"{first_part} {last_part}"

    # Remove suffixes
    name = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', name, flags=re.IGNORECASE)

    # Lowercase and strip
    return name.lower().strip()


def get_name_match_keys(name: str) -> List[str]:
    """
    Get multiple matching keys for a name to enable fuzzy matching.

    This handles cases like "Johnson, K" matching "Kyle Johnson" by creating
    keys based on last name + first initial.

    Args:
        name: Player name

    Returns:
        List of possible match keys
    """
    keys = []
    normalized = normalize_name(name)
    if normalized:
        keys.append(normalized)

    if not name:
        return keys

    # Handle "Last, Initial" format (e.g., "Johnson, K")
    if ',' in name:
        parts = name.split(',')
        if len(parts) == 2:
            first_part = parts[1].strip().rstrip('.')
            last_part = parts[0].strip().lower()
            # If it's an initial, create a partial match key
            if len(first_part) <= 2:
                # Key format: "_initial_last" for partial matching
                keys.append(f"_{first_part[0].lower()}_{last_part}")
    else:
        # Handle "First Last" format
        parts = name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[-1].lower()
            # Create partial match key from first initial + last name
            if first_name:
                keys.append(f"_{first_name[0].lower()}_{last_name}")

    return keys


class PlayerCrossover:
    """
    Track players across NCAA baseball, MiLB, and MLB.

    Uses Baseball Reference IDs as primary key where available,
    with name matching as fallback. Also supports partial name matching
    (first initial + last name) to link players across data sources with
    different name formats.
    """

    def __init__(self):
        self.players: Dict[str, PlayerRecord] = {}  # key -> PlayerRecord
        self.bref_id_map: Dict[str, str] = {}  # bref_id -> key
        self.mlb_api_id_map: Dict[int, str] = {}  # mlb_api_id -> key
        self.name_map: Dict[str, List[str]] = defaultdict(list)  # normalized_name -> [keys]
        self.partial_name_map: Dict[str, List[str]] = defaultdict(list)  # _initial_last -> [keys]

    def _get_or_create_player(
        self,
        name: str,
        bref_id: Optional[str] = None,
        mlb_api_id: Optional[int] = None,
        mlb_bref_id: Optional[str] = None,
    ) -> str:
        """
        Get existing player key or create new player record.

        Uses the Chadwick Bureau Register to link IDs across systems.

        Args:
            name: Player name
            bref_id: Baseball Reference register ID (e.g., "fielde001pri")
            mlb_api_id: MLB Stats API ID (e.g., 425902)
            mlb_bref_id: Baseball Reference MLB ID (e.g., "fieldpr01")

        Returns:
            Player key
        """
        # Use ID mapper to find linked IDs
        mapper = get_id_mapper()
        if mapper:
            # If we have MLBAM ID, look up linked BBRef IDs
            if mlb_api_id and not bref_id:
                bref_id = mapper.get_register_from_mlbam(mlb_api_id)
            if mlb_api_id and not mlb_bref_id:
                mlb_bref_id = mapper.get_mlb_from_mlbam(mlb_api_id)

            # If we have register ID, look up linked MLBAM and MLB BBRef IDs
            if bref_id and not mlb_api_id:
                mlb_api_id = mapper.get_mlbam_from_register(bref_id)
            if bref_id and not mlb_bref_id:
                mlb_bref_id = mapper.get_mlb_id(bref_id)

            # If we have MLB BBRef ID, look up linked register ID
            if mlb_bref_id and not bref_id:
                bref_id = mapper.get_register_id(mlb_bref_id)

        # Try to find by bref_id first (most reliable - links NCAA and MiLB)
        if bref_id and bref_id in self.bref_id_map:
            key = self.bref_id_map[bref_id]
            player = self.players[key]
            # Update other IDs if we have them
            if mlb_api_id and not player.mlb_api_id:
                player.mlb_api_id = mlb_api_id
                self.mlb_api_id_map[mlb_api_id] = key
            if mlb_bref_id and not player.mlb_bref_id:
                player.mlb_bref_id = mlb_bref_id
            return key

        # Try by MLB BBRef ID (links MLB Game Tracker data)
        if mlb_bref_id and mlb_bref_id in self.bref_id_map:
            key = self.bref_id_map[mlb_bref_id]
            player = self.players[key]
            if bref_id and not player.bref_id:
                player.bref_id = bref_id
                self.bref_id_map[bref_id] = key
            if mlb_api_id and not player.mlb_api_id:
                player.mlb_api_id = mlb_api_id
                self.mlb_api_id_map[mlb_api_id] = key
            return key

        # Try by MLB API ID
        if mlb_api_id and mlb_api_id in self.mlb_api_id_map:
            key = self.mlb_api_id_map[mlb_api_id]
            player = self.players[key]
            if bref_id and not player.bref_id:
                player.bref_id = bref_id
                self.bref_id_map[bref_id] = key
            if mlb_bref_id and not player.mlb_bref_id:
                player.mlb_bref_id = mlb_bref_id
            return key

        # Try to find by normalized name (fallback for cross-level matching)
        name_keys = get_name_match_keys(name)
        normalized = name_keys[0] if name_keys else ''

        if normalized in self.name_map and self.name_map[normalized]:
            # Found a name match - use the existing player
            key = self.name_map[normalized][0]
            player = self.players[key]
            # Update IDs if we have new ones
            if bref_id and not player.bref_id:
                player.bref_id = bref_id
                self.bref_id_map[bref_id] = key
            if mlb_api_id and not player.mlb_api_id:
                player.mlb_api_id = mlb_api_id
                self.mlb_api_id_map[mlb_api_id] = key
            if mlb_bref_id and not player.mlb_bref_id:
                player.mlb_bref_id = mlb_bref_id
            return key

        # Try partial name match (first initial + last name)
        # This handles cases like "Johnson, K" matching "Kyle Johnson"
        for name_key in name_keys:
            if name_key.startswith('_') and name_key in self.partial_name_map:
                # Found a partial match - use the existing player
                key = self.partial_name_map[name_key][0]
                player = self.players[key]
                # Update IDs if we have new ones
                if bref_id and not player.bref_id:
                    player.bref_id = bref_id
                    self.bref_id_map[bref_id] = key
                if mlb_api_id and not player.mlb_api_id:
                    player.mlb_api_id = mlb_api_id
                    self.mlb_api_id_map[mlb_api_id] = key
                if mlb_bref_id and not player.mlb_bref_id:
                    player.mlb_bref_id = mlb_bref_id
                return key

        # Create new player
        key = bref_id or mlb_bref_id or (f"mlb_{mlb_api_id}" if mlb_api_id else f"name_{normalized}")

        # Check if we already have this player by key
        if key in self.players:
            return key

        # Create new record
        self.players[key] = PlayerRecord(
            name=name,
            bref_id=bref_id,
            mlb_bref_id=mlb_bref_id,
            mlb_api_id=mlb_api_id,
        )

        # Index by various IDs
        if bref_id:
            self.bref_id_map[bref_id] = key
        if mlb_bref_id:
            self.bref_id_map[mlb_bref_id] = key
        if mlb_api_id:
            self.mlb_api_id_map[mlb_api_id] = key
        if normalized:
            self.name_map[normalized].append(key)

        # Index by partial name keys for future matching
        for name_key in name_keys:
            if name_key.startswith('_'):
                self.partial_name_map[name_key].append(key)

        return key

    def load_ncaa_data(self, games: List[Dict[str, Any]]) -> None:
        """
        Load NCAA baseball player appearances.

        Args:
            games: List of NCAA game data dicts (from cache)
        """
        for game in games:
            metadata = game.get('metadata', {})
            date = metadata.get('date', '')
            date_yyyymmdd = metadata.get('date_yyyymmdd', '')

            box_score = game.get('box_score', {})

            for side in ['away', 'home']:
                team = metadata.get(f'{side}_team', '')

                # Process batters
                for player in box_score.get(f'{side}_batting', []):
                    name = player.get('full_name') or player.get('name', '')
                    bref_id = player.get('bref_id')

                    if not name:
                        continue

                    key = self._get_or_create_player(name, bref_id=bref_id)
                    self.players[key].ncaa_appearances.append({
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'opponent': metadata.get('home_team' if side == 'away' else 'away_team', ''),
                        'level': 'NCAA',
                        'type': 'batting',
                        'stats': {
                            'AB': player.get('at_bats', player.get('ab', 0)),
                            'R': player.get('runs', player.get('r', 0)),
                            'H': player.get('hits', player.get('h', 0)),
                            'RBI': player.get('rbi', 0),
                            'BB': player.get('walks', player.get('bb', 0)),
                            'K': player.get('strikeouts', player.get('k', 0)),
                        },
                    })
                    self.players[key].teams.add(team)

                # Process pitchers
                for player in box_score.get(f'{side}_pitching', []):
                    name = player.get('full_name') or player.get('name', '')
                    bref_id = player.get('bref_id')

                    if not name:
                        continue

                    key = self._get_or_create_player(name, bref_id=bref_id)

                    # Check if already added as batter for this game
                    existing = [a for a in self.players[key].ncaa_appearances
                               if a.get('date_yyyymmdd') == date_yyyymmdd and a.get('team') == team]

                    self.players[key].ncaa_appearances.append({
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'opponent': metadata.get('home_team' if side == 'away' else 'away_team', ''),
                        'level': 'NCAA',
                        'type': 'pitching',
                        'stats': {
                            'IP': player.get('innings_pitched', player.get('ip', 0)),
                            'H': player.get('hits', player.get('h', 0)),
                            'R': player.get('runs', player.get('r', 0)),
                            'ER': player.get('earned_runs', player.get('er', 0)),
                            'BB': player.get('walks', player.get('bb', 0)),
                            'K': player.get('strikeouts', player.get('k', 0)),
                        },
                    })
                    self.players[key].teams.add(team)

    def load_milb_data(self, games: List[Dict[str, Any]]) -> None:
        """
        Load MiLB player appearances.

        Args:
            games: List of MiLB game data dicts
        """
        for game in games:
            metadata = game.get('metadata', {})
            date = metadata.get('date', '')
            date_yyyymmdd = metadata.get('date_yyyymmdd', '')

            box_score = game.get('box_score', {})

            for side in ['away', 'home']:
                team = metadata.get(f'{side}_team', '')
                parent_org = metadata.get('parent_orgs', {}).get(side, '')

                # Process batters
                for player in box_score.get(f'{side}_batting', []):
                    name = player.get('name', '')
                    mlb_api_id = player.get('player_id')

                    if not name:
                        continue

                    key = self._get_or_create_player(name, mlb_api_id=mlb_api_id)
                    self.players[key].milb_appearances.append({
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'parent_org': parent_org,
                        'opponent': metadata.get('home_team' if side == 'away' else 'away_team', ''),
                        'level': 'MiLB',
                        'type': 'batting',
                        'stats': {
                            'AB': player.get('ab', 0),
                            'R': player.get('r', 0),
                            'H': player.get('h', 0),
                            'RBI': player.get('rbi', 0),
                            'BB': player.get('bb', 0),
                            'K': player.get('k', 0),
                        },
                    })
                    self.players[key].teams.add(team)
                    if mlb_api_id and not self.players[key].mlb_api_id:
                        self.players[key].mlb_api_id = mlb_api_id

                # Process pitchers
                for player in box_score.get(f'{side}_pitching', []):
                    name = player.get('name', '')
                    mlb_api_id = player.get('player_id')

                    if not name:
                        continue

                    key = self._get_or_create_player(name, mlb_api_id=mlb_api_id)
                    self.players[key].milb_appearances.append({
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'parent_org': parent_org,
                        'opponent': metadata.get('home_team' if side == 'away' else 'away_team', ''),
                        'level': 'MiLB',
                        'type': 'pitching',
                        'stats': {
                            'IP': player.get('ip', '0.0'),
                            'H': player.get('h', 0),
                            'R': player.get('r', 0),
                            'ER': player.get('er', 0),
                            'BB': player.get('bb', 0),
                            'K': player.get('k', 0),
                        },
                    })
                    self.players[key].teams.add(team)

    def load_partner_data(self, games: List[Dict[str, Any]]) -> None:
        """
        Load Partner League player appearances.

        Partner leagues use bref_id for player identification (same format as NCAA).

        Args:
            games: List of Partner league game data dicts
        """
        for game in games:
            metadata = game.get('metadata', {})
            date = metadata.get('date', '')
            date_yyyymmdd = metadata.get('date_yyyymmdd', '')
            league = metadata.get('league', {})
            league_name = league.get('home', 'Partner') if isinstance(league, dict) else league

            box_score = game.get('box_score', {})

            for side in ['away', 'home']:
                team = metadata.get(f'{side}_team', '')

                # Process batters
                for player in box_score.get(f'{side}_batting', []):
                    name = player.get('name', '')
                    # Use bref_id if available, otherwise fall back to player_id
                    bref_id = player.get('bref_id') or player.get('player_id')

                    if not name:
                        continue

                    key = self._get_or_create_player(name, bref_id=bref_id)
                    self.players[key].milb_appearances.append({
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'parent_org': '',
                        'opponent': metadata.get('home_team' if side == 'away' else 'away_team', ''),
                        'level': 'Partner',
                        'league': league_name,
                        'type': 'batting',
                        'stats': {
                            'AB': player.get('ab', 0),
                            'R': player.get('r', 0),
                            'H': player.get('h', 0),
                            'RBI': player.get('rbi', 0),
                            'BB': player.get('bb', 0),
                            'K': player.get('k', 0),
                        },
                    })
                    self.players[key].teams.add(team)
                    if bref_id and not self.players[key].bref_id:
                        self.players[key].bref_id = bref_id

                # Process pitchers
                for player in box_score.get(f'{side}_pitching', []):
                    name = player.get('name', '')
                    bref_id = player.get('bref_id') or player.get('player_id')

                    if not name:
                        continue

                    key = self._get_or_create_player(name, bref_id=bref_id)
                    self.players[key].milb_appearances.append({
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'parent_org': '',
                        'opponent': metadata.get('home_team' if side == 'away' else 'away_team', ''),
                        'level': 'Partner',
                        'league': league_name,
                        'type': 'pitching',
                        'stats': {
                            'IP': player.get('ip', '0.0'),
                            'H': player.get('h', 0),
                            'R': player.get('r', 0),
                            'ER': player.get('er', 0),
                            'BB': player.get('bb', 0),
                            'K': player.get('k', 0),
                        },
                    })
                    self.players[key].teams.add(team)

    def load_mlb_data(self, mlb_reader) -> None:
        """
        Load MLB player appearances from MLB Game Tracker.

        Args:
            mlb_reader: MLBDataReader instance (already loaded)
        """
        for player_id, appearances in mlb_reader.player_appearances.items():
            # Get or create player using MLB BBRef ID (e.g., "tayloch03")
            # The ID mapper will link this to the register ID if available
            if appearances:
                name = appearances[0].get('name', '')
                key = self._get_or_create_player(name, mlb_bref_id=player_id)

                for appearance in appearances:
                    self.players[key].mlb_appearances.append({
                        'date_yyyymmdd': appearance.get('date', ''),
                        'team': appearance.get('team', ''),
                        'opponent': appearance.get('opponent', ''),
                        'venue': appearance.get('venue', ''),
                        'level': 'MLB',
                        'type': appearance.get('type', 'batting'),
                        'stats': appearance.get('stats', {}),
                    })
                    self.players[key].teams.add(appearance.get('team', ''))

    def find_crossover_players(self) -> List[PlayerRecord]:
        """
        Find all players seen at multiple levels.

        Returns:
            List of PlayerRecord for crossover players
        """
        return [p for p in self.players.values() if p.is_crossover()]

    def get_player_journey(self, key: str) -> Optional[PlayerRecord]:
        """
        Get a player's journey across all levels.

        Args:
            key: Player key (bref_id, mlb_api_id, or name-based key)

        Returns:
            PlayerRecord or None if not found
        """
        return self.players.get(key)

    def search_by_name(self, name: str) -> List[PlayerRecord]:
        """
        Search for players by name.

        Args:
            name: Player name (partial match supported)

        Returns:
            List of matching PlayerRecords
        """
        name_lower = name.lower()
        matches = []

        for player in self.players.values():
            if name_lower in player.name.lower():
                matches.append(player)

        return matches

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_players = len(self.players)
        ncaa_only = sum(1 for p in self.players.values()
                       if p.ncaa_appearances and not p.milb_appearances and not p.mlb_appearances)
        milb_only = sum(1 for p in self.players.values()
                       if p.milb_appearances and not p.ncaa_appearances and not p.mlb_appearances)
        mlb_only = sum(1 for p in self.players.values()
                      if p.mlb_appearances and not p.ncaa_appearances and not p.milb_appearances)
        crossover = sum(1 for p in self.players.values() if p.is_crossover())

        return {
            'total_players': total_players,
            'ncaa_only': ncaa_only,
            'milb_only': milb_only,
            'mlb_only': mlb_only,
            'crossover_players': crossover,
            'ncaa_to_milb': sum(1 for p in self.players.values()
                               if p.ncaa_appearances and p.milb_appearances),
            'milb_to_mlb': sum(1 for p in self.players.values()
                             if p.milb_appearances and p.mlb_appearances),
            'ncaa_to_mlb': sum(1 for p in self.players.values()
                             if p.ncaa_appearances and p.mlb_appearances),
            'all_levels': sum(1 for p in self.players.values()
                            if p.ncaa_appearances and p.milb_appearances and p.mlb_appearances),
        }

    def to_dataframe_data(self) -> List[Dict[str, Any]]:
        """
        Convert crossover players to list of dicts for DataFrame creation.

        Returns:
            List of dicts suitable for pandas DataFrame
        """
        data = []

        for key, player in self.players.items():
            if not player.is_crossover():
                continue

            ncaa_teams = set()
            milb_teams = set()
            mlb_teams = set()

            for a in player.ncaa_appearances:
                ncaa_teams.add(a.get('team', ''))
            for a in player.milb_appearances:
                milb_teams.add(a.get('team', ''))
            for a in player.mlb_appearances:
                mlb_teams.add(a.get('team', ''))

            data.append({
                'Name': player.name,
                'BBRef ID': player.bref_id or '',
                'MLB API ID': player.mlb_api_id or '',
                'Levels': ', '.join(player.levels_seen()),
                'NCAA Games': len(player.ncaa_appearances),
                'MiLB Games': len(player.milb_appearances),
                'MLB Games': len(player.mlb_appearances),
                'Total Games': player.total_appearances(),
                'NCAA Teams': ', '.join(sorted(ncaa_teams - {''})),
                'MiLB Teams': ', '.join(sorted(milb_teams - {''})),
                'MLB Teams': ', '.join(sorted(mlb_teams - {''})),
            })

        # Sort by total appearances descending
        data.sort(key=lambda x: x['Total Games'], reverse=True)
        return data


if __name__ == '__main__':
    # Test the crossover tracker
    from mlb_reader import MLBDataReader

    print("Testing Player Crossover Tracker\n")

    # Load MLB data
    mlb_reader = MLBDataReader()
    mlb_reader.load_cache()

    # Create crossover tracker
    crossover = PlayerCrossover()
    crossover.load_mlb_data(mlb_reader)

    summary = crossover.get_summary()
    print(f"Summary:")
    print(f"  Total players: {summary['total_players']}")
    print(f"  MLB only: {summary['mlb_only']}")

    # Search for a sample player
    print("\nSearching for 'Carroll':")
    matches = crossover.search_by_name('Carroll')
    for player in matches[:5]:
        print(f"  {player.name}: {player.levels_seen()}, {player.total_appearances()} appearances")
