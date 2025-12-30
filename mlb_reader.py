"""
Read-only interface to MLB Game Tracker cache.

This module provides functions to read MLB game data and player appearances
from the MLB Game Tracker's cache without modifying it.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict


class MLBDataReader:
    """
    Read-only interface to MLB Game Tracker cache.

    Loads game data from the cache directory and provides methods to
    query player appearances for crossover tracking.
    """

    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize the reader.

        Args:
            cache_path: Path to MLB Game Tracker cache directory.
                       Defaults to ~/MLB Game Tracker/cache/
        """
        if cache_path is None:
            cache_path = Path.home() / "MLB Game Tracker" / "cache"

        self.cache_path = Path(cache_path)
        self.games: List[Dict[str, Any]] = []
        self.player_appearances: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._loaded = False

    def load_cache(self) -> None:
        """Load all games from the MLB cache directory."""
        if self._loaded:
            return

        if not self.cache_path.exists():
            print(f"MLB cache not found at {self.cache_path}")
            return

        # Skip non-game cache files
        skip_files = {'nba_lookup_cache.json', 'nba_api_cache.json', 'career_firsts'}

        json_files = list(self.cache_path.glob("*.json"))
        print(f"Loading {len(json_files)} MLB games from cache...")

        for json_file in json_files:
            if json_file.name in skip_files:
                continue
            if 'career_firsts' in json_file.name:
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    game = json.load(f)

                # Validate it's a game file
                if 'basic_info' not in game or 'batting' not in game:
                    continue

                self.games.append(game)
                self._index_player_appearances(game)

            except (json.JSONDecodeError, IOError) as e:
                print(f"  Warning: Could not load {json_file.name}: {e}")

        self._loaded = True
        print(f"  Loaded {len(self.games)} MLB games")

    def _index_player_appearances(self, game: Dict[str, Any]) -> None:
        """Index player appearances from a game for fast lookup."""
        basic_info = game.get('basic_info', {})
        game_date = basic_info.get('date_yyyymmdd', '')
        venue = basic_info.get('venue', '')

        # Index batters
        for side in ['away', 'home']:
            team = basic_info.get(f'{side}_team', '')
            opponent = basic_info.get('home_team' if side == 'away' else 'away_team', '')

            for player in game.get('batting', {}).get(side, []):
                player_id = player.get('player_id')
                if player_id:
                    self.player_appearances[player_id].append({
                        'date': game_date,
                        'team': team,
                        'opponent': opponent,
                        'venue': venue,
                        'side': side,
                        'type': 'batting',
                        'stats': {
                            'AB': player.get('AB', 0),
                            'R': player.get('R', 0),
                            'H': player.get('H', 0),
                            'RBI': player.get('RBI', 0),
                            'BB': player.get('BB', 0),
                            'SO': player.get('SO', 0),
                        },
                        'name': player.get('name', ''),
                        'position': player.get('position', ''),
                        'level': 'MLB',
                    })

        # Index pitchers
        for side in ['away', 'home']:
            team = basic_info.get(f'{side}_team', '')
            opponent = basic_info.get('home_team' if side == 'away' else 'away_team', '')

            for player in game.get('pitching', {}).get(side, []):
                player_id = player.get('player_id')
                if player_id:
                    # Check if already indexed as batter for this game
                    existing = [a for a in self.player_appearances[player_id]
                               if a['date'] == game_date and a['type'] == 'batting']

                    self.player_appearances[player_id].append({
                        'date': game_date,
                        'team': team,
                        'opponent': opponent,
                        'venue': venue,
                        'side': side,
                        'type': 'pitching',
                        'stats': {
                            'IP': player.get('IP', 0),
                            'H': player.get('H', 0),
                            'R': player.get('R', 0),
                            'ER': player.get('ER', 0),
                            'BB': player.get('BB', 0),
                            'K': player.get('SO', 0),
                        },
                        'name': player.get('name', ''),
                        'level': 'MLB',
                    })

    def get_player_appearances(self, player_id: str) -> List[Dict[str, Any]]:
        """
        Get all game appearances for a player.

        Args:
            player_id: Baseball Reference player ID (e.g., 'carroco02')

        Returns:
            List of appearance records
        """
        if not self._loaded:
            self.load_cache()
        return self.player_appearances.get(player_id, [])

    def get_all_player_ids(self) -> Set[str]:
        """
        Get set of all player IDs in the MLB cache.

        Returns:
            Set of Baseball Reference player IDs
        """
        if not self._loaded:
            self.load_cache()
        return set(self.player_appearances.keys())

    def get_player_names(self) -> Dict[str, str]:
        """
        Get mapping of player IDs to names.

        Returns:
            Dict mapping player_id -> full name
        """
        if not self._loaded:
            self.load_cache()

        names = {}
        for player_id, appearances in self.player_appearances.items():
            if appearances:
                names[player_id] = appearances[0].get('name', '')
        return names

    def get_games_by_date(self, date_yyyymmdd: str) -> List[Dict[str, Any]]:
        """
        Get all games from a specific date.

        Args:
            date_yyyymmdd: Date in YYYYMMDD format

        Returns:
            List of game data dicts
        """
        if not self._loaded:
            self.load_cache()

        return [g for g in self.games
                if g.get('basic_info', {}).get('date_yyyymmdd') == date_yyyymmdd]

    def get_games_by_team(self, team_name: str) -> List[Dict[str, Any]]:
        """
        Get all games involving a team.

        Args:
            team_name: Team name (partial match supported)

        Returns:
            List of game data dicts
        """
        if not self._loaded:
            self.load_cache()

        team_lower = team_name.lower()
        return [g for g in self.games
                if team_lower in g.get('basic_info', {}).get('away_team', '').lower()
                or team_lower in g.get('basic_info', {}).get('home_team', '').lower()]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the MLB data.

        Returns:
            Dict with summary stats
        """
        if not self._loaded:
            self.load_cache()

        return {
            'total_games': len(self.games),
            'total_players': len(self.player_appearances),
            'date_range': self._get_date_range(),
        }

    def _get_date_range(self) -> Dict[str, str]:
        """Get earliest and latest game dates."""
        dates = [g.get('basic_info', {}).get('date_yyyymmdd', '')
                for g in self.games if g.get('basic_info', {}).get('date_yyyymmdd')]

        if not dates:
            return {'earliest': '', 'latest': ''}

        return {
            'earliest': min(dates),
            'latest': max(dates),
        }


if __name__ == '__main__':
    # Test the reader
    reader = MLBDataReader()
    reader.load_cache()

    summary = reader.get_summary()
    print(f"\nMLB Game Tracker Summary:")
    print(f"  Total games: {summary['total_games']}")
    print(f"  Total players: {summary['total_players']}")
    print(f"  Date range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")

    # Test player lookup
    player_ids = list(reader.get_all_player_ids())[:5]
    print(f"\nSample players:")
    for pid in player_ids:
        appearances = reader.get_player_appearances(pid)
        if appearances:
            name = appearances[0].get('name', 'Unknown')
            print(f"  {pid}: {name} ({len(appearances)} appearances)")
