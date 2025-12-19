"""
Main entry point for the NCAA Baseball Stats Processor.
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from .utils.constants import BASE_DIR, CACHE_DIR, ROSTERS_DIR, PDF_DIR, OUTPUT_DIR
from .excel.workbook_generator import generate_excel_workbook
from .website.generator import generate_website_from_data


# Add parent directory for imports
sys.path.insert(0, str(BASE_DIR))
from ncaab_parser import parse_ncaab_pdf
from name_matcher import NameMatcher, enrich_game_data


def process_pdf_file(
    file_path: str,
    matcher: Optional[NameMatcher] = None,
    use_cache: bool = True,
    index: Optional[int] = None,
    total: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Process a single PDF file with caching support.

    Args:
        file_path: Path to PDF file
        matcher: Optional NameMatcher for player linking
        use_cache: Whether to use/update cache
        index: Current file index (for progress)
        total: Total files (for progress)

    Returns:
        Parsed game data dictionary
    """
    filename = os.path.basename(file_path)
    filename_no_ext = os.path.splitext(filename)[0]
    safe_filename = re.sub(r'[^\w\-_]', '_', filename_no_ext)
    cache_path = CACHE_DIR / f"{safe_filename}.json"

    if index is not None and total is not None:
        print(f"[{index}/{total}] Processing: {filename}")
    else:
        print(f"Processing: {filename}")

    # Check cache
    if use_cache and cache_path.exists():
        pdf_mtime = os.path.getmtime(file_path)
        cache_mtime = os.path.getmtime(cache_path)

        if pdf_mtime <= cache_mtime:
            print("  Using cached data")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print("  Cache outdated, re-parsing...")

    # Parse PDF
    try:
        game_data = parse_ncaab_pdf(file_path)

        meta = game_data.get('metadata', {})
        print(f"  {meta.get('away_team', '?')} vs {meta.get('home_team', '?')}")
        print(f"  Score: {meta.get('away_team_score', '?')} - {meta.get('home_team_score', '?')}")

        # Enrich with bref_ids if matcher provided
        if matcher:
            game_data = enrich_game_data(game_data, matcher)

        # Save to cache
        if use_cache:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2)
            print("  Cached")

        return game_data

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def load_from_cache() -> List[Dict[str, Any]]:
    """Load all games from cache directory."""
    games = []
    cache_files = list(CACHE_DIR.glob("*.json"))
    print(f"Loading {len(cache_files)} games from cache...")

    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                games.append(json.load(f))
        except Exception as e:
            print(f"  Error loading {cache_file.name}: {e}")

    return games


def process_games(
    input_path: str = None,
    use_cache: bool = True,
    roster_dir: str = None,
) -> List[Dict[str, Any]]:
    """
    Process PDF files from directory or load from cache.

    Args:
        input_path: Path to PDF file or directory
        use_cache: Whether to use caching
        roster_dir: Directory with roster JSON files

    Returns:
        List of parsed game dictionaries
    """
    # Setup name matcher
    matcher = None
    if roster_dir and Path(roster_dir).exists():
        matcher = NameMatcher()
        count = matcher.load_rosters_from_dir(roster_dir)
        print(f"Loaded {count} rosters for player matching")

    games = []

    if input_path is None:
        input_path = str(PDF_DIR)

    if os.path.isfile(input_path):
        # Single file
        if input_path.endswith('.pdf'):
            game = process_pdf_file(input_path, matcher, use_cache)
            if game:
                games.append(game)
    elif os.path.isdir(input_path):
        # Directory
        pdf_files = list(Path(input_path).glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")

        for idx, pdf_file in enumerate(pdf_files, 1):
            game = process_pdf_file(str(pdf_file), matcher, use_cache, idx, len(pdf_files))
            if game:
                games.append(game)
    else:
        print(f"Invalid path: {input_path}")

    print(f"\nSuccessfully processed {len(games)} games")
    return games


def main():
    parser = argparse.ArgumentParser(
        description="NCAA Baseball Stats Processor - Parse PDFs and generate statistics"
    )

    parser.add_argument(
        'input_path',
        nargs='?',
        default=str(PDF_DIR),
        help='Directory containing PDF files or single PDF file'
    )

    parser.add_argument(
        '--output-excel', '-o',
        default=str(BASE_DIR / 'Baseball_Stats.xlsx'),
        help='Excel output filename'
    )

    parser.add_argument(
        '--roster-dir', '-r',
        default=str(ROSTERS_DIR),
        help='Directory with roster JSON files'
    )

    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching (always re-parse PDFs)'
    )

    parser.add_argument(
        '--from-cache-only',
        action='store_true',
        help='Load all games from cache only (skip PDF parsing)'
    )

    parser.add_argument(
        '--excel-only',
        action='store_true',
        help='Generate only Excel, skip website'
    )

    parser.add_argument(
        '--website-only',
        action='store_true',
        help='Generate only website, skip Excel'
    )

    parser.add_argument(
        '--save-json',
        action='store_true',
        help='Save intermediate JSON data file'
    )

    args = parser.parse_args()

    # Validate flags
    if args.excel_only and args.website_only:
        print("Error: Cannot use both --excel-only and --website-only")
        return

    print("NCAA Baseball Stats Processor")
    print("=" * 50)

    # Load game data
    if args.from_cache_only:
        games = load_from_cache()
    else:
        roster_dir = args.roster_dir if Path(args.roster_dir).exists() else None
        games = process_games(args.input_path, not args.no_cache, roster_dir)

    if not games:
        print("No games to process. Exiting.")
        return

    # Save intermediate JSON if requested
    if args.save_json:
        json_path = args.output_excel.replace('.xlsx', '_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(games, f, indent=2)
        print(f"JSON data saved: {json_path}")

    # Generate outputs
    try:
        if args.website_only:
            print("\nGenerating website only...")
            processed_data = generate_excel_workbook(games, args.output_excel, write_file=False)

            html_path = args.output_excel.replace('.xlsx', '.html')
            generate_website_from_data(processed_data, html_path, games)

            print(f"\nDone! Website: {os.path.abspath(html_path)}")

        elif args.excel_only:
            print("\nGenerating Excel only...")
            generate_excel_workbook(games, args.output_excel, write_file=True)

            print(f"\nDone! Excel: {os.path.abspath(args.output_excel)}")

        else:
            print("\nGenerating Excel and website...")

            processed_data = generate_excel_workbook(games, args.output_excel, write_file=True)

            html_path = args.output_excel.replace('.xlsx', '.html')
            generate_website_from_data(processed_data, html_path, games)

            print(f"\nDone!")
            print(f"Excel: {os.path.abspath(args.output_excel)}")
            print(f"Website: {os.path.abspath(html_path)}")

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
