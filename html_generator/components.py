"""
HTML component generation for NCAA baseball box scores.

Contains functions to generate HTML tables and components for batting,
pitching, and other game statistics.
"""

from typing import Optional

from utils.names import normalize_name_for_matching, format_innings_pitched


BREF_BASE = "https://www.baseball-reference.com"


def generate_player_link(name: str, bref_id: Optional[str]) -> str:
    """Generate HTML for a player name with optional link."""
    if bref_id:
        url = f"{BREF_BASE}/register/player.fcgi?id={bref_id}"
        return f'<a href="{url}" target="_blank" class="player-link">{name}</a>'
    return f'<span class="player-name">{name}</span>'


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
