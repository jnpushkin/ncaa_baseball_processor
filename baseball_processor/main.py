"""
Main entry point for the NCAA Baseball Stats Processor.

Supports processing:
- NCAA baseball box scores (from PDFs)
- MiLB games (from MLB Stats API)

With player crossover tracking across NCAA and MiLB levels.
"""

import os
import sys
import json
import argparse
import shutil
import subprocess

from .utils.constants import (
    BASE_DIR,
    CACHE_DIR,
    ROSTERS_DIR,
    PDF_DIR,
    MILB_CACHE_DIR,
    PARTNER_CACHE_DIR,
    PARTNER_ARTIFACT_DIR,
    NCAA_API_CACHE_DIR,
)
from .excel.workbook_generator import generate_excel_workbook
from .pipeline import build_crossover_data as build_pipeline_crossover_data
from .sources import load_source_games
from .website.generator import generate_nextjs_data


# Add parent directory for root-level legacy modules used by parsers/pipeline.
sys.path.insert(0, str(BASE_DIR))


def main():
    parser = argparse.ArgumentParser(
        description="Baseball Stats Processor - NCAA and MiLB crossover tracking"
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
        '--save-json',
        action='store_true',
        help='Save intermediate JSON data file'
    )

    # MiLB options
    parser.add_argument(
        '--include-milb',
        action='store_true',
        default=True,
        help='Include MiLB games from game_ids.txt (default: on)'
    )
    parser.add_argument(
        '--no-milb',
        action='store_true',
        help='Exclude MiLB games'
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
        default=True,
        help='Include Partner League games (default: on)'
    )
    parser.add_argument(
        '--no-partner',
        action='store_true',
        help='Exclude Partner League games'
    )

    parser.add_argument(
        '--partner-game',
        type=str,
        help='Process a single Partner League game (format: league:game_id, e.g., pioneer:20240828_fhp1)'
    )
    parser.add_argument(
        '--pioneer-by-date',
        type=str,
        metavar='YYYY-MM-DD',
        help='List Pioneer League games on a date, pick one to add to game_ids.txt and fetch'
    )
    parser.add_argument(
        '--download-pioneer-pdfs',
        action='store_true',
        help='Save rendered Pioneer source HTML plus a generated PDF of the print view when processing Pioneer games'
    )
    parser.add_argument(
        '--pioneer-artifact-dir',
        default=str(PARTNER_ARTIFACT_DIR),
        help='Directory for Pioneer source artifacts (default: partner/artifacts)'
    )

    # NCAA API options
    parser.add_argument(
        '--no-ncaa-api',
        action='store_true',
        help='Exclude NCAA API games'
    )
    parser.add_argument(
        '--ncaa-api-game',
        type=str,
        help='Process a single NCAA API game by game ID'
    )
    parser.add_argument(
        '--ncaa-api-date',
        type=str,
        help='Fetch all NCAA API games for a date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--ncaa-api-date-range',
        nargs=2,
        metavar=('START', 'END'),
        help='Fetch NCAA API games for a date range (YYYY-MM-DD YYYY-MM-DD)'
    )
    parser.add_argument(
        '--ncaa-api-only',
        action='store_true',
        help='Process only NCAA API games (skip PDF, MiLB, Partner)'
    )

    # Crossover options
    parser.add_argument(
        '--crossover',
        action='store_true',
        help='Generate player crossover report (NCAA/MiLB)'
    )

    # Schedule options
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Scrape upcoming game schedule from D1Baseball.com'
    )
    parser.add_argument(
        '--refresh-schedule',
        action='store_true',
        help='Force refresh schedule cache (ignore TTL)'
    )
    parser.add_argument(
        '--schedule-days',
        type=int,
        default=None,
        help='Number of days ahead to scrape (default: full season Feb 14 - Jun 30)'
    )

    # Draft tracking options
    parser.add_argument(
        '--fetch-draft',
        action='store_true',
        help='Fetch MLB draft data for crossover player matching'
    )
    parser.add_argument(
        '--draft-years',
        type=str,
        default=None,
        help='Draft year range to fetch (e.g., "2020-2025" or "2024")'
    )

    # Deploy options
    parser.add_argument(
        '--no-deploy',
        action='store_true',
        help='Skip automatic Surge deployment after website generation'
    )
    parser.add_argument(
        '--deploy-domain',
        default='ncaa-baseball.surge.sh',
        help='Surge domain to deploy to (default: ncaa-baseball.surge.sh)'
    )

    # Cross-project options
    parser.add_argument(
        '--export-players',
        action='store_true',
        help='Generate shared_players.json for cross-project player linking'
    )

    # Database options
    parser.add_argument(
        '--migrate-cache',
        action='store_true',
        help='Migrate all JSON cache files into SQLite database'
    )
    parser.add_argument(
        '--db-stats',
        action='store_true',
        help='Show database statistics'
    )
    parser.add_argument(
        '--from-db',
        action='store_true',
        help='Load all games from SQLite database instead of cache'
    )

    args = parser.parse_args()

    if args.from_cache_only or args.from_db:
        os.environ['NCAA_BASEBALL_OFFLINE'] = '1'

    # Handle database commands
    if args.migrate_cache:
        from .db.database import Database
        db = Database()
        print("Migrating cache files to SQLite database...")
        ncaa_imported, ncaa_errors = db.migrate_from_cache(CACHE_DIR, 'ncaa')
        milb_imported, milb_errors = db.migrate_from_cache(MILB_CACHE_DIR, 'milb')
        partner_imported, partner_errors = db.migrate_from_cache(PARTNER_CACHE_DIR, 'partner')
        ncaa_api_imported, ncaa_api_errors = db.migrate_from_cache(NCAA_API_CACHE_DIR, 'ncaa_api')
        total = ncaa_imported + milb_imported + partner_imported + ncaa_api_imported
        total_errors = ncaa_errors + milb_errors + partner_errors + ncaa_api_errors
        print(f"\nTotal: {total} games migrated, {total_errors} errors")
        stats = db.get_stats()
        print(f"Database: {stats}")
        return

    if args.db_stats:
        from .db.database import Database
        db = Database()
        stats = db.get_stats()
        print("Database Statistics:")
        for key, val in stats.items():
            print(f"  {key}: {val}")
        return

    print("Baseball Stats Processor")
    print("=" * 50)

    # Handle schedule scraping
    schedule_games = []
    if args.schedule or args.refresh_schedule:
        from .utils.schedule_scraper import get_schedule
        from datetime import datetime, timedelta
        # Use explicit days if provided, otherwise let get_schedule use full-season default
        if args.schedule_days is not None:
            start = datetime.now()
            end = start + timedelta(days=args.schedule_days)
        else:
            start = None
            end = None
        schedule_games = get_schedule(
            force_refresh=args.refresh_schedule,
            start_date=start,
            end_date=end,
        )
        print(f"Schedule: {len(schedule_games)} upcoming games loaded")

    # Handle draft data fetching
    draft_picks = []
    if args.fetch_draft:
        sys.path.insert(0, str(BASE_DIR))
        from parsers.draft_api import fetch_draft_range
        if args.draft_years:
            if '-' in args.draft_years:
                start, end = args.draft_years.split('-')
                draft_picks = fetch_draft_range(int(start), int(end))
            else:
                draft_picks = fetch_draft_range(int(args.draft_years), int(args.draft_years))
        else:
            from datetime import datetime as dt
            draft_picks = fetch_draft_range(2020, dt.now().year)
        print(f"Draft: {len(draft_picks)} picks loaded")

    source_games = load_source_games(args)
    ncaa_games = source_games.ncaa_games
    ncaa_api_games = source_games.ncaa_api_games
    milb_games = source_games.milb_games
    partner_games = source_games.partner_games

    all_ncaa = source_games.all_ncaa
    pro_minor_games = source_games.pro_minor_games
    processing_ncaa = source_games.processing_ncaa
    all_games = processing_ncaa + pro_minor_games

    if not all_games:
        print("No games to process. Exiting.")
        return

    print(f"\nTotal: {' + '.join(source_games.summary_parts())} = {len(all_games)} games")

    # Build crossover data if requested
    crossover_data = None
    if args.crossover or milb_games or partner_games or args.export_players:
        print("\nBuilding crossover tracking data...")
        crossover_data = build_pipeline_crossover_data(
            processing_ncaa,
            milb_games,
            partner_games,
        )

        summary = crossover_data.get_summary()
        print(f"  Total players tracked: {summary['total_players']}")
        print(f"  Crossover players: {summary['crossover_players']}")
        if summary['crossover_players'] > 0:
            print(f"    NCAA -> MiLB: {summary['ncaa_to_milb']}")

    # Generate shared player export if requested
    if args.export_players and crossover_data:
        from .exporters.shared_players import generate_shared_export
        generate_shared_export(crossover_data, website_url=f"https://{args.deploy_domain}")

    # Save intermediate JSON if requested
    if args.save_json:
        json_path = args.output_excel.replace('.xlsx', '_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'ncaa_games': ncaa_games,
                'ncaa_api_games': ncaa_api_games,
                'milb_games': milb_games,
                'partner_games': partner_games,
            }, f, indent=2)
        print(f"JSON data saved: {json_path}")

    # Load schedule data for website (from cache if not freshly scraped)
    if not schedule_games and not args.excel_only:
        from .utils.schedule_scraper import load_schedule_cache
        schedule_games = load_schedule_cache()

    # Generate outputs
    try:
        if args.excel_only:
            print("\nGenerating Excel only...")
            generate_excel_workbook(
                all_games, args.output_excel, write_file=True,
                milb_games=pro_minor_games, crossover_data=crossover_data
            )
            print(f"\nDone! Excel: {os.path.abspath(args.output_excel)}")
            return

        print("\nGenerating Excel and Next.js website...")
        processed_data = generate_excel_workbook(
            all_games, args.output_excel, write_file=True,
            milb_games=pro_minor_games, crossover_data=crossover_data
        )

        json_path = generate_nextjs_data(processed_data, all_games, schedule_games=schedule_games)
        print(f"\nNext.js data ready: {json_path}")

        web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')
        if not os.path.isdir(web_dir):
            print(f"Warning: web/ directory not found at {web_dir}")
            return

        print("\nBuilding Next.js site...")
        build_result = subprocess.run(
            ['npm', 'run', 'build'],
            cwd=web_dir,
            capture_output=True, text=True
        )
        if build_result.returncode != 0:
            print(f"Next.js build failed:\n{build_result.stderr or build_result.stdout}")
            return
        print("Next.js build succeeded.")

        if args.no_deploy:
            return

        out_dir = os.path.join(web_dir, 'out')
        if not shutil.which('surge'):
            print("Skipping deploy: 'surge' CLI not found.")
            return
        if not os.path.isdir(out_dir):
            print(f"Skipping deploy: build output not found at {out_dir}")
            return

        print(f"\nDeploying to {args.deploy_domain}...")
        deploy_result = subprocess.run(
            ['surge', out_dir, '--domain', args.deploy_domain],
            capture_output=True, text=True
        )
        if deploy_result.returncode == 0:
            print(f"Deployed to https://{args.deploy_domain}")
        else:
            print(f"Deploy failed: {deploy_result.stderr or deploy_result.stdout}")

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == '__main__':
    main()
