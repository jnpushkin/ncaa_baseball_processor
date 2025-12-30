"""
Excel workbook generator for baseball statistics.

Supports NCAA baseball, MiLB, and player crossover tracking.
"""

import os
from typing import Dict, List, Any, Optional
import pandas as pd

from ..processors.player_stats import PlayerStatsProcessor
from ..processors.milestones import MilestonesProcessor
from ..processors.team_records import TeamRecordsProcessor
from ..processors.game_log import GameLogProcessor


def create_milb_game_log(milb_games: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create game log DataFrame for MiLB and Partner League games."""
    if not milb_games:
        return pd.DataFrame()

    rows = []
    for game in milb_games:
        meta = game.get('metadata', {})
        source = meta.get('source', 'milb')
        rows.append({
            'Date': meta.get('date', ''),
            'date_yyyymmdd': meta.get('date_yyyymmdd', ''),
            'Away Team': meta.get('away_team', ''),
            'Home Team': meta.get('home_team', ''),
            'Score': f"{meta.get('away_team_score', 0)}-{meta.get('home_team_score', 0)}",
            'Venue': meta.get('venue', ''),
            'Away Parent': meta.get('parent_orgs', {}).get('away', ''),
            'Home Parent': meta.get('parent_orgs', {}).get('home', ''),
            'Game PK': meta.get('game_pk', ''),
            'Source': source,
            'League': meta.get('league', {}).get('home', '') or meta.get('league', {}).get('away', ''),
        })

    df = pd.DataFrame(rows)
    if not df.empty and 'date_yyyymmdd' in df.columns:
        df = df.sort_values('date_yyyymmdd', ascending=False)
    return df


def create_milb_batters(milb_games: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create batting stats DataFrame for MiLB games."""
    if not milb_games:
        return pd.DataFrame()

    from collections import defaultdict
    batter_totals = defaultdict(lambda: defaultdict(int))
    batter_info = {}
    batter_teams = defaultdict(set)  # Track teams for each player

    for game in milb_games:
        for side in ['away', 'home']:
            team = game.get('metadata', {}).get(f'{side}_team', '')
            parent_org = game.get('metadata', {}).get('parent_orgs', {}).get(side, '')
            for player in game.get('box_score', {}).get(f'{side}_batting', []):
                player_id = player.get('player_id')
                name = player.get('name', '')
                if not name:
                    continue

                key = player_id or name
                batter_info[key] = {'name': name, 'player_id': player_id}
                if team:
                    batter_teams[key].add(team)

                batter_totals[key]['games'] += 1
                for stat in ['ab', 'r', 'h', 'rbi', 'bb', 'k', 'hr', 'doubles', 'triples', 'sb']:
                    batter_totals[key][stat] += player.get(stat, 0)

    rows = []
    for key, totals in batter_totals.items():
        info = batter_info.get(key, {})
        teams = batter_teams.get(key, set())
        ab = totals['ab']
        h = totals['h']
        avg = h / ab if ab > 0 else 0

        rows.append({
            'Name': info.get('name', ''),
            'Team': ', '.join(sorted(teams)) if teams else '',
            'Player ID': info.get('player_id', ''),
            'G': totals['games'],
            'AB': ab,
            'R': totals['r'],
            'H': h,
            'RBI': totals['rbi'],
            'BB': totals['bb'],
            'K': totals['k'],
            'HR': totals['hr'],
            '2B': totals['doubles'],
            '3B': totals['triples'],
            'SB': totals['sb'],
            'AVG': f"{avg:.3f}",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values('AB', ascending=False)
    return df


def create_milb_pitchers(milb_games: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create pitching stats DataFrame for MiLB games."""
    if not milb_games:
        return pd.DataFrame()

    from collections import defaultdict
    pitcher_totals = defaultdict(lambda: defaultdict(float))
    pitcher_info = {}
    pitcher_teams = defaultdict(set)  # Track teams for each player

    for game in milb_games:
        for side in ['away', 'home']:
            team = game.get('metadata', {}).get(f'{side}_team', '')
            for player in game.get('box_score', {}).get(f'{side}_pitching', []):
                player_id = player.get('player_id')
                name = player.get('name', '')
                if not name:
                    continue

                key = player_id or name
                pitcher_info[key] = {'name': name, 'player_id': player_id}
                if team:
                    pitcher_teams[key].add(team)

                pitcher_totals[key]['games'] += 1

                # Handle IP as string (e.g., "5.2" = 5 2/3)
                ip_str = str(player.get('ip', '0'))
                try:
                    ip = float(ip_str)
                except ValueError:
                    ip = 0
                pitcher_totals[key]['ip'] += ip

                for stat in ['h', 'r', 'er', 'bb', 'k', 'hr', 'np']:
                    pitcher_totals[key][stat] += player.get(stat, 0)

                if player.get('win'):
                    pitcher_totals[key]['w'] += 1
                if player.get('loss'):
                    pitcher_totals[key]['l'] += 1
                if player.get('save'):
                    pitcher_totals[key]['sv'] += 1

    rows = []
    for key, totals in pitcher_totals.items():
        info = pitcher_info.get(key, {})
        teams = pitcher_teams.get(key, set())
        ip = totals['ip']
        er = totals['er']
        era = (er * 9 / ip) if ip > 0 else 0

        rows.append({
            'Name': info.get('name', ''),
            'Team': ', '.join(sorted(teams)) if teams else '',
            'Player ID': info.get('player_id', ''),
            'G': int(totals['games']),
            'W': int(totals['w']),
            'L': int(totals['l']),
            'SV': int(totals['sv']),
            'IP': f"{ip:.1f}",
            'H': int(totals['h']),
            'R': int(totals['r']),
            'ER': int(totals['er']),
            'BB': int(totals['bb']),
            'K': int(totals['k']),
            'HR': int(totals['hr']),
            'ERA': f"{era:.2f}",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values('IP', ascending=False, key=lambda x: pd.to_numeric(x, errors='coerce'))
    return df


def generate_excel_workbook(
    games: List[Dict[str, Any]],
    output_path: str,
    write_file: bool = True,
    milb_games: Optional[List[Dict[str, Any]]] = None,
    crossover_data: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate Excel workbook from parsed games data.

    Args:
        games: List of parsed game dictionaries (NCAA + MiLB combined)
        output_path: Path to save the Excel file
        write_file: Whether to actually write the file
        milb_games: Optional list of MiLB-only games (for separate sheets)
        crossover_data: Optional PlayerCrossover instance

    Returns:
        Dictionary containing all processed DataFrames
    """
    # Filter to NCAA games only for NCAA-specific processing
    # Exclude MiLB (format='milb_api') and Partner games (source='partner' in metadata)
    ncaa_games = [g for g in games if g.get('format') != 'milb_api' and g.get('metadata', {}).get('source') != 'partner']

    print(f"Processing {len(ncaa_games)} NCAA games...")

    processed_data = {}

    # Game Log (NCAA)
    if ncaa_games:
        print("  Creating NCAA game log...")
        game_log_processor = GameLogProcessor(ncaa_games)
        processed_data['game_log'] = game_log_processor.create_game_log()

        # Player Stats (NCAA)
        print("  Processing NCAA player statistics...")
        player_processor = PlayerStatsProcessor(ncaa_games)
        player_data = player_processor.process_all_stats()
        processed_data['batters'] = player_data['batters']
        processed_data['pitchers'] = player_data['pitchers']
        processed_data['batter_games'] = player_data['batter_games']
        processed_data['pitcher_games'] = player_data['pitcher_games']

        # Milestones (NCAA)
        print("  Processing NCAA milestones...")
        milestones_processor = MilestonesProcessor(ncaa_games)
        milestones_data = milestones_processor.process_all_milestones()
        processed_data['milestones'] = milestones_data

        # Team Records (NCAA)
        print("  Processing NCAA team records...")
        team_processor = TeamRecordsProcessor(ncaa_games)
        team_data = team_processor.process_team_records()
        processed_data['team_records'] = team_data['team_records']
        processed_data['venue_records'] = team_data['venue_records']
    else:
        processed_data['game_log'] = pd.DataFrame()
        processed_data['batters'] = pd.DataFrame()
        processed_data['pitchers'] = pd.DataFrame()
        processed_data['milestones'] = {}
        processed_data['team_records'] = pd.DataFrame()
        processed_data['venue_records'] = pd.DataFrame()

    # MiLB data
    if milb_games:
        print(f"  Processing {len(milb_games)} MiLB games...")
        processed_data['milb_game_log'] = create_milb_game_log(milb_games)
        processed_data['milb_batters'] = create_milb_batters(milb_games)
        processed_data['milb_pitchers'] = create_milb_pitchers(milb_games)
    else:
        processed_data['milb_game_log'] = pd.DataFrame()
        processed_data['milb_batters'] = pd.DataFrame()
        processed_data['milb_pitchers'] = pd.DataFrame()

    # Crossover data
    if crossover_data:
        print("  Processing crossover players...")
        crossover_list = crossover_data.to_dataframe_data()
        processed_data['crossover_players'] = pd.DataFrame(crossover_list)
    else:
        processed_data['crossover_players'] = pd.DataFrame()

    if not write_file:
        print("  Skipping Excel file generation")
        return processed_data

    # Write Excel file
    print(f"  Writing Excel file: {output_path}")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # NCAA Game Log
        if not processed_data['game_log'].empty:
            processed_data['game_log'].to_excel(writer, sheet_name='NCAA Game Log', index=False)

        # NCAA Batters
        if not processed_data['batters'].empty:
            processed_data['batters'].to_excel(writer, sheet_name='NCAA Batters', index=False)

        # NCAA Pitchers
        if not processed_data['pitchers'].empty:
            processed_data['pitchers'].to_excel(writer, sheet_name='NCAA Pitchers', index=False)

        # NCAA Team Records
        if not processed_data['team_records'].empty:
            processed_data['team_records'].to_excel(writer, sheet_name='NCAA Team Records', index=False)

        # MiLB Game Log
        if not processed_data['milb_game_log'].empty:
            processed_data['milb_game_log'].to_excel(writer, sheet_name='MiLB Game Log', index=False)

        # MiLB Batters
        if not processed_data['milb_batters'].empty:
            processed_data['milb_batters'].to_excel(writer, sheet_name='MiLB Batters', index=False)

        # MiLB Pitchers
        if not processed_data['milb_pitchers'].empty:
            processed_data['milb_pitchers'].to_excel(writer, sheet_name='MiLB Pitchers', index=False)

        # Crossover Players
        if not processed_data['crossover_players'].empty:
            processed_data['crossover_players'].to_excel(writer, sheet_name='Crossover Players', index=False)

        # NCAA Milestones
        milestones_data = processed_data.get('milestones', {})
        milestone_sheets = [
            ('multi_hr_games', 'Multi-HR Games'),
            ('hr_games', 'HR Games'),
            ('four_hit_games', '4+ Hit Games'),
            ('three_hit_games', '3+ Hit Games'),
            ('five_rbi_games', '5+ RBI Games'),
            ('ten_k_games', '10+ K Games'),
            ('quality_starts', 'Quality Starts'),
            ('complete_games', 'Complete Games'),
        ]

        for key, sheet_name in milestone_sheets:
            df = milestones_data.get(key, pd.DataFrame())
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"  Excel file saved: {output_path}")

    return processed_data
