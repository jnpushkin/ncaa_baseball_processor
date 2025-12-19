#!/usr/bin/env python3
"""
NCAA Baseball HTML Generator

Generates Baseball Reference-style HTML pages from parsed box score data.
Includes player links to Baseball Reference register pages.
"""

import json
from pathlib import Path
from typing import Optional
from name_matcher import NameMatcher, enrich_game_data


BREF_BASE = "https://www.baseball-reference.com"


def generate_player_link(name: str, bref_id: Optional[str]) -> str:
    """Generate HTML for a player name with optional link."""
    if bref_id:
        url = f"{BREF_BASE}/register/player.fcgi?id={bref_id}"
        return f'<a href="{url}" target="_blank" class="player-link">{name}</a>'
    return f'<span class="player-name">{name}</span>'


def format_innings_pitched(ip: float) -> str:
    """Format innings pitched (e.g., 5.1, 5.2 for outs)."""
    whole = int(ip)
    fraction = ip - whole
    # Convert decimal to outs (0.1 = 1 out, 0.2 = 2 outs)
    if fraction < 0.15:
        outs = 0
    elif fraction < 0.4:
        outs = 1
    else:
        outs = 2
    return f"{whole}.{outs}"


def normalize_name_for_matching(name: str) -> str:
    """Normalize a player name for matching (lowercase, remove punctuation)."""
    import re
    # Convert to lowercase
    name = name.lower()
    # Remove common suffixes like ", J." or ", PJ"
    name = re.sub(r',\s*[a-z\.]+$', '', name)
    # Remove periods and extra spaces
    name = re.sub(r'\.', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_hr_counts_for_players(players: list, home_runs: list) -> dict:
    """
    Map home run counts from game_notes to players.

    Args:
        players: List of player dicts from batting lineup
        home_runs: List of HR entries from game_notes (dicts with 'player', 'game_count')

    Returns:
        Dict mapping player name (normalized) to HR count in this game
    """
    hr_counts = {}

    for hr in home_runs:
        if isinstance(hr, dict):
            player_name = hr.get('player', '')
            game_count = hr.get('game_count', 1)
        else:
            player_name = str(hr)
            game_count = 1

        # Normalize the name for matching
        normalized = normalize_name_for_matching(player_name)
        hr_counts[normalized] = game_count

    return hr_counts


def match_player_hr(player: dict, hr_counts: dict) -> int:
    """Find HR count for a player by matching names."""
    # Get player name from either full_name or name field
    player_name = player.get('full_name') or player.get('name', '')
    normalized = normalize_name_for_matching(player_name)

    # Direct match
    if normalized in hr_counts:
        return hr_counts[normalized]

    # Try last name only match
    last_name = normalized.split()[-1] if normalized else ''
    for hr_name, count in hr_counts.items():
        # Check if last names match
        hr_last = hr_name.split()[-1] if hr_name else ''
        if last_name and hr_last and last_name == hr_last:
            return count

    return 0


def generate_batting_table(players: list, team_name: str, home_runs: list = None) -> str:
    """Generate HTML batting table for a team."""
    if not players:
        return ""

    # Build HR lookup from game notes
    hr_counts = get_hr_counts_for_players(players, home_runs or [])

    rows = []
    totals = {
        'ab': 0, 'r': 0, 'h': 0, 'rbi': 0, 'bb': 0, 'k': 0, 'hr': 0, 'po': 0, 'a': 0, 'lob': 0
    }

    for p in players:
        name_html = generate_player_link(
            p.get('full_name') or p.get('name', ''),
            p.get('bref_id')
        )

        # Get stats
        ab = p.get('at_bats', 0)
        r = p.get('runs', 0)
        h = p.get('hits', 0)
        rbi = p.get('rbi', 0)
        bb = p.get('walks', 0)
        k = p.get('strikeouts', 0)
        hr = match_player_hr(p, hr_counts)
        po = p.get('put_outs', 0)
        a = p.get('assists', 0)
        lob = p.get('left_on_base', 0)

        # Update totals
        totals['ab'] += ab
        totals['r'] += r
        totals['h'] += h
        totals['rbi'] += rbi
        totals['bb'] += bb
        totals['k'] += k
        totals['hr'] += hr
        totals['po'] += po
        totals['a'] += a
        totals['lob'] += lob

        pos = p.get('position', '')
        num = p.get('number', '')

        rows.append(f"""
            <tr>
                <td class="player-cell">{num}</td>
                <td class="player-cell">{name_html}</td>
                <td class="pos-cell">{pos}</td>
                <td class="stat-cell">{ab}</td>
                <td class="stat-cell">{r}</td>
                <td class="stat-cell">{h}</td>
                <td class="stat-cell">{hr}</td>
                <td class="stat-cell">{rbi}</td>
                <td class="stat-cell">{bb}</td>
                <td class="stat-cell">{k}</td>
                <td class="stat-cell">{po}</td>
                <td class="stat-cell">{a}</td>
                <td class="stat-cell">{lob}</td>
            </tr>
        """)

    # Totals row
    rows.append(f"""
        <tr class="totals-row">
            <td class="player-cell"></td>
            <td class="player-cell"><strong>Totals</strong></td>
            <td class="pos-cell"></td>
            <td class="stat-cell"><strong>{totals['ab']}</strong></td>
            <td class="stat-cell"><strong>{totals['r']}</strong></td>
            <td class="stat-cell"><strong>{totals['h']}</strong></td>
            <td class="stat-cell"><strong>{totals['hr']}</strong></td>
            <td class="stat-cell"><strong>{totals['rbi']}</strong></td>
            <td class="stat-cell"><strong>{totals['bb']}</strong></td>
            <td class="stat-cell"><strong>{totals['k']}</strong></td>
            <td class="stat-cell"><strong>{totals['po']}</strong></td>
            <td class="stat-cell"><strong>{totals['a']}</strong></td>
            <td class="stat-cell"><strong>{totals['lob']}</strong></td>
        </tr>
    """)

    return f"""
    <div class="team-batting">
        <h3 class="team-header">{team_name} Batting</h3>
        <table class="stats-table batting-table">
            <thead>
                <tr>
                    <th class="player-cell">#</th>
                    <th class="player-cell">Player</th>
                    <th class="pos-cell">Pos</th>
                    <th class="stat-cell">AB</th>
                    <th class="stat-cell">R</th>
                    <th class="stat-cell">H</th>
                    <th class="stat-cell">HR</th>
                    <th class="stat-cell">RBI</th>
                    <th class="stat-cell">BB</th>
                    <th class="stat-cell">K</th>
                    <th class="stat-cell">PO</th>
                    <th class="stat-cell">A</th>
                    <th class="stat-cell">LOB</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """


def generate_pitching_table(pitchers: list, team_name: str) -> str:
    """Generate HTML pitching table for a team."""
    if not pitchers:
        return ""

    rows = []
    totals = {
        'ip': 0, 'h': 0, 'r': 0, 'er': 0, 'bb': 0, 'k': 0, 'bf': 0, 'np': 0
    }

    for p in pitchers:
        name_html = generate_player_link(
            p.get('full_name') or p.get('name', ''),
            p.get('bref_id')
        )

        ip = p.get('innings_pitched', 0)
        h = p.get('hits', 0)
        r = p.get('runs', 0)
        er = p.get('earned_runs', 0)
        bb = p.get('walks', 0)
        k = p.get('strikeouts', 0)
        bf = p.get('batters_faced', 0)
        np = p.get('pitches', 0)

        totals['ip'] += ip
        totals['h'] += h
        totals['r'] += r
        totals['er'] += er
        totals['bb'] += bb
        totals['k'] += k
        totals['bf'] += bf
        totals['np'] += np

        num = p.get('number', '')

        rows.append(f"""
            <tr>
                <td class="player-cell">{num}</td>
                <td class="player-cell">{name_html}</td>
                <td class="stat-cell">{format_innings_pitched(ip)}</td>
                <td class="stat-cell">{h}</td>
                <td class="stat-cell">{r}</td>
                <td class="stat-cell">{er}</td>
                <td class="stat-cell">{bb}</td>
                <td class="stat-cell">{k}</td>
                <td class="stat-cell">{bf}</td>
                <td class="stat-cell">{np}</td>
            </tr>
        """)

    rows.append(f"""
        <tr class="totals-row">
            <td class="player-cell"></td>
            <td class="player-cell"><strong>Totals</strong></td>
            <td class="stat-cell"><strong>{format_innings_pitched(totals['ip'])}</strong></td>
            <td class="stat-cell"><strong>{totals['h']}</strong></td>
            <td class="stat-cell"><strong>{totals['r']}</strong></td>
            <td class="stat-cell"><strong>{totals['er']}</strong></td>
            <td class="stat-cell"><strong>{totals['bb']}</strong></td>
            <td class="stat-cell"><strong>{totals['k']}</strong></td>
            <td class="stat-cell"><strong>{totals['bf']}</strong></td>
            <td class="stat-cell"><strong>{totals['np']}</strong></td>
        </tr>
    """)

    return f"""
    <div class="team-pitching">
        <h3 class="team-header">{team_name} Pitching</h3>
        <table class="stats-table pitching-table">
            <thead>
                <tr>
                    <th class="player-cell">#</th>
                    <th class="player-cell">Pitcher</th>
                    <th class="stat-cell">IP</th>
                    <th class="stat-cell">H</th>
                    <th class="stat-cell">R</th>
                    <th class="stat-cell">ER</th>
                    <th class="stat-cell">BB</th>
                    <th class="stat-cell">K</th>
                    <th class="stat-cell">BF</th>
                    <th class="stat-cell">NP</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """


def generate_line_score(game_data: dict) -> str:
    """Generate the line score (score by innings) table."""
    meta = game_data.get('metadata', {})
    line_score = game_data.get('box_score', {}).get('line_score', {})

    away_team = meta.get('away_team', 'Away')
    home_team = meta.get('home_team', 'Home')
    away_innings = line_score.get('away_innings', [])
    home_innings = line_score.get('home_innings', [])

    # Calculate totals
    away_r = meta.get('away_team_score', sum(away_innings))
    home_r = meta.get('home_team_score', sum(home_innings))

    # Get hits from box score
    away_h = sum(p.get('hits', 0) for p in game_data.get('box_score', {}).get('away_batting', []))
    home_h = sum(p.get('hits', 0) for p in game_data.get('box_score', {}).get('home_batting', []))

    # Get errors from game notes
    errors = game_data.get('game_notes', {}).get('errors', [])
    away_e = len([e for e in errors if away_team.lower() in str(e).lower()])
    home_e = len(errors) - away_e  # Simple approximation

    # Generate inning headers
    num_innings = max(len(away_innings), len(home_innings), 9)
    inning_headers = ''.join(f'<th class="inning-cell">{i+1}</th>' for i in range(num_innings))

    # Generate inning cells
    away_cells = ''.join(
        f'<td class="inning-cell">{away_innings[i] if i < len(away_innings) else "-"}</td>'
        for i in range(num_innings)
    )
    home_cells = ''.join(
        f'<td class="inning-cell">{home_innings[i] if i < len(home_innings) else "X" if i == num_innings - 1 and len(home_innings) < num_innings else "-"}</td>'
        for i in range(num_innings)
    )

    return f"""
    <div class="line-score-container">
        <table class="line-score-table">
            <thead>
                <tr>
                    <th class="team-cell">Team</th>
                    {inning_headers}
                    <th class="total-cell">R</th>
                    <th class="total-cell">H</th>
                    <th class="total-cell">E</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="team-cell">{away_team}</td>
                    {away_cells}
                    <td class="total-cell"><strong>{away_r}</strong></td>
                    <td class="total-cell">{away_h}</td>
                    <td class="total-cell">{away_e}</td>
                </tr>
                <tr>
                    <td class="team-cell">{home_team}</td>
                    {home_cells}
                    <td class="total-cell"><strong>{home_r}</strong></td>
                    <td class="total-cell">{home_h}</td>
                    <td class="total-cell">{home_e}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """


def generate_game_notes(game_data: dict) -> str:
    """Generate the game notes section (2B, 3B, HR, etc.)."""
    notes = game_data.get('game_notes', {})
    sections = []

    # Doubles
    if notes.get('doubles'):
        items = [d.get('player', d) if isinstance(d, dict) else d for d in notes['doubles']]
        sections.append(f"<p><strong>2B:</strong> {'; '.join(str(i) for i in items)}</p>")

    # Triples
    if notes.get('triples'):
        sections.append(f"<p><strong>3B:</strong> {'; '.join(str(t) for t in notes['triples'])}</p>")

    # Home runs
    if notes.get('home_runs'):
        items = []
        for hr in notes['home_runs']:
            if isinstance(hr, dict):
                player = hr.get('player', '')
                count = hr.get('game_count', 1)
                season = hr.get('season_total', '')
                items.append(f"{player}{' ' + str(count) if count > 1 else ''}{' (' + str(season) + ')' if season else ''}")
            else:
                items.append(str(hr))
        sections.append(f"<p><strong>HR:</strong> {'; '.join(items)}</p>")

    # Stolen bases
    if notes.get('stolen_bases'):
        sections.append(f"<p><strong>SB:</strong> {'; '.join(str(sb) for sb in notes['stolen_bases'])}</p>")

    # Errors
    if notes.get('errors'):
        sections.append(f"<p><strong>E:</strong> {'; '.join(str(e) for e in notes['errors'])}</p>")

    # Win/Loss/Save
    if notes.get('win'):
        w = notes['win']
        sections.append(f"<p><strong>Win:</strong> {w.get('player', '')} ({w.get('record', '')})</p>")

    if notes.get('loss'):
        l = notes['loss']
        sections.append(f"<p><strong>Loss:</strong> {l.get('player', '')} ({l.get('record', '')})</p>")

    if notes.get('save'):
        s = notes['save']
        sections.append(f"<p><strong>Save:</strong> {s.get('player', '')} ({s.get('count', '')})</p>")

    if not sections:
        return ""

    return f"""
    <div class="game-notes">
        <h3>Game Notes</h3>
        {''.join(sections)}
    </div>
    """


def generate_game_info(game_data: dict) -> str:
    """Generate game metadata section."""
    meta = game_data.get('metadata', {})

    info_items = []

    if meta.get('date'):
        info_items.append(f"<span class='info-item'><strong>Date:</strong> {meta['date']}</span>")

    if meta.get('venue'):
        info_items.append(f"<span class='info-item'><strong>Venue:</strong> {meta['venue']}</span>")

    if meta.get('attendance'):
        info_items.append(f"<span class='info-item'><strong>Attendance:</strong> {meta['attendance']:,}</span>")

    if meta.get('duration'):
        info_items.append(f"<span class='info-item'><strong>Duration:</strong> {meta['duration']}</span>")

    if meta.get('weather'):
        info_items.append(f"<span class='info-item'><strong>Weather:</strong> {meta['weather']}</span>")

    return f"""
    <div class="game-info">
        {' | '.join(info_items)}
    </div>
    """


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


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("NCAA Baseball HTML Generator")
        print("\nUsage:")
        print("  python ncaab_html_generator.py <game.json> [output.html] [--roster-dir DIR]")
        print("  python ncaab_html_generator.py --all <input_dir> <output_dir> [--roster-dir DIR]")
        print("\nExamples:")
        print("  python ncaab_html_generator.py output/game1.json")
        print("  python ncaab_html_generator.py output/game1.json game1.html --roster-dir rosters")
        print("  python ncaab_html_generator.py --all output html_output --roster-dir rosters")
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
