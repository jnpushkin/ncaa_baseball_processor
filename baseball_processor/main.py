"""
Main entry point for the NCAA Baseball Stats Processor.

Supports processing:
- NCAA baseball box scores (from PDFs)
- MiLB games (from MLB Stats API)
- MLB games (read-only from MLB Game Tracker cache)

With player crossover tracking across all levels.
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from .utils.constants import (
    BASE_DIR, CACHE_DIR, ROSTERS_DIR, PDF_DIR, OUTPUT_DIR,
    MILB_DIR, MILB_CACHE_DIR, MILB_GAME_IDS_FILE, MLB_TRACKER_CACHE,
    PARTNER_DIR, PARTNER_CACHE_DIR, PARTNER_GAME_IDS_FILE
)
from .excel.workbook_generator import generate_excel_workbook
from .website.generator import generate_website_from_data


# Add parent directory for imports
sys.path.insert(0, str(BASE_DIR))
from ncaab_parser import parse_ncaab_pdf
from name_matcher import NameMatcher, enrich_game_data
from parsers.milb_api import process_all_milb_games, process_milb_game
from parsers.partner_leagues import process_all_partner_games, process_partner_game
from mlb_reader import MLBDataReader
from player_crossover import PlayerCrossover


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
    """Load all NCAA games from cache directory."""
    games = []
    cache_files = list(CACHE_DIR.glob("*.json"))
    print(f"Loading {len(cache_files)} NCAA games from cache...")

    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                games.append(json.load(f))
        except Exception as e:
            print(f"  Error loading {cache_file.name}: {e}")

    return games


def load_milb_games() -> List[Dict[str, Any]]:
    """
    Load MiLB games from game IDs file.

    Returns:
        List of MiLB game data dicts
    """
    if not MILB_GAME_IDS_FILE.exists():
        print("No MiLB game_ids.txt file found")
        return []

    # Ensure cache directory exists
    MILB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    return process_all_milb_games(MILB_GAME_IDS_FILE, MILB_CACHE_DIR)


def load_milb_from_cache() -> List[Dict[str, Any]]:
    """Load all MiLB games from cache directory."""
    games = []

    if not MILB_CACHE_DIR.exists():
        return games

    cache_files = list(MILB_CACHE_DIR.glob("milb_*.json"))
    print(f"Loading {len(cache_files)} MiLB games from cache...")

    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                games.append(json.load(f))
        except Exception as e:
            print(f"  Error loading {cache_file.name}: {e}")

    return games


def load_partner_games() -> List[Dict[str, Any]]:
    """
    Load Partner League games from game IDs file.

    Returns:
        List of Partner League game data dicts
    """
    if not PARTNER_GAME_IDS_FILE.exists():
        print("No partner league game_ids.txt file found")
        return []

    # Ensure cache directory exists
    PARTNER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    return process_all_partner_games(PARTNER_GAME_IDS_FILE, PARTNER_CACHE_DIR)


def load_partner_from_cache() -> List[Dict[str, Any]]:
    """Load all Partner League games from cache directory."""
    games = []

    if not PARTNER_CACHE_DIR.exists():
        return games

    cache_files = list(PARTNER_CACHE_DIR.glob("*.json"))
    print(f"Loading {len(cache_files)} Partner League games from cache...")

    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                games.append(json.load(f))
        except Exception as e:
            print(f"  Error loading {cache_file.name}: {e}")

    return games


def build_crossover_data(
    ncaa_games: List[Dict[str, Any]],
    milb_games: List[Dict[str, Any]],
    include_mlb: bool = True,
    mlb_cache_path: Optional[Path] = None,
) -> PlayerCrossover:
    """
    Build player crossover tracking data.

    Args:
        ncaa_games: List of NCAA game data
        milb_games: List of MiLB game data
        include_mlb: Whether to include MLB data
        mlb_cache_path: Path to MLB Game Tracker cache

    Returns:
        PlayerCrossover instance with all data loaded
    """
    crossover = PlayerCrossover()

    # Load NCAA data
    if ncaa_games:
        print(f"Loading {len(ncaa_games)} NCAA games for crossover...")
        crossover.load_ncaa_data(ncaa_games)

    # Load MiLB data
    if milb_games:
        print(f"Loading {len(milb_games)} MiLB games for crossover...")
        crossover.load_milb_data(milb_games)

    # Load MLB data (read-only)
    if include_mlb:
        cache_path = mlb_cache_path or MLB_TRACKER_CACHE
        if cache_path.exists():
            print("Loading MLB data for crossover...")
            mlb_reader = MLBDataReader(cache_path)
            mlb_reader.load_cache()
            crossover.load_mlb_data(mlb_reader)

    return crossover


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
        description="Baseball Stats Processor - NCAA, MiLB, and MLB crossover tracking"
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

    # MiLB options
    parser.add_argument(
        '--include-milb',
        action='store_true',
        help='Include MiLB games from game_ids.txt'
    )

    parser.add_argument(
        '--milb-only',
        action='store_true',
        help='Process only MiLB games (skip NCAA)'
    )

    parser.add_argument(
        '--milb-game',
        type=int,
        help='Process a single MiLB game by game_pk ID'
    )

    # Partner League options
    parser.add_argument(
        '--include-partner',
        action='store_true',
        help='Include Partner League games (Pioneer, Atlantic, American Association, Frontier)'
    )

    parser.add_argument(
        '--partner-game',
        type=str,
        help='Process a single Partner League game (format: league:game_id, e.g., pioneer:20240828_fhp1)'
    )

    # Crossover options
    parser.add_argument(
        '--crossover',
        action='store_true',
        help='Generate player crossover report (NCAA/MiLB/MLB)'
    )

    parser.add_argument(
        '--mlb-cache',
        type=str,
        default=str(MLB_TRACKER_CACHE),
        help='Path to MLB Game Tracker cache (for crossover tracking)'
    )

    parser.add_argument(
        '--no-mlb',
        action='store_true',
        help='Skip MLB data in crossover tracking'
    )

    args = parser.parse_args()

    # Validate flags
    if args.excel_only and args.website_only:
        print("Error: Cannot use both --excel-only and --website-only")
        return

    print("Baseball Stats Processor")
    print("=" * 50)

    ncaa_games = []
    milb_games = []
    partner_games = []

    # Handle single MiLB game
    if args.milb_game:
        print(f"\nProcessing single MiLB game: {args.milb_game}")
        MILB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        game_data = process_milb_game(args.milb_game, MILB_CACHE_DIR)
        milb_games.append(game_data)
        meta = game_data['metadata']
        print(f"  {meta['away_team']} @ {meta['home_team']}")
        print(f"  Score: {meta['away_team_score']} - {meta['home_team_score']}")

    # Handle single Partner League game
    if args.partner_game:
        if ':' not in args.partner_game:
            print("Error: --partner-game must be in format league:game_id")
            return
        league, game_id = args.partner_game.split(':', 1)
        print(f"\nProcessing single Partner League game: {league}:{game_id}")
        PARTNER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        game_data = process_partner_game(game_id, league, PARTNER_CACHE_DIR)
        partner_games.append(game_data)
        meta = game_data['metadata']
        print(f"  [{meta.get('league', {}).get('home', league)}] {meta['away_team']} @ {meta['home_team']}")
        print(f"  Score: {meta['away_team_score']} - {meta['home_team_score']}")

    # Load NCAA games (unless milb-only)
    elif not args.milb_only:
        if args.from_cache_only:
            ncaa_games = load_from_cache()
        else:
            roster_dir = args.roster_dir if Path(args.roster_dir).exists() else None
            ncaa_games = process_games(args.input_path, not args.no_cache, roster_dir)

    # Load MiLB games
    if args.include_milb or args.milb_only:
        if args.from_cache_only:
            milb_games = load_milb_from_cache()
        else:
            milb_games = load_milb_games()

    # Load Partner League games
    if args.include_partner:
        if args.from_cache_only:
            partner_games = load_partner_from_cache()
        else:
            partner_games = load_partner_games()

    # Combine games for processing (partner games are included with MiLB for stats)
    all_games = ncaa_games + milb_games + partner_games

    if not all_games:
        print("No games to process. Exiting.")
        return

    print(f"\nTotal: {len(ncaa_games)} NCAA + {len(milb_games)} MiLB + {len(partner_games)} Partner = {len(all_games)} games")

    # Combine MiLB and Partner games for processing (both are minor/independent leagues)
    pro_minor_games = milb_games + partner_games

    # Build crossover data if requested
    crossover_data = None
    if args.crossover or args.include_milb or args.milb_only or args.include_partner:
        print("\nBuilding crossover tracking data...")
        crossover_data = build_crossover_data(
            ncaa_games,
            pro_minor_games,
            include_mlb=not args.no_mlb,
            mlb_cache_path=Path(args.mlb_cache) if args.mlb_cache else None,
        )

        summary = crossover_data.get_summary()
        print(f"  Total players tracked: {summary['total_players']}")
        print(f"  Crossover players: {summary['crossover_players']}")
        if summary['crossover_players'] > 0:
            print(f"    NCAA -> MiLB: {summary['ncaa_to_milb']}")
            print(f"    MiLB -> MLB: {summary['milb_to_mlb']}")
            print(f"    NCAA -> MLB: {summary['ncaa_to_mlb']}")
            print(f"    All levels: {summary['all_levels']}")

    # Save intermediate JSON if requested
    if args.save_json:
        json_path = args.output_excel.replace('.xlsx', '_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'ncaa_games': ncaa_games,
                'milb_games': milb_games,
                'partner_games': partner_games,
            }, f, indent=2)
        print(f"JSON data saved: {json_path}")

    # Generate outputs
    try:
        if args.website_only:
            print("\nGenerating website only...")
            processed_data = generate_excel_workbook(
                all_games, args.output_excel, write_file=False,
                milb_games=pro_minor_games, crossover_data=crossover_data
            )

            html_path = args.output_excel.replace('.xlsx', '.html')
            generate_website_from_data(processed_data, html_path, all_games)

            print(f"\nDone! Website: {os.path.abspath(html_path)}")

        elif args.excel_only:
            print("\nGenerating Excel only...")
            generate_excel_workbook(
                all_games, args.output_excel, write_file=True,
                milb_games=pro_minor_games, crossover_data=crossover_data
            )

            print(f"\nDone! Excel: {os.path.abspath(args.output_excel)}")

        else:
            print("\nGenerating Excel and website...")

            processed_data = generate_excel_workbook(
                all_games, args.output_excel, write_file=True,
                milb_games=pro_minor_games, crossover_data=crossover_data
            )

            html_path = args.output_excel.replace('.xlsx', '.html')
            generate_website_from_data(processed_data, html_path, all_games)

            print(f"\nDone!")
            print(f"Excel: {os.path.abspath(args.output_excel)}")
            print(f"Website: {os.path.abspath(html_path)}")

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
