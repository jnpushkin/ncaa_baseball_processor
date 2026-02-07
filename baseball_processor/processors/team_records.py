"""
Team records processor for baseball.
"""

from typing import Dict, List, Any
import pandas as pd
from collections import defaultdict

from ..utils.helpers import safe_int, normalize_team_name
from ..utils.constants import get_conference, resolve_level_and_league


class TeamRecordsProcessor:
    """Process and compile team records across games."""

    def __init__(self, games: List[Dict[str, Any]]):
        self.games = games

    def process_team_records(self) -> Dict[str, pd.DataFrame]:
        """
        Process team records from all games.

        Returns:
            Dictionary with team_records, venue_records, head_to_head
        """
        team_stats = defaultdict(lambda: {
            'wins': 0, 'losses': 0,
            'runs_for': 0, 'runs_against': 0,
            'home_wins': 0, 'home_losses': 0,
            'away_wins': 0, 'away_losses': 0,
        })

        venue_stats = defaultdict(lambda: {'games': 0, 'wins': 0, 'losses': 0})
        head_to_head = defaultdict(lambda: {'wins': 0, 'losses': 0, 'runs_for': 0, 'runs_against': 0})

        # Track which years each team appears in (for conference lookup)
        team_years = defaultdict(list)
        # Track level/league per team
        team_level_league = {}

        for game in self.games:
            meta = game.get('metadata', {})

            # Normalize team names
            away_team = normalize_team_name(meta.get('away_team', ''))
            home_team = normalize_team_name(meta.get('home_team', ''))
            away_score = safe_int(meta.get('away_team_score', 0))
            home_score = safe_int(meta.get('home_team_score', 0))
            venue = meta.get('venue', '')

            # Extract year from game date for conference lookup
            game_date = meta.get('date', '')
            game_year = None
            if game_date:
                try:
                    # Parse year from date string (e.g., "6/16/2025" or "2025-06-16")
                    if '/' in game_date:
                        parts = game_date.split('/')
                        game_year = int(parts[-1]) if len(parts[-1]) == 4 else int(parts[0])
                    elif '-' in game_date:
                        game_year = int(game_date.split('-')[0])
                except (ValueError, IndexError):
                    pass

            if away_team and game_year:
                team_years[away_team].append(game_year)
            if home_team and game_year:
                team_years[home_team].append(game_year)

            # Resolve level/league for each team
            is_milb = game.get('format') == 'milb_api'
            is_partner = meta.get('source') == 'partner'
            if is_milb or is_partner:
                if home_team and home_team not in team_level_league:
                    level, league = resolve_level_and_league(meta, home_team)
                    team_level_league[home_team] = (level, league)
                if away_team and away_team not in team_level_league:
                    level, league = resolve_level_and_league(meta, away_team)
                    team_level_league[away_team] = (level, league)
            else:
                if home_team and home_team not in team_level_league:
                    team_level_league[home_team] = ('NCAA', '')
                if away_team and away_team not in team_level_league:
                    team_level_league[away_team] = ('NCAA', '')

            if not away_team or not home_team:
                continue

            # Determine winner
            if away_score > home_score:
                team_stats[away_team]['wins'] += 1
                team_stats[away_team]['away_wins'] += 1
                team_stats[home_team]['losses'] += 1
                team_stats[home_team]['home_losses'] += 1

                venue_stats[venue]['wins'] += 1  # For away team at this venue
            else:
                team_stats[home_team]['wins'] += 1
                team_stats[home_team]['home_wins'] += 1
                team_stats[away_team]['losses'] += 1
                team_stats[away_team]['away_losses'] += 1

                venue_stats[venue]['losses'] += 1

            venue_stats[venue]['games'] += 1

            # Run totals
            team_stats[away_team]['runs_for'] += away_score
            team_stats[away_team]['runs_against'] += home_score
            team_stats[home_team]['runs_for'] += home_score
            team_stats[home_team]['runs_against'] += away_score

            # Head to head
            h2h_key = tuple(sorted([away_team, home_team]))
            if away_score > home_score:
                head_to_head[h2h_key + (away_team,)]['wins'] += 1
                head_to_head[h2h_key + (home_team,)]['losses'] += 1
            else:
                head_to_head[h2h_key + (home_team,)]['wins'] += 1
                head_to_head[h2h_key + (away_team,)]['losses'] += 1

        # Create team records DataFrame
        team_rows = []
        for team, stats in team_stats.items():
            wins = stats['wins']
            losses = stats['losses']
            total = wins + losses
            win_pct = wins / total if total > 0 else 0

            # Use the most recent year for conference lookup
            years = team_years.get(team, [])
            most_recent_year = max(years) if years else None

            # Format win percentage (1.000 for undefeated, .XXX otherwise)
            if win_pct == 1.0:
                win_pct_str = "1.000"
            elif win_pct == 0.0:
                win_pct_str = ".000"
            else:
                win_pct_str = f".{int(win_pct * 1000):03d}"

            level, league = team_level_league.get(team, ('NCAA', ''))
            if level == 'NCAA':
                league = get_conference(team, most_recent_year)

            team_rows.append({
                'Team': team,
                'Level': level,
                'League': league,
                'Conference': league if level == 'NCAA' else level,
                'W': wins,
                'L': losses,
                'Win%': win_pct_str,
                'RS': stats['runs_for'],
                'RA': stats['runs_against'],
                'Diff': stats['runs_for'] - stats['runs_against'],
                'Home': f"{stats['home_wins']}-{stats['home_losses']}",
                'Away': f"{stats['away_wins']}-{stats['away_losses']}",
            })

        team_df = pd.DataFrame(team_rows)
        if not team_df.empty:
            team_df = team_df.sort_values(['W', 'Diff'], ascending=[False, False])

        # Create venue records DataFrame
        venue_rows = []
        for venue, stats in venue_stats.items():
            if venue:
                venue_rows.append({
                    'Venue': venue,
                    'Games': stats['games'],
                    'Wins': stats['wins'],
                    'Losses': stats['losses'],
                })

        venue_df = pd.DataFrame(venue_rows)
        if not venue_df.empty:
            venue_df = venue_df.sort_values('Games', ascending=False)

        return {
            'team_records': team_df,
            'venue_records': venue_df,
        }
