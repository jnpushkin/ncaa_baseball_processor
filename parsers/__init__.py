"""
NCAA Baseball Box Score PDF Parsers.

This package contains parsers for converting NCAA baseball box score PDFs
into structured JSON format.
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import Optional

from .models import PlayerBattingStats, PitcherStats, PlayEvent
from .format_detection import detect_pdf_format
from .game_notes import extract_game_notes
from .metadata import extract_game_metadata, extract_format_b_metadata
from .format_a import (
    parse_box_score_from_tables,
    parse_side_by_side_batting_line,
    parse_side_by_side_pitching_line,
    VALID_POSITIONS,
)
from .format_a_no_num import parse_format_a_no_num_box_score
from .format_b import parse_format_b_box_score
from .play_by_play import parse_play_by_play, parse_format_b_play_by_play
from .statcrew_html import parse_statcrew_html


def parse_ncaab_pdf(pdf_path: str) -> dict:
    """
    Main function to parse an NCAA baseball box score PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing all parsed game data
    """
    result = {
        "metadata": {},
        "box_score": {},
        "game_notes": {},
        "play_by_play": {},
        "format": None
    }

    with pdfplumber.open(pdf_path) as pdf:
        page_texts = [page.extract_text() or "" for page in pdf.pages]
        full_text = "\n".join(page_texts) + "\n"

        def first_page_matching(pattern: str, default_index: int = 0) -> int:
            for page_index, page_text in enumerate(page_texts):
                if re.search(pattern, page_text, re.IGNORECASE):
                    return page_index
            return default_index if pdf.pages else 0

        # Detect PDF format
        pdf_format = detect_pdf_format(full_text)
        result["format"] = pdf_format

        # Extract game notes (applies to all formats)
        result["game_notes"] = extract_game_notes(full_text)

        if pdf_format == 'format_b':
            # Use format B parsers (newer NCAA format)
            result["metadata"] = extract_format_b_metadata(full_text)

            # Parse box score from page 1 (format B has everything on page 1)
            page1_text = pdf.pages[0].extract_text() or ""
            result["box_score"] = parse_format_b_box_score(page1_text)

            # Parse play-by-play (starts on page 2 for format B)
            pbp_text = ""
            for page in pdf.pages[1:]:
                page_text = page.extract_text() or ""
                pbp_text += page_text + "\n"
            result["play_by_play"] = parse_format_b_play_by_play(pbp_text)

        elif pdf_format == 'format_a_no_num':
            # Format A without jersey numbers
            result["metadata"] = extract_game_metadata(full_text)

            # Parse the page that contains the box table. Some StatCrew PDFs are
            # one-page box scores, while older exports place the table on page 2.
            box_page_index = 0
            if pdf.pages:
                box_page_index = first_page_matching(r'Player\s+ab\s+r\s+h\s+rbi', 1 if len(pdf.pages) >= 2 else 0)
                result["box_score"] = parse_format_a_no_num_box_score(pdf.pages[box_page_index])

            # Parse play-by-play
            pbp_text = ""
            pbp_start = (box_page_index + 1) if pdf.pages else 0
            for page in pdf.pages[pbp_start:]:
                page_text = page.extract_text() or ""
                if 'Scoring Innings - Final' in page_text:
                    break
                pbp_text += page_text + "\n"
            result["play_by_play"] = parse_play_by_play(pbp_text)

        else:
            # Use format A parsers (original format with jersey numbers)
            result["metadata"] = extract_game_metadata(full_text)

            # Parse the page that contains the box table (usually page 2).
            box_page_index = 0
            if pdf.pages:
                box_page_index = first_page_matching(r'#\s*player\s+pos\s+ab\s+r\s+h\s+rbi', 1 if len(pdf.pages) >= 2 else 0)
                result["box_score"] = parse_box_score_from_tables(pdf.pages[box_page_index])

            # Parse play-by-play (pages 3 onward)
            pbp_text = ""
            pbp_start = (box_page_index + 1) if pdf.pages else 0
            for page in pdf.pages[pbp_start:]:
                page_text = page.extract_text() or ""
                if 'Scoring Innings - Final' in page_text:
                    break
                pbp_text += page_text + "\n"
            result["play_by_play"] = parse_play_by_play(pbp_text)

    # If venue-based validation detected teams should be swapped, swap them
    # Note: Only swap metadata team names, NOT the batting lineups
    # The lineups are parsed in order from the PDF and are correct;
    # it's the team name labels that are wrong
    if result["metadata"].get("_teams_swapped"):
        meta = result["metadata"]

        # Swap team metadata only - the lineups stay as-is
        meta["away_team"], meta["home_team"] = meta["home_team"], meta["away_team"]
        meta["away_team_score"], meta["home_team_score"] = meta["home_team_score"], meta["away_team_score"]
        meta["away_team_rank"], meta["home_team_rank"] = meta["home_team_rank"], meta["away_team_rank"]
        meta["away_team_record"], meta["home_team_record"] = meta["home_team_record"], meta["away_team_record"]

        # Remove the swap flag from output
        del meta["_teams_swapped"]

    return result


def convert_pdf_to_json(pdf_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert a PDF to JSON and optionally save to file.

    Args:
        pdf_path: Path to input PDF
        output_path: Optional path for output JSON (default: same name as PDF with .json extension)

    Returns:
        JSON string of parsed data
    """
    data = parse_ncaab_pdf(pdf_path)
    json_str = json.dumps(data, indent=2)

    if output_path is None:
        output_path = str(Path(pdf_path).with_suffix('.json'))

    with open(output_path, 'w') as f:
        f.write(json_str)

    print(f"Saved JSON to: {output_path}")
    return json_str


__all__ = [
    'parse_ncaab_pdf',
    'parse_statcrew_html',
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
