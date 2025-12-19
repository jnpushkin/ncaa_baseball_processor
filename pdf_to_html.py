#!/usr/bin/env python3
"""
NCAA Baseball PDF to HTML Pipeline

Complete pipeline to convert NCAA baseball box score PDFs to
Baseball Reference-style HTML pages with player links.

Usage:
    python pdf_to_html.py <pdf_file> [options]
    python pdf_to_html.py --batch <pdf_dir> [options]

Options:
    --output-dir DIR    Directory for output files (default: html_output)
    --roster-dir DIR    Directory with roster JSON files
    --keep-json         Keep intermediate JSON files
    --scrape-rosters    Scrape rosters for teams in the PDF before processing
"""

import sys
import os
from pathlib import Path
import argparse
import json
import time

# Import our modules
from ncaab_parser import parse_ncaab_pdf
from name_matcher import NameMatcher, enrich_game_data
from ncaab_html_generator import generate_html_page
from bref_roster_scraper import search_team, fetch_roster, scraper, REQUEST_DELAY


def scrape_roster_for_team(team_name: str, roster_dir: str) -> bool:
    """
    Scrape roster for a team if not already cached.

    Args:
        team_name: Team name to search for
        roster_dir: Directory to save roster

    Returns:
        True if roster is available (cached or newly scraped)
    """
    roster_path = Path(roster_dir)
    roster_path.mkdir(exist_ok=True)

    # Check if we already have a roster for this team
    for existing in roster_path.glob("*.json"):
        try:
            with open(existing, 'r') as f:
                data = json.load(f)
                if team_name.lower() in data.get('team_name', '').lower():
                    print(f"  Using cached roster: {existing.name}")
                    return True
        except:
            pass

    # Search and scrape
    print(f"  Searching for roster: {team_name}")
    teams = search_team(team_name)

    if not teams:
        print(f"  No roster found for: {team_name}")
        return False

    team = teams[0]
    print(f"  Found: {team['name']} (ID: {team['id']})")

    time.sleep(REQUEST_DELAY)

    roster = fetch_roster(team['id'])
    if not roster or not roster.players:
        print(f"  Failed to fetch roster")
        return False

    # Save roster
    import re
    from dataclasses import asdict
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', roster.team_name).strip('_').lower()
    filename = roster_path / f"{safe_name}.json"

    roster_dict = {
        "team_name": roster.team_name,
        "team_id": roster.team_id,
        "year": roster.year,
        "players": [asdict(p) for p in roster.players]
    }

    with open(filename, 'w') as f:
        json.dump(roster_dict, f, indent=2)

    print(f"  Saved roster: {filename.name}")
    return True


