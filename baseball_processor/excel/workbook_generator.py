"""
Excel workbook generator for baseball statistics.
"""

import os
from typing import Dict, List, Any
import pandas as pd

from ..processors.player_stats import PlayerStatsProcessor
from ..processors.milestones import MilestonesProcessor
from ..processors.team_records import TeamRecordsProcessor
from ..processors.game_log import GameLogProcessor


def generate_excel_workbook(
    games: List[Dict[str, Any]],
    output_path: str,
    write_file: bool = True
) -> Dict[str, Any]:
    """
    Generate Excel workbook from parsed games data.

    Args:
        games: List of parsed game dictionaries
        output_path: Path to save the Excel file
        write_file: Whether to actually write the file

    Returns:
        Dictionary containing all processed DataFrames
    """
    print(f"Processing {len(games)} games...")

    processed_data = {}

    # Game Log
    print("  Creating game log...")
    game_log_processor = GameLogProcessor(games)
    processed_data['game_log'] = game_log_processor.create_game_log()

    # Player Stats
    print("  Processing player statistics...")
    player_processor = PlayerStatsProcessor(games)
    player_data = player_processor.process_all_stats()
    processed_data['batters'] = player_data['batters']
    processed_data['pitchers'] = player_data['pitchers']
    processed_data['batter_games'] = player_data['batter_games']
    processed_data['pitcher_games'] = player_data['pitcher_games']

    # Milestones
    print("  Processing milestones...")
    milestones_processor = MilestonesProcessor(games)
    milestones_data = milestones_processor.process_all_milestones()
    processed_data['milestones'] = milestones_data

    # Team Records
    print("  Processing team records...")
    team_processor = TeamRecordsProcessor(games)
    team_data = team_processor.process_team_records()
    processed_data['team_records'] = team_data['team_records']
    processed_data['venue_records'] = team_data['venue_records']

    if not write_file:
        print("  Skipping Excel file generation")
        return processed_data

    # Write Excel file
    print(f"  Writing Excel file: {output_path}")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Game Log
        if not processed_data['game_log'].empty:
            processed_data['game_log'].to_excel(writer, sheet_name='Game Log', index=False)

        # Batters
        if not processed_data['batters'].empty:
            processed_data['batters'].to_excel(writer, sheet_name='Batters', index=False)

        # Pitchers
        if not processed_data['pitchers'].empty:
            processed_data['pitchers'].to_excel(writer, sheet_name='Pitchers', index=False)

        # Team Records
        if not processed_data['team_records'].empty:
            processed_data['team_records'].to_excel(writer, sheet_name='Team Records', index=False)

        # Milestones
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
