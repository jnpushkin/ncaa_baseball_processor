"""
NCAA Baseball Box Score PDF Parser

Converts NCAA baseball box score PDFs into structured JSON format.
Supports multiple PDF formats from different years/sources.

This is a backward-compatibility layer. The actual implementation
is in the parsers/ package.
"""

# Re-export from parsers package for backward compatibility
from parsers import (
    parse_ncaab_pdf,
    convert_pdf_to_json,
    PlayerBattingStats,
    PitcherStats,
    PlayEvent,
    detect_pdf_format,
    extract_game_notes,
    extract_game_metadata,
    extract_format_b_metadata,
    parse_box_score_from_tables,
    parse_format_a_no_num_box_score,
    parse_format_b_box_score,
    parse_play_by_play,
    parse_format_b_play_by_play,
    VALID_POSITIONS,
)

__all__ = [
    'parse_ncaab_pdf',
    'convert_pdf_to_json',
    'PlayerBattingStats',
    'PitcherStats',
    'PlayEvent',
    'detect_pdf_format',
    'extract_game_notes',
    'extract_game_metadata',
    'extract_format_b_metadata',
    'parse_box_score_from_tables',
    'parse_format_a_no_num_box_score',
    'parse_format_b_box_score',
    'parse_play_by_play',
    'parse_format_b_play_by_play',
    'VALID_POSITIONS',
]


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python ncaab_parser.py <pdf_path> [output_path]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = convert_pdf_to_json(pdf_path, output_path)
    print("\nPreview of parsed data:")
    data = json.loads(result)
    print(f"Game: {data['metadata'].get('away_team')} vs {data['metadata'].get('home_team')}")
    print(f"Date: {data['metadata'].get('date')}")
    print(f"Score: {data['metadata'].get('away_team_score')} - {data['metadata'].get('home_team_score')}")
    print(f"Batting stats parsed: {len(data['box_score'].get('away_batting', []))} away, {len(data['box_score'].get('home_batting', []))} home")
    print(f"Innings with play-by-play: {len(data['play_by_play'])}")