def process_pdf(
    pdf_path: str,
    output_dir: str = "html_output",
    roster_dir: str = None,
    keep_json: bool = False,
    scrape_rosters: bool = False
) -> str:
    """
    Process a single PDF file through the complete pipeline.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory for output files
        roster_dir: Directory with roster files (or to save scraped rosters)
        keep_json: Whether to keep the intermediate JSON file
        scrape_rosters: Whether to scrape rosters for teams in the PDF

    Returns:
        Path to the generated HTML file
    """
    pdf_path = Path(pdf_path)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print(f"\nProcessing: {pdf_path.name}")
    print("=" * 60)

    # Step 1: Parse PDF to JSON
    print("\n[1/4] Parsing PDF...")
    try:
        game_data = parse_ncaab_pdf(str(pdf_path))
        print(f"  Format detected: {game_data.get('format', 'unknown')}")
        print(f"  Teams: {game_data['metadata'].get('away_team', '?')} vs {game_data['metadata'].get('home_team', '?')}")
        print(f"  Score: {game_data['metadata'].get('away_team_score', '?')} - {game_data['metadata'].get('home_team_score', '?')}")
    except Exception as e:
        print(f"  ERROR parsing PDF: {e}")
        return None

    # Step 2: Scrape rosters if requested
    if scrape_rosters and roster_dir:
        print("\n[2/4] Scraping rosters...")
        away_team = game_data['metadata'].get('away_team', '')
        home_team = game_data['metadata'].get('home_team', '')

        if away_team:
            scrape_roster_for_team(away_team, roster_dir)
            time.sleep(REQUEST_DELAY)

        if home_team:
            scrape_roster_for_team(home_team, roster_dir)
    else:
        print("\n[2/4] Skipping roster scraping")

    # Step 3: Match player names to bref_ids
    print("\n[3/4] Matching player names...")
    if roster_dir and Path(roster_dir).exists():
        matcher = NameMatcher()
        count = matcher.load_rosters_from_dir(roster_dir)
        print(f"  Loaded {count} rosters")

        if count > 0:
            game_data = enrich_game_data(game_data, matcher)

            # Count successful matches
            total_players = 0
            matched_players = 0
            for section in ['away_batting', 'home_batting', 'away_pitching', 'home_pitching']:
                for player in game_data.get('box_score', {}).get(section, []):
                    total_players += 1
                    if player.get('bref_id'):
                        matched_players += 1

            print(f"  Matched {matched_players}/{total_players} players to bref_ids")
    else:
        print("  No roster directory specified, skipping name matching")

    # Step 4: Generate HTML
    print("\n[4/4] Generating HTML...")
    html = generate_html_page(game_data)

    # Create output filename
    meta = game_data.get('metadata', {})
    date = meta.get('date', '').replace('/', '-')
    away = meta.get('away_team', 'away')
    home = meta.get('home_team', 'home')

    if date:
        html_filename = f"{date}_{away}_vs_{home}.html"
    else:
        html_filename = pdf_path.stem + ".html"

    html_filename = html_filename.replace(' ', '_')
    html_path = output_path / html_filename

    with open(html_path, 'w') as f:
        f.write(html)

    print(f"  Generated: {html_path}")

    # Optionally save JSON
    if keep_json:
        json_path = output_path / (pdf_path.stem + ".json")
        with open(json_path, 'w') as f:
            json.dump(game_data, f, indent=2)
        print(f"  JSON saved: {json_path}")

    print("\nDone!")
    return str(html_path)


def process_batch(
    pdf_dir: str,
    output_dir: str = "html_output",
    roster_dir: str = None,
    keep_json: bool = False,
    scrape_rosters: bool = False
) -> list:
    """
    Process all PDF files in a directory.

    Args:
        pdf_dir: Directory containing PDF files
        output_dir: Directory for output files
        roster_dir: Directory with roster files
        keep_json: Whether to keep intermediate JSON files
        scrape_rosters: Whether to scrape rosters

    Returns:
        List of generated HTML file paths
    """
    pdf_path = Path(pdf_dir)
    pdf_files = list(pdf_path.glob("*.pdf")) + list(pdf_path.glob("*.PDF"))

    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return []

    print(f"Found {len(pdf_files)} PDF files to process")

    html_files = []
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(pdf_files)}")

        result = process_pdf(
            str(pdf_file),
            output_dir,
            roster_dir,
            keep_json,
            scrape_rosters
        )

        if result:
            html_files.append(result)

    print(f"\n{'='*60}")
    print(f"Processed {len(html_files)}/{len(pdf_files)} PDFs successfully")

    return html_files


def main():
    parser = argparse.ArgumentParser(
        description="Convert NCAA baseball box score PDFs to Baseball Reference-style HTML"
    )

    parser.add_argument(
        "input",
        help="PDF file or directory (with --batch)"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all PDFs in a directory"
    )

    parser.add_argument(
        "--output-dir", "-o",
        default="html_output",
        help="Output directory (default: html_output)"
    )

    parser.add_argument(
        "--roster-dir", "-r",
        default="rosters",
        help="Directory with roster JSON files (default: rosters)"
    )

    parser.add_argument(
        "--keep-json",
        action="store_true",
        help="Keep intermediate JSON files"
    )

    parser.add_argument(
        "--scrape-rosters", "-s",
        action="store_true",
        help="Scrape rosters from Baseball Reference for teams in PDFs"
    )

    parser.add_argument(
        "--no-rosters",
        action="store_true",
        help="Skip roster matching entirely"
    )

    args = parser.parse_args()

    roster_dir = None if args.no_rosters else args.roster_dir

    if args.batch:
        process_batch(
            args.input,
            args.output_dir,
            roster_dir,
            args.keep_json,
            args.scrape_rosters
        )
    else:
        process_pdf(
            args.input,
            args.output_dir,
            roster_dir,
            args.keep_json,
            args.scrape_rosters
        )


if __name__ == "__main__":
    main()
