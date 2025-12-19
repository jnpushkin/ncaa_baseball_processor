#!/usr/bin/env python3
"""
Generate the NCAA Baseball viewer HTML with embedded game data.
"""

import os
import json
import re
from pathlib import Path


def load_game_data(output_dir: str = "output") -> list:
    """Load all JSON game files from the output directory."""
    games = []
    output_path = Path(output_dir)

    if not output_path.exists():
        print(f"Output directory '{output_dir}' not found.")
        return games

    for json_file in sorted(output_path.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                game_data = json.load(f)
                game_data['filename'] = json_file.name
                games.append(game_data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {json_file}: {e}")

    # Sort by date (most recent first)
    games.sort(key=lambda g: g.get('metadata', {}).get('date', ''), reverse=True)

    return games


def generate_viewer_html(games: list, template_path: str = "ncaab_viewer.html", output_path: str = "ncaab_stats.html") -> str:
    """Generate the final viewer HTML with embedded game data."""

    # Read the template
    with open(template_path, 'r') as f:
        template = f.read()

    # Create the data object
    data = {"games": games}
    data_json = json.dumps(data, indent=2)

    # Replace the placeholder data with actual data
    pattern = r'const NCAAB_DATA = \{games: \[\]\};'
    replacement = f'const NCAAB_DATA = {data_json};'

    html = re.sub(pattern, replacement, template)

    # Write the output
    with open(output_path, 'w') as f:
        f.write(html)

    return output_path


def main():
    """Main function to generate the viewer."""
    print("Loading game data...")
    games = load_game_data()
    print(f"Loaded {len(games)} games")

    if not games:
        print("No games found. Make sure to run the parser first.")
        return

    # Print summary
    teams = set()
    for g in games:
        meta = g.get('metadata', {})
        if meta.get('away_team'):
            teams.add(meta['away_team'])
        if meta.get('home_team'):
            teams.add(meta['home_team'])

    print(f"Teams: {', '.join(sorted(teams))}")

    # Generate the HTML
    output_file = generate_viewer_html(games)
    print(f"\nGenerated viewer: {output_file}")
    print(f"Open in browser: file://{os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()
