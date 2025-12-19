"""
Game log processor for baseball.
"""

from typing import Dict, List, Any
import pandas as pd

from ..utils.helpers import safe_int, normalize_team_name, parse_date_for_sort


class GameLogProcessor:
    """Process and compile game log."""

    def __init__(self, games: List[Dict[str, Any]]):
        self.games = games

    def create_game_log(self) -> pd.DataFrame:
        """
        Create game log DataFrame.

        Returns:
            DataFrame with one row per game
        """
        rows = []

        for game in self.games:
            meta = game.get('metadata', {})
            box_score = game.get('box_score', {})

            # Normalize team names
            away_team = normalize_team_name(meta.get('away_team', ''))
            home_team = normalize_team_name(meta.get('home_team', ''))
            away_score = safe_int(meta.get('away_team_score', 0))
            home_score = safe_int(meta.get('home_team_score', 0))

            # Calculate hits
            away_hits = sum(
                safe_int(p.get('hits', p.get('h', 0)))
                for p in box_score.get('away_batting', [])
                if p.get('name', '').lower() != 'totals'
            )
            home_hits = sum(
                safe_int(p.get('hits', p.get('h', 0)))
                for p in box_score.get('home_batting', [])
                if p.get('name', '').lower() != 'totals'
            )

            # Get line score
            line_score = box_score.get('line_score', {})
            innings = max(
                len(line_score.get('away_innings', [])),
                len(line_score.get('home_innings', [])),
                9
            )

            date_str = meta.get('date', '')
            rows.append({
                'Date': date_str,
                'DateSort': parse_date_for_sort(date_str),
                'Away': away_team,
                'Home': home_team,
                'Away Score': away_score,
                'Home Score': home_score,
                'Away Hits': away_hits,
                'Home Hits': home_hits,
                'Innings': innings,
                'Venue': meta.get('venue', ''),
                'Attendance': meta.get('attendance', ''),
            })

        df = pd.DataFrame(rows)
        if not df.empty and 'DateSort' in df.columns:
            df = df.sort_values('DateSort', ascending=False)
        return df
