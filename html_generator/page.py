"""
Full HTML page generation for NCAA baseball box scores.

Contains the main generate_html_page function with CSS and page template,
along with conversion functions and CLI.
"""

import json
from pathlib import Path
from typing import Optional

from name_matcher import NameMatcher, enrich_game_data

from .components import (
    BREF_BASE,
    generate_batting_table,
    generate_pitching_table,
    generate_line_score,
    generate_game_notes,
    generate_game_info,
)


def generate_html_page(game_data: dict) -> str:
    """Generate complete HTML page for a game."""
    meta = game_data.get('metadata', {})
    box_score = game_data.get('box_score', {})

    away_team = meta.get('away_team', 'Away')
    home_team = meta.get('home_team', 'Home')
    away_score = meta.get('away_team_score', 0)
    home_score = meta.get('home_team_score', 0)
    away_rank = meta.get('away_team_rank', '')
    home_rank = meta.get('home_team_rank', '')

    # Format team names with ranks
    away_display = f"{away_rank + ' ' if away_rank else ''}{away_team}"
    home_display = f"{home_rank + ' ' if home_rank else ''}{home_team}"

    title = f"{away_display} vs {home_display} - Box Score"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            box-sizing: border-box;
        }}

        body {{
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
            padding: 24px;
            text-align: center;
        }}

        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 1.75rem;
        }}

        .score-display {{
            font-size: 2.5rem;
            font-weight: bold;
            margin: 16px 0;
        }}

        .score-display .away-score,
        .score-display .home-score {{
            display: inline-block;
            min-width: 60px;
        }}

        .score-display .vs {{
            margin: 0 20px;
            font-size: 1.5rem;
            opacity: 0.7;
        }}

        .game-info {{
            background: #f8f9fa;
            padding: 12px 24px;
            font-size: 0.875rem;
            color: #666;
            border-bottom: 1px solid #e0e0e0;
        }}

        .info-item {{
            margin-right: 8px;
        }}

        .content {{
            padding: 24px;
        }}

        .line-score-container {{
            margin-bottom: 24px;
            overflow-x: auto;
        }}

        .line-score-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}

        .line-score-table th,
        .line-score-table td {{
            padding: 8px 12px;
            text-align: center;
            border: 1px solid #ddd;
        }}

        .line-score-table th {{
            background: #f0f0f0;
            font-weight: 600;
        }}

        .line-score-table .team-cell {{
            text-align: left;
            font-weight: 600;
            min-width: 120px;
        }}

        .line-score-table .inning-cell {{
            min-width: 32px;
        }}

        .line-score-table .total-cell {{
            background: #f8f9fa;
            font-weight: 600;
            min-width: 40px;
        }}

        .box-scores {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}

        @media (max-width: 900px) {{
            .box-scores {{
                grid-template-columns: 1fr;
            }}
        }}

        .team-header {{
            background: #1e3a5f;
            color: white;
            padding: 10px 16px;
            margin: 0;
            font-size: 1rem;
            border-radius: 4px 4px 0 0;
        }}

        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
        }}

        .stats-table th,
        .stats-table td {{
            padding: 6px 8px;
            border: 1px solid #ddd;
        }}

        .stats-table th {{
            background: #f0f0f0;
            font-weight: 600;
            text-align: center;
        }}

        .stats-table .player-cell {{
            text-align: left;
            white-space: nowrap;
        }}

        .stats-table .pos-cell {{
            text-align: center;
            width: 40px;
        }}

        .stats-table .stat-cell {{
            text-align: center;
            width: 36px;
        }}

        .stats-table tbody tr:hover {{
            background: #f8f9fa;
        }}

        .stats-table .totals-row {{
            background: #f0f0f0;
        }}

        .player-link {{
            color: #1e40af;
            text-decoration: none;
        }}

        .player-link:hover {{
            text-decoration: underline;
        }}

        .game-notes {{
            background: #f8f9fa;
            padding: 16px;
            border-radius: 4px;
            margin-top: 24px;
        }}

        .game-notes h3 {{
            margin: 0 0 12px 0;
            font-size: 1rem;
            color: #1e3a5f;
        }}

        .game-notes p {{
            margin: 4px 0;
            font-size: 0.875rem;
        }}

        .pitching-section {{
            margin-top: 24px;
        }}

        .footer {{
            background: #f0f0f0;
            padding: 16px 24px;
            font-size: 0.75rem;
            color: #666;
            text-align: center;
        }}

        .footer a {{
            color: #1e40af;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{away_display} at {home_display}</h1>
            <div class="score-display">
                <span class="away-score">{away_score}</span>
                <span class="vs">-</span>
                <span class="home-score">{home_score}</span>
            </div>
        </div>

        {generate_game_info(game_data)}

        <div class="content">
            {generate_line_score(game_data)}

            <div class="box-scores">
                {generate_batting_table(box_score.get('away_batting', []), away_team, game_data.get('game_notes', {}).get('home_runs', []))}
                {generate_batting_table(box_score.get('home_batting', []), home_team, game_data.get('game_notes', {}).get('home_runs', []))}
            </div>

            <div class="pitching-section">
                <div class="box-scores">
                    {generate_pitching_table(box_score.get('away_pitching', []), away_team)}
                    {generate_pitching_table(box_score.get('home_pitching', []), home_team)}
                </div>
            </div>

            {generate_game_notes(game_data)}
        </div>

        <div class="footer">
            Generated from NCAA box score data.
            Player links go to <a href="{BREF_BASE}" target="_blank">Baseball-Reference.com</a>.
        </div>
    </div>
</body>
</html>"""


def convert_game_to_html(
    game_json_path: str,
    output_path: Optional[str] = None,
    roster_dir: Optional[str] = None
) -> str:
    """
    Convert a parsed game JSON file to HTML.

    Args:
        game_json_path: Path to the game JSON file
        output_path: Optional output path for HTML (default: same name with .html)
        roster_dir: Optional directory with roster files for player matching

    Returns:
        Path to the generated HTML file
    """
    # Load game data
    with open(game_json_path, 'r') as f:
        game_data = json.load(f)

    # Enrich with bref_ids if roster is available
    if roster_dir:
        matcher = NameMatcher()
        count = matcher.load_rosters_from_dir(roster_dir)
        if count > 0:
            print(f"Loaded {count} rosters for player matching")
            game_data = enrich_game_data(game_data, matcher)

    # Generate HTML
    html = generate_html_page(game_data)

    # Determine output path
    if output_path is None:
        output_path = str(Path(game_json_path).with_suffix('.html'))

    # Write HTML
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Generated HTML: {output_path}")
    return output_path


def convert_all_games(
    input_dir: str,
    output_dir: str,
    roster_dir: Optional[str] = None
) -> list:
    """
    Convert all game JSON files in a directory to HTML.

    Args:
        input_dir: Directory with game JSON files
        output_dir: Directory for HTML output
        roster_dir: Optional directory with roster files

    Returns:
        List of generated HTML file paths
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Load rosters once
    matcher = None
    if roster_dir:
        matcher = NameMatcher()
        count = matcher.load_rosters_from_dir(roster_dir)
        print(f"Loaded {count} rosters for player matching")

    html_files = []

    for json_file in sorted(input_path.glob("*.json")):
        print(f"Processing: {json_file.name}")

        # Load game data
        with open(json_file, 'r') as f:
            game_data = json.load(f)

        # Enrich with bref_ids
        if matcher:
            game_data = enrich_game_data(game_data, matcher)

        # Generate HTML
        html = generate_html_page(game_data)

        # Write HTML
        html_path = output_path / json_file.with_suffix('.html').name
        with open(html_path, 'w') as f:
            f.write(html)

        html_files.append(str(html_path))

    print(f"\nGenerated {len(html_files)} HTML files in {output_dir}")
    return html_files


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("NCAA Baseball HTML Generator")
        print("\nUsage:")
        print("  python -m html_generator.page <game.json> [output.html] [--roster-dir DIR]")
        print("  python -m html_generator.page --all <input_dir> <output_dir> [--roster-dir DIR]")
        print("\nExamples:")
        print("  python -m html_generator.page output/game1.json")
        print("  python -m html_generator.page output/game1.json game1.html --roster-dir rosters")
        print("  python -m html_generator.page --all output html_output --roster-dir rosters")
        sys.exit(1)

    roster_dir = None
    if "--roster-dir" in sys.argv:
        idx = sys.argv.index("--roster-dir")
        roster_dir = sys.argv[idx + 1]
        sys.argv = sys.argv[:idx] + sys.argv[idx + 2:]

    if sys.argv[1] == "--all":
        if len(sys.argv) < 4:
            print("Error: --all requires input_dir and output_dir")
            sys.exit(1)
        convert_all_games(sys.argv[2], sys.argv[3], roster_dir)
    else:
        game_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        convert_game_to_html(game_path, output_path, roster_dir)


if __name__ == "__main__":
    main()
