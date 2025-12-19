"""
Website generator for interactive HTML output.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

from ..utils.stadiums import STADIUM_DATA
from ..utils.constants import CONFERENCES, get_conference
from ..utils.helpers import normalize_team_name


def generate_website_from_data(processed_data: Dict[str, Any], output_path: str, raw_games: List[Dict] = None):
    """
    Generate interactive HTML website from processed data.

    Args:
        processed_data: Dictionary containing processed DataFrames
        output_path: Path to save the HTML file
        raw_games: Optional list of raw game data for additional details
    """
    print(f"Generating website: {output_path}")

    # Serialize data for JavaScript
    data = _serialize_data(processed_data, raw_games or [])
    json_data = json.dumps(data, default=str)

    # Generate HTML
    html_content = _generate_html(json_data, data.get('summary', {}))

    # Write file
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Website saved: {output_path}")


def _serialize_data(processed_data: Dict[str, Any], raw_games: List[Dict]) -> Dict[str, Any]:
    """Convert DataFrames to JSON-serializable format."""

    def df_to_list(df):
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return []
        if isinstance(df, pd.DataFrame):
            return df.to_dict('records')
        return df

    # Calculate summary stats
    game_log = processed_data.get('game_log', pd.DataFrame())
    batters = processed_data.get('batters', pd.DataFrame())
    pitchers = processed_data.get('pitchers', pd.DataFrame())
    team_records = processed_data.get('team_records', pd.DataFrame())

    total_games = len(game_log) if isinstance(game_log, pd.DataFrame) else 0
    total_batters = len(batters) if isinstance(batters, pd.DataFrame) else 0
    total_pitchers = len(pitchers) if isinstance(pitchers, pd.DataFrame) else 0
    total_teams = len(team_records) if isinstance(team_records, pd.DataFrame) else 0

    # Milestone counts
    milestones = processed_data.get('milestones', {})
    hr_games_count = len(milestones.get('hr_games', []))
    ten_k_count = len(milestones.get('ten_k_games', []))

    # Build stadium locations for map
    stadium_locations = {}
    for team, info in STADIUM_DATA.items():
        lat, lng, stadium_name = info
        stadium_locations[team] = {'lat': lat, 'lng': lng, 'stadium': stadium_name}

    # Build checklist data - track which teams/venues have been seen
    teams_seen_home = set()  # Teams seen at their actual home stadium
    teams_seen_away = set()  # Teams seen but not at their home stadium
    venues_visited = set()    # Venues we've been to

    def normalize_venue(name):
        """Normalize venue name for matching."""
        name = name.lower()
        # Common abbreviations
        name = name.replace('muni ', 'municipal ')
        name = name.replace(' at ', ' ')
        # Remove parenthetical city/state info
        if '(' in name:
            name = name.split('(')[0].strip()
        return name

    def venues_match(stadium_name, venue_name):
        """Check if a venue matches a stadium name."""
        stadium = normalize_venue(stadium_name)
        venue = normalize_venue(venue_name)

        # Direct containment check
        if stadium in venue or venue in stadium:
            return True

        # Check if key words match (for partial names like "Benedetti Diamond")
        stadium_words = set(stadium.split())
        venue_words = set(venue.split())
        # Remove common words
        common = {'field', 'stadium', 'park', 'ballpark', 'diamond', 'at', 'the'}
        stadium_key = stadium_words - common
        venue_key = venue_words - common

        # If 2+ key words match, consider it a match
        if len(stadium_key & venue_key) >= 2:
            return True

        # Check if the main distinctive word matches
        for word in stadium_key:
            if len(word) > 4 and word in venue:  # Significant word
                return True

        return False

    # Build a mapping of team -> home stadium name for matching
    team_stadiums = {}
    for team, info in STADIUM_DATA.items():
        stadium_name = info[2] if len(info) > 2 else ''
        team_stadiums[team] = stadium_name

    for game in raw_games:
        meta = game.get('metadata', {})
        home_team = normalize_team_name(meta.get('home_team', ''))
        away_team = normalize_team_name(meta.get('away_team', ''))
        venue = meta.get('venue', '')

        if venue:
            venues_visited.add(venue)

        # Check if venue matches the team's actual stadium
        home_stadium = team_stadiums.get(home_team, '')
        away_stadium = team_stadiums.get(away_team, '')

        # A team is "visited" only if we were at their actual home stadium
        if home_team:
            if home_stadium and venues_match(home_stadium, venue):
                teams_seen_home.add(home_team)
            else:
                # Neutral site - just mark as seen (away)
                teams_seen_away.add(home_team)

        if away_team:
            if away_stadium and venues_match(away_stadium, venue):
                teams_seen_home.add(away_team)
            else:
                teams_seen_away.add(away_team)

    # Build conference checklist
    checklist = {}
    for conf, teams in CONFERENCES.items():
        seen = len([t for t in teams if t in teams_seen_home or t in teams_seen_away])
        visited = len([t for t in teams if t in teams_seen_home])
        checklist[conf] = {
            'teams': teams,
            'total': len(teams),
            'seen': seen,
            'visited': visited,
            'teamStatus': {t: 'home' if t in teams_seen_home else ('away' if t in teams_seen_away else 'none') for t in teams}
        }

    # Get game-by-game data for players
    batter_games = processed_data.get('batter_games', pd.DataFrame())
    pitcher_games = processed_data.get('pitcher_games', pd.DataFrame())

    return {
        'summary': {
            'totalGames': total_games,
            'totalBatters': total_batters,
            'totalPitchers': total_pitchers,
            'totalTeams': total_teams,
            'hrGames': hr_games_count,
            'tenKGames': ten_k_count,
        },
        'gameLog': df_to_list(game_log),
        'batters': df_to_list(batters),
        'pitchers': df_to_list(pitchers),
        'batterGames': df_to_list(batter_games),
        'pitcherGames': df_to_list(pitcher_games),
        'teamRecords': df_to_list(team_records),
        'milestones': {
            'multiHrGames': df_to_list(milestones.get('multi_hr_games', [])),
            'hrGames': df_to_list(milestones.get('hr_games', [])),
            'fourHitGames': df_to_list(milestones.get('four_hit_games', [])),
            'threeHitGames': df_to_list(milestones.get('three_hit_games', [])),
            'fiveRbiGames': df_to_list(milestones.get('five_rbi_games', [])),
            'fourRbiGames': df_to_list(milestones.get('four_rbi_games', [])),
            'threeRbiGames': df_to_list(milestones.get('three_rbi_games', [])),
            'multiSbGames': df_to_list(milestones.get('multi_sb_games', [])),
            'cycleWatch': df_to_list(milestones.get('cycle_watch', [])),
            'tenKGames': df_to_list(milestones.get('ten_k_games', [])),
            'qualityStarts': df_to_list(milestones.get('quality_starts', [])),
            'completeGames': df_to_list(milestones.get('complete_games', [])),
            'shutouts': df_to_list(milestones.get('shutouts', [])),
            'noHitters': df_to_list(milestones.get('no_hitters', [])),
        },
        'rawGames': raw_games,
        'stadiumLocations': stadium_locations,
        'checklist': checklist,
        'teamsSeenHome': list(teams_seen_home),
        'teamsSeenAway': list(teams_seen_away),
        'venuesVisited': list(venues_visited),
    }


def _generate_html(json_data: str, summary: Dict[str, Any]) -> str:
    """Generate the HTML content."""

    total_games = summary.get('totalGames', 0)
    total_batters = summary.get('totalBatters', 0)
    total_pitchers = summary.get('totalPitchers', 0)
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCAA Baseball Statistics</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        :root {{
            --bg-primary: #f5f5f5;
            --bg-secondary: #ffffff;
            --bg-header: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            --text-primary: #333333;
            --text-secondary: #666666;
            --accent-color: #1e3a5f;
            --accent-light: #e8f0fe;
            --border-color: #e0e0e0;
            --hover-color: #f8f9fa;
        }}

        * {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 0;
            background: var(--bg-primary);
            color: var(--text-primary);
        }}

        .header {{
            background: var(--bg-header);
            color: white;
            padding: 24px;
            text-align: center;
        }}

        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 1.75rem;
        }}

        .header p {{
            margin: 0;
            opacity: 0.8;
            font-size: 0.875rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .stat-card {{
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .stat-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent-color);
        }}

        .stat-card .label {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}

        .tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}

        .tab {{
            padding: 10px 20px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.2s;
        }}

        .tab:hover {{
            background: var(--hover-color);
        }}

        .tab.active {{
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }}

        .panel {{
            background: var(--bg-secondary);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .panel-header {{
            background: var(--accent-light);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
        }}

        .panel-header h2 {{
            margin: 0;
            font-size: 1.125rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}

        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
            cursor: pointer;
            user-select: none;
        }}

        th:hover {{
            background: #e9ecef;
        }}

        th .sort-indicator {{
            margin-left: 4px;
            opacity: 0.5;
        }}

        th.sorted .sort-indicator {{
            opacity: 1;
        }}

        tr:hover {{
            background: var(--hover-color);
        }}

        .text-center {{
            text-align: center;
        }}

        .text-right {{
            text-align: right;
        }}

        .player-link {{
            color: var(--accent-color);
            text-decoration: none;
        }}

        .player-link:hover {{
            text-decoration: underline;
        }}

        .search-box {{
            padding: 10px 16px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 0.875rem;
            width: 100%;
            max-width: 300px;
            margin-bottom: 16px;
        }}

        .table-container {{
            overflow-x: auto;
            max-height: 600px;
            overflow-y: auto;
        }}

        .footer {{
            text-align: center;
            padding: 24px;
            color: var(--text-secondary);
            font-size: 0.75rem;
        }}

        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}

        .modal-content {{
            background: white;
            border-radius: 12px;
            max-width: 900px;
            max-height: 80vh;
            width: 90%;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}

        .modal-header {{
            background: var(--bg-header);
            color: white;
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-header h3 {{
            margin: 0;
            font-size: 1.25rem;
        }}

        .modal-close {{
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }}

        .modal-body {{
            padding: 20px;
            overflow-y: auto;
            max-height: calc(80vh - 60px);
        }}

        .clickable-name {{
            color: var(--accent-color);
            cursor: pointer;
            text-decoration: none;
        }}

        .clickable-name:hover {{
            text-decoration: underline;
        }}

        .player-summary {{
            display: flex;
            gap: 24px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}

        .player-summary-stat {{
            text-align: center;
        }}

        .player-summary-stat .value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent-color);
        }}

        .player-summary-stat .label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NCAA Baseball Statistics</h1>
        <p>{total_games} Games | {total_batters} Batters | {total_pitchers} Pitchers | Generated {generated_time}</p>
    </div>

    <div id="root"></div>

    <script>
        const DATA = {json_data};
    </script>

    <script type="text/babel">
        const {{ useState, useMemo, useRef, useEffect }} = React;

        const BREF_BASE = "https://www.baseball-reference.com/register/player.fcgi?id=";

        // Custom hook for sortable tables
        const useSortableData = (items, defaultSort = null) => {{
            const [sortConfig, setSortConfig] = useState(defaultSort);

            const sortedItems = useMemo(() => {{
                if (!sortConfig || !items) return items;
                const sorted = [...items].sort((a, b) => {{
                    let aVal = a[sortConfig.key];
                    let bVal = b[sortConfig.key];

                    // Handle numeric values
                    if (typeof aVal === 'number' && typeof bVal === 'number') {{
                        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
                    }}

                    // Handle string values that look like numbers
                    const aNum = parseFloat(aVal);
                    const bNum = parseFloat(bVal);
                    if (!isNaN(aNum) && !isNaN(bNum)) {{
                        return sortConfig.direction === 'asc' ? aNum - bNum : bNum - aNum;
                    }}

                    // Handle date-like strings (M/D/YYYY)
                    if (sortConfig.key === 'Date' || sortConfig.key === 'DateSort') {{
                        const parseDate = (d) => {{
                            if (!d) return 0;
                            const parts = d.split('/');
                            if (parts.length === 3) {{
                                return new Date(parts[2], parts[0] - 1, parts[1]).getTime();
                            }}
                            return 0;
                        }};
                        const aDate = parseDate(aVal);
                        const bDate = parseDate(bVal);
                        return sortConfig.direction === 'asc' ? aDate - bDate : bDate - aDate;
                    }}

                    // String comparison
                    aVal = String(aVal || '').toLowerCase();
                    bVal = String(bVal || '').toLowerCase();
                    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
                    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
                    return 0;
                }});
                return sorted;
            }}, [items, sortConfig]);

            const requestSort = (key) => {{
                let direction = 'asc';
                if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {{
                    direction = 'desc';
                }}
                setSortConfig({{ key, direction }});
            }};

            return {{ items: sortedItems, sortConfig, requestSort }};
        }};

        const SortableHeader = ({{ label, sortKey, sortConfig, onSort }}) => {{
            const isActive = sortConfig && sortConfig.key === sortKey;
            return (
                <th onClick={{() => onSort(sortKey)}} className={{isActive ? 'sorted' : ''}}>
                    {{label}}
                    <span className="sort-indicator">
                        {{isActive ? (sortConfig.direction === 'asc' ? '▲' : '▼') : '⇅'}}
                    </span>
                </th>
            );
        }};

        const PlayerLink = ({{ name, brefId, onClick }}) => {{
            return (
                <span className="clickable-name" onClick={{onClick}}>
                    {{name}}
                    {{brefId && <a href={{BREF_BASE + brefId}} target="_blank" onClick={{(e) => e.stopPropagation()}} style={{{{marginLeft: '4px', fontSize: '10px'}}}}>↗</a>}}
                </span>
            );
        }};

        const PlayerModal = ({{ player, games, type, onClose }}) => {{
            if (!player) return null;

            const isBatter = type === 'batter';

            return (
                <div className="modal-overlay" onClick={{onClose}}>
                    <div className="modal-content" onClick={{(e) => e.stopPropagation()}}>
                        <div className="modal-header">
                            <h3>{{player.Name}} - {{player.Team}}</h3>
                            <button className="modal-close" onClick={{onClose}}>&times;</button>
                        </div>
                        <div className="modal-body">
                            <div className="player-summary">
                                {{isBatter ? (
                                    <>
                                        <div className="player-summary-stat"><div className="value">{{player.G}}</div><div className="label">Games</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.AVG}}</div><div className="label">AVG</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.H}}</div><div className="label">Hits</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.HR}}</div><div className="label">HR</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.RBI}}</div><div className="label">RBI</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.OPS}}</div><div className="label">OPS</div></div>
                                    </>
                                ) : (
                                    <>
                                        <div className="player-summary-stat"><div className="value">{{player.G}}</div><div className="label">Games</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.IP}}</div><div className="label">IP</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.ERA}}</div><div className="label">ERA</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.K}}</div><div className="label">K</div></div>
                                        <div className="player-summary-stat"><div className="value">{{player.WHIP}}</div><div className="label">WHIP</div></div>
                                    </>
                                )}}
                            </div>

                            <h4 style={{{{marginBottom: '12px'}}}}>Game Log</h4>
                            <div className="table-container" style={{{{maxHeight: '400px'}}}}>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Opp</th>
                                            {{isBatter ? (
                                                <>
                                                    <th>AB</th>
                                                    <th>R</th>
                                                    <th>H</th>
                                                    <th>2B</th>
                                                    <th>HR</th>
                                                    <th>RBI</th>
                                                    <th>BB</th>
                                                    <th>K</th>
                                                </>
                                            ) : (
                                                <>
                                                    <th>IP</th>
                                                    <th>H</th>
                                                    <th>R</th>
                                                    <th>ER</th>
                                                    <th>BB</th>
                                                    <th>K</th>
                                                </>
                                            )}}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {{games.map((g, i) => (
                                            <tr key={{i}}>
                                                <td>{{g.date}}</td>
                                                <td>{{g.opponent}}</td>
                                                {{isBatter ? (
                                                    <>
                                                        <td className="text-center">{{g.ab}}</td>
                                                        <td className="text-center">{{g.r}}</td>
                                                        <td className="text-center">{{g.h}}</td>
                                                        <td className="text-center">{{g.doubles || 0}}</td>
                                                        <td className="text-center">{{g.hr || 0}}</td>
                                                        <td className="text-center">{{g.rbi}}</td>
                                                        <td className="text-center">{{g.bb}}</td>
                                                        <td className="text-center">{{g.k}}</td>
                                                    </>
                                                ) : (
                                                    <>
                                                        <td className="text-center">{{g.ip}}</td>
                                                        <td className="text-center">{{g.h}}</td>
                                                        <td className="text-center">{{g.r}}</td>
                                                        <td className="text-center">{{g.er}}</td>
                                                        <td className="text-center">{{g.bb}}</td>
                                                        <td className="text-center">{{g.k}}</td>
                                                    </>
                                                )}}
                                            </tr>
                                        ))}}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }};

        const StatsGrid = ({{ data }}) => (
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="value">{{data.totalGames}}</div>
                    <div className="label">Games</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.totalBatters}}</div>
                    <div className="label">Batters</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.totalPitchers}}</div>
                    <div className="label">Pitchers</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.totalTeams}}</div>
                    <div className="label">Teams</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.hrGames}}</div>
                    <div className="label">HR Games</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.tenKGames}}</div>
                    <div className="label">10+ K Games</div>
                </div>
            </div>
        );

        const GameLog = ({{ games }}) => {{
            const {{ items, sortConfig, requestSort }} = useSortableData(games, {{ key: 'Date', direction: 'desc' }});

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Game Log</h2></div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Date" sortKey="Date" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Away" sortKey="Away" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <th className="text-center">Score</th>
                                    <SortableHeader label="Home" sortKey="Home" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Venue" sortKey="Venue" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                </tr>
                            </thead>
                            <tbody>
                                {{items.map((g, i) => (
                                    <tr key={{i}}>
                                        <td>{{g.Date}}</td>
                                        <td>{{g.Away}}</td>
                                        <td className="text-center">{{g['Away Score']}} - {{g['Home Score']}}</td>
                                        <td>{{g.Home}}</td>
                                        <td>{{g.Venue}}</td>
                                    </tr>
                                ))}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const BattersTable = ({{ batters, search, confFilter, onPlayerClick }}) => {{
            const filtered = useMemo(() => {{
                let result = batters;
                if (confFilter && confFilter !== 'All') {{
                    result = result.filter(b => b.Conference?.includes(confFilter));
                }}
                if (search) {{
                    const s = search.toLowerCase();
                    result = result.filter(b =>
                        b.Name?.toLowerCase().includes(s) ||
                        b.Team?.toLowerCase().includes(s)
                    );
                }}
                return result;
            }}, [batters, search, confFilter]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'H', direction: 'desc' }});

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Batting Leaders ({{filtered.length}})</h2></div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Name" sortKey="Name" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Team" sortKey="Team" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Conf" sortKey="Conference" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="G" sortKey="G" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="AB" sortKey="AB" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="R" sortKey="R" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="H" sortKey="H" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="2B" sortKey="2B" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="HR" sortKey="HR" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="RBI" sortKey="RBI" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="BB" sortKey="BB" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="K" sortKey="K" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="AVG" sortKey="AVG" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="OBP" sortKey="OBP" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="SLG" sortKey="SLG" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                </tr>
                            </thead>
                            <tbody>
                                {{items.slice(0, 100).map((b, i) => (
                                    <tr key={{i}}>
                                        <td><PlayerLink name={{b.Name}} brefId={{b.bref_id}} onClick={{() => onPlayerClick(b, 'batter')}} /></td>
                                        <td>{{b.Team}}</td>
                                        <td>{{b.Conference}}</td>
                                        <td className="text-center">{{b.G}}</td>
                                        <td className="text-center">{{b.AB}}</td>
                                        <td className="text-center">{{b.R}}</td>
                                        <td className="text-center">{{b.H}}</td>
                                        <td className="text-center">{{b['2B']}}</td>
                                        <td className="text-center">{{b.HR}}</td>
                                        <td className="text-center">{{b.RBI}}</td>
                                        <td className="text-center">{{b.BB}}</td>
                                        <td className="text-center">{{b.K}}</td>
                                        <td className="text-center">{{b.AVG}}</td>
                                        <td className="text-center">{{b.OBP}}</td>
                                        <td className="text-center">{{b.SLG}}</td>
                                    </tr>
                                ))}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const PitchersTable = ({{ pitchers, search, confFilter, onPlayerClick }}) => {{
            const filtered = useMemo(() => {{
                let result = pitchers;
                if (confFilter && confFilter !== 'All') {{
                    result = result.filter(p => p.Conference?.includes(confFilter));
                }}
                if (search) {{
                    const s = search.toLowerCase();
                    result = result.filter(p =>
                        p.Name?.toLowerCase().includes(s) ||
                        p.Team?.toLowerCase().includes(s)
                    );
                }}
                return result;
            }}, [pitchers, search, confFilter]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'K', direction: 'desc' }});

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Pitching Leaders ({{filtered.length}})</h2></div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Name" sortKey="Name" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Team" sortKey="Team" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Conf" sortKey="Conference" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="G" sortKey="G" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="IP" sortKey="IP" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="H" sortKey="H" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="R" sortKey="R" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="ER" sortKey="ER" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="BB" sortKey="BB" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="K" sortKey="K" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="ERA" sortKey="ERA" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="WHIP" sortKey="WHIP" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="K/9" sortKey="K/9" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                </tr>
                            </thead>
                            <tbody>
                                {{items.slice(0, 100).map((p, i) => (
                                    <tr key={{i}}>
                                        <td><PlayerLink name={{p.Name}} brefId={{p.bref_id}} onClick={{() => onPlayerClick(p, 'pitcher')}} /></td>
                                        <td>{{p.Team}}</td>
                                        <td>{{p.Conference}}</td>
                                        <td className="text-center">{{p.G}}</td>
                                        <td className="text-center">{{p.IP}}</td>
                                        <td className="text-center">{{p.H}}</td>
                                        <td className="text-center">{{p.R}}</td>
                                        <td className="text-center">{{p.ER}}</td>
                                        <td className="text-center">{{p.BB}}</td>
                                        <td className="text-center">{{p.K}}</td>
                                        <td className="text-center">{{p.ERA}}</td>
                                        <td className="text-center">{{p.WHIP}}</td>
                                        <td className="text-center">{{p['K/9']}}</td>
                                    </tr>
                                ))}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const TeamRecords = ({{ teams, confFilter }}) => {{
            const filtered = useMemo(() => {{
                if (!confFilter || confFilter === 'All') return teams;
                return teams.filter(t => t.Conference === confFilter);
            }}, [teams, confFilter]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'W', direction: 'desc' }});

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Team Records ({{filtered.length}})</h2></div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Team" sortKey="Team" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Conference" sortKey="Conference" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="W" sortKey="W" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="L" sortKey="L" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Win%" sortKey="Win%" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="RS" sortKey="RS" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="RA" sortKey="RA" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Diff" sortKey="Diff" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                </tr>
                            </thead>
                            <tbody>
                                {{items.map((t, i) => (
                                    <tr key={{i}}>
                                        <td>{{t.Team}}</td>
                                        <td>{{t.Conference}}</td>
                                        <td className="text-center">{{t.W}}</td>
                                        <td className="text-center">{{t.L}}</td>
                                        <td className="text-center">{{t['Win%']}}</td>
                                        <td className="text-center">{{t.RS}}</td>
                                        <td className="text-center">{{t.RA}}</td>
                                        <td className="text-center">{{t.Diff > 0 ? '+' : ''}}{{t.Diff}}</td>
                                    </tr>
                                ))}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const MilestonesTable = ({{ title, data, columns }}) => {{
            const {{ items, sortConfig, requestSort }} = useSortableData(data, {{ key: 'Date', direction: 'desc' }});

            if (!data || data.length === 0) return null;
            return (
                <div className="panel" style={{{{marginTop: '16px'}}}}>
                    <div className="panel-header"><h2>{{title}} ({{data.length}})</h2></div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    {{columns.map(col => (
                                        <SortableHeader key={{col}} label={{col}} sortKey={{col}} sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    ))}}
                                </tr>
                            </thead>
                            <tbody>
                                {{items.slice(0, 50).map((row, i) => (
                                    <tr key={{i}}>
                                        {{columns.map(col => (
                                            <td key={{col}} className="text-center">{{row[col]}}</td>
                                        ))}}
                                    </tr>
                                ))}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const Checklist = ({{ checklist }}) => {{
            const [selectedConf, setSelectedConf] = useState('All');

            const conferences = useMemo(() => {{
                return ['All', ...Object.keys(checklist).sort()];
            }}, [checklist]);

            const getStats = useMemo(() => {{
                if (selectedConf === 'All') {{
                    let totalTeams = 0, totalSeen = 0, totalVisited = 0;
                    Object.values(checklist).forEach(c => {{
                        totalTeams += c.total;
                        totalSeen += c.seen;
                        totalVisited += c.visited;
                    }});
                    return {{ total: totalTeams, seen: totalSeen, visited: totalVisited }};
                }}
                const conf = checklist[selectedConf] || {{}};
                return {{ total: conf.total || 0, seen: conf.seen || 0, visited: conf.visited || 0 }};
            }}, [checklist, selectedConf]);

            const teams = useMemo(() => {{
                if (selectedConf === 'All') {{
                    const all = [];
                    Object.entries(checklist).forEach(([confName, c]) => {{
                        c.teams.forEach(t => all.push({{ team: t, status: c.teamStatus[t], conf: confName }}));
                    }});
                    return all.sort((a, b) => a.team.localeCompare(b.team));
                }}
                const conf = checklist[selectedConf];
                if (!conf) return [];
                return conf.teams.map(t => ({{ team: t, status: conf.teamStatus[t], conf: selectedConf }})).sort((a, b) => a.team.localeCompare(b.team));
            }}, [checklist, selectedConf]);

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Conference Checklist</h2></div>
                    <div style={{{{padding: '20px'}}}}>
                    <div style={{{{marginBottom: '16px'}}}}>
                        <select
                            className="search-box"
                            style={{{{width: 'auto', minWidth: '200px'}}}}
                            value={{selectedConf}}
                            onChange={{(e) => setSelectedConf(e.target.value)}}
                        >
                            {{conferences.map(c => <option key={{c}} value={{c}}>{{c}}</option>)}}
                        </select>
                    </div>
                    <div style={{{{display: 'flex', gap: '24px', marginBottom: '16px', flexWrap: 'wrap'}}}}>
                        <div style={{{{background: '#f0f0f0', padding: '12px 24px', borderRadius: '8px', textAlign: 'center'}}}}>
                            <div style={{{{fontSize: '24px', fontWeight: 'bold', color: '#333'}}}}>{{getStats.seen}}/{{getStats.total}}</div>
                            <div style={{{{fontSize: '14px', color: '#666'}}}}>Teams Seen</div>
                        </div>
                        <div style={{{{background: '#f0f0f0', padding: '12px 24px', borderRadius: '8px', textAlign: 'center'}}}}>
                            <div style={{{{fontSize: '24px', fontWeight: 'bold', color: '#27ae60'}}}}>{{getStats.visited}}</div>
                            <div style={{{{fontSize: '14px', color: '#666'}}}}>Home Stadiums</div>
                        </div>
                        <div style={{{{background: '#f0f0f0', padding: '12px 24px', borderRadius: '8px', textAlign: 'center'}}}}>
                            <div style={{{{fontSize: '24px', fontWeight: 'bold', color: '#333'}}}}>{{Math.round((getStats.seen / getStats.total) * 100) || 0}}%</div>
                            <div style={{{{fontSize: '14px', color: '#666'}}}}>Progress</div>
                        </div>
                    </div>
                    <div style={{{{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px'}}}}>
                        {{teams.map(({{ team, status, conf }}) => (
                            <div key={{team}} style={{{{
                                padding: '10px 14px',
                                borderRadius: '6px',
                                background: status === 'home' ? '#d4edda' : status === 'away' ? '#cce5ff' : '#f8f9fa',
                                border: `1px solid ${{status === 'home' ? '#28a745' : status === 'away' ? '#007bff' : '#dee2e6'}}`,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}}}>
                                <span style={{{{
                                    width: '12px',
                                    height: '12px',
                                    borderRadius: '50%',
                                    background: status === 'home' ? '#28a745' : status === 'away' ? '#007bff' : '#ccc'
                                }}}}></span>
                                <span style={{{{flex: 1, fontWeight: status !== 'none' ? 500 : 400}}}}>{{team}}</span>
                                {{selectedConf === 'All' && <span style={{{{fontSize: '11px', color: '#666'}}}}>{{conf}}</span>}}
                            </div>
                        ))}}
                    </div>
                    <div style={{{{marginTop: '16px', display: 'flex', gap: '16px', fontSize: '14px', color: '#666'}}}}>
                        <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#28a745', marginRight: '4px'}}}}></span> Visited (Home)</span>
                        <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#007bff', marginRight: '4px'}}}}></span> Seen (Away)</span>
                        <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#ccc', marginRight: '4px'}}}}></span> Not Seen</span>
                    </div>
                    </div>
                </div>
            );
        }};

        const SchoolMap = ({{ stadiums, teamsSeenHome, teamsSeenAway, checklist }}) => {{
            const mapRef = useRef(null);
            const mapInstance = useRef(null);
            const markersRef = useRef([]);
            const [selectedConf, setSelectedConf] = useState('All');
            const [filter, setFilter] = useState('all');

            const conferences = useMemo(() => {{
                return ['All', ...Object.keys(checklist).sort()];
            }}, [checklist]);

            useEffect(() => {{
                if (!mapRef.current || mapInstance.current) return;

                // Initialize map centered on US
                mapInstance.current = L.map(mapRef.current).setView([39.5, -98.35], 4);

                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 18,
                    attribution: '&copy; OpenStreetMap contributors'
                }}).addTo(mapInstance.current);

                return () => {{
                    if (mapInstance.current) {{
                        mapInstance.current.remove();
                        mapInstance.current = null;
                    }}
                }};
            }}, []);

            useEffect(() => {{
                if (!mapInstance.current) return;

                // Clear existing markers
                markersRef.current.forEach(m => m.remove());
                markersRef.current = [];

                // Get teams to show
                let teamsToShow = [];
                if (selectedConf === 'All') {{
                    Object.values(checklist).forEach(c => {{
                        teamsToShow.push(...c.teams);
                    }});
                }} else if (checklist[selectedConf]) {{
                    teamsToShow = checklist[selectedConf].teams;
                }}

                // Filter by seen status
                if (filter === 'seen') {{
                    teamsToShow = teamsToShow.filter(t => teamsSeenHome.includes(t) || teamsSeenAway.includes(t));
                }} else if (filter === 'visited') {{
                    teamsToShow = teamsToShow.filter(t => teamsSeenHome.includes(t));
                }} else if (filter === 'unseen') {{
                    teamsToShow = teamsToShow.filter(t => !teamsSeenHome.includes(t) && !teamsSeenAway.includes(t));
                }}

                // Add markers
                teamsToShow.forEach(team => {{
                    const info = stadiums[team];
                    if (!info) return;

                    const isHome = teamsSeenHome.includes(team);
                    const isAway = teamsSeenAway.includes(team);
                    const color = isHome ? '#28a745' : isAway ? '#007bff' : '#999';

                    const icon = L.divIcon({{
                        className: 'custom-marker',
                        html: `<div style="width: 14px; height: 14px; background: ${{color}}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                        iconSize: [14, 14],
                        iconAnchor: [7, 7]
                    }});

                    const marker = L.marker([info.lat, info.lng], {{ icon }})
                        .bindPopup(`<strong>${{team}}</strong><br>${{info.stadium}}<br><em>${{isHome ? 'Visited' : isAway ? 'Seen (Away)' : 'Not Seen'}}</em>`)
                        .addTo(mapInstance.current);
                    markersRef.current.push(marker);
                }});
            }}, [stadiums, teamsSeenHome, teamsSeenAway, selectedConf, filter, checklist]);

            return (
                <div className="panel">
                    <div className="panel-header"><h2>School Map</h2></div>
                    <div style={{{{marginBottom: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap'}}}}>
                        <select
                            className="search-box"
                            style={{{{width: 'auto', minWidth: '150px'}}}}
                            value={{selectedConf}}
                            onChange={{(e) => setSelectedConf(e.target.value)}}
                        >
                            {{conferences.map(c => <option key={{c}} value={{c}}>{{c}}</option>)}}
                        </select>
                        <select
                            className="search-box"
                            style={{{{width: 'auto', minWidth: '150px'}}}}
                            value={{filter}}
                            onChange={{(e) => setFilter(e.target.value)}}
                        >
                            <option value="all">All Schools</option>
                            <option value="seen">Seen</option>
                            <option value="visited">Visited (Home)</option>
                            <option value="unseen">Not Seen</option>
                        </select>
                    </div>
                    <div ref={{mapRef}} style={{{{height: '500px', borderRadius: '8px', border: '1px solid #ddd'}}}}></div>
                    <div style={{{{marginTop: '12px', display: 'flex', gap: '16px', fontSize: '14px', color: '#666'}}}}>
                        <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#28a745', marginRight: '4px'}}}}></span> Visited</span>
                        <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#007bff', marginRight: '4px'}}}}></span> Seen (Away)</span>
                        <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#999', marginRight: '4px'}}}}></span> Not Seen</span>
                    </div>
                </div>
            );
        }};

        const CalendarView = ({{ games }}) => {{
            const [selectedDay, setSelectedDay] = useState(null);

            const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

            // Group games by month-day (ignoring year)
            const gamesByDay = useMemo(() => {{
                const map = {{}};
                games.forEach(game => {{
                    const date = game.Date;
                    if (!date) return;
                    const parts = date.split('/');
                    if (parts.length >= 2) {{
                        const month = parseInt(parts[0], 10);
                        const day = parseInt(parts[1], 10);
                        if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {{
                            const key = `${{month}}-${{day}}`;
                            if (!map[key]) map[key] = [];
                            map[key].push(game);
                        }}
                    }}
                }});
                return map;
            }}, [games]);

            // Get games for selected day
            const selectedGames = useMemo(() => {{
                if (!selectedDay) return [];
                return gamesByDay[selectedDay] || [];
            }}, [selectedDay, gamesByDay]);

            const getColorIntensity = (count) => {{
                if (count === 0) return '#f8f9fa';
                if (count === 1) return '#c6e5c6';
                if (count === 2) return '#8fce8f';
                if (count >= 3) return '#4caf50';
                return '#f8f9fa';
            }};

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Games by Date (All Years)</h2></div>
                    <div style={{{{padding: '20px'}}}}>
                        <div style={{{{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '20px'}}}}>
                            {{MONTHS.map((month, monthIdx) => (
                                <div key={{month}} style={{{{background: '#f8f9fa', borderRadius: '8px', padding: '12px'}}}}>
                                    <div style={{{{fontWeight: 'bold', marginBottom: '8px', textAlign: 'center'}}}}>{{month}}</div>
                                    <div style={{{{display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '2px'}}}}>
                                        {{Array.from({{length: DAYS_IN_MONTH[monthIdx]}}, (_, i) => i + 1).map(day => {{
                                            const key = `${{monthIdx + 1}}-${{day}}`;
                                            const count = (gamesByDay[key] || []).length;
                                            const isSelected = selectedDay === key;
                                            return (
                                                <div
                                                    key={{day}}
                                                    onClick={{() => count > 0 && setSelectedDay(isSelected ? null : key)}}
                                                    style={{{{
                                                        width: '100%',
                                                        aspectRatio: '1',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        fontSize: '10px',
                                                        background: getColorIntensity(count),
                                                        borderRadius: '3px',
                                                        cursor: count > 0 ? 'pointer' : 'default',
                                                        border: isSelected ? '2px solid #1e3a5f' : '1px solid #ddd',
                                                        fontWeight: count > 0 ? 'bold' : 'normal',
                                                    }}}}
                                                    title={{count > 0 ? `${{month}} ${{day}}: ${{count}} game(s)` : `${{month}} ${{day}}`}}
                                                >
                                                    {{day}}
                                                </div>
                                            );
                                        }})}}
                                    </div>
                                </div>
                            ))}}
                        </div>

                        <div style={{{{marginBottom: '16px', display: 'flex', gap: '16px', fontSize: '14px', alignItems: 'center'}}}}>
                            <span>Games:</span>
                            <span style={{{{display: 'flex', alignItems: 'center', gap: '4px'}}}}>
                                <span style={{{{width: '16px', height: '16px', background: '#f8f9fa', border: '1px solid #ddd', borderRadius: '3px'}}}}></span> 0
                            </span>
                            <span style={{{{display: 'flex', alignItems: 'center', gap: '4px'}}}}>
                                <span style={{{{width: '16px', height: '16px', background: '#c6e5c6', border: '1px solid #ddd', borderRadius: '3px'}}}}></span> 1
                            </span>
                            <span style={{{{display: 'flex', alignItems: 'center', gap: '4px'}}}}>
                                <span style={{{{width: '16px', height: '16px', background: '#8fce8f', border: '1px solid #ddd', borderRadius: '3px'}}}}></span> 2
                            </span>
                            <span style={{{{display: 'flex', alignItems: 'center', gap: '4px'}}}}>
                                <span style={{{{width: '16px', height: '16px', background: '#4caf50', border: '1px solid #ddd', borderRadius: '3px'}}}}></span> 3+
                            </span>
                        </div>

                        {{selectedDay && selectedGames.length > 0 && (
                            <div style={{{{marginTop: '16px'}}}}>
                                <h4 style={{{{margin: '0 0 12px 0', color: '#1e3a5f'}}}}>
                                    Games on {{MONTHS[parseInt(selectedDay.split('-')[0], 10) - 1]}} {{selectedDay.split('-')[1]}} ({{selectedGames.length}})
                                </h4>
                                <div className="table-container" style={{{{maxHeight: '300px'}}}}>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Year</th>
                                                <th>Away</th>
                                                <th className="text-center">Score</th>
                                                <th>Home</th>
                                                <th>Venue</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {{selectedGames.sort((a, b) => {{
                                                const yearA = a.Date?.split('/')[2] || '0';
                                                const yearB = b.Date?.split('/')[2] || '0';
                                                return yearB.localeCompare(yearA);
                                            }}).map((g, i) => (
                                                <tr key={{i}}>
                                                    <td>{{g.Date?.split('/')[2]}}</td>
                                                    <td>{{g.Away}}</td>
                                                    <td className="text-center">{{g['Away Score']}} - {{g['Home Score']}}</td>
                                                    <td>{{g.Home}}</td>
                                                    <td>{{g.Venue}}</td>
                                                </tr>
                                            ))}}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}}
                    </div>
                </div>
            );
        }};

        const App = () => {{
            const [activeTab, setActiveTab] = useState('games');
            const [search, setSearch] = useState('');
            const [confFilter, setConfFilter] = useState('All');
            const [selectedPlayer, setSelectedPlayer] = useState(null);
            const [playerType, setPlayerType] = useState(null);

            // Handle player click to show modal
            const handlePlayerClick = (player, type) => {{
                setSelectedPlayer(player);
                setPlayerType(type);
            }};

            const closeModal = () => {{
                setSelectedPlayer(null);
                setPlayerType(null);
            }};

            // Get game log for selected player
            const selectedPlayerGames = useMemo(() => {{
                if (!selectedPlayer) return [];
                const name = selectedPlayer.Name;
                if (playerType === 'batter') {{
                    return DATA.batterGames.filter(g => g.Name === name);
                }} else {{
                    return DATA.pitcherGames.filter(g => g.Name === name);
                }}
            }}, [selectedPlayer, playerType]);

            // Get unique conferences from data
            const conferences = useMemo(() => {{
                const confs = new Set(['All']);
                DATA.batters.forEach(b => {{
                    if (b.Conference) {{
                        b.Conference.split(', ').forEach(c => confs.add(c));
                    }}
                }});
                DATA.pitchers.forEach(p => {{
                    if (p.Conference) {{
                        p.Conference.split(', ').forEach(c => confs.add(c));
                    }}
                }});
                DATA.teamRecords.forEach(t => {{
                    if (t.Conference && t.Conference !== 'Other') confs.add(t.Conference);
                }});
                return Array.from(confs).sort((a, b) => {{
                    if (a === 'All') return -1;
                    if (b === 'All') return 1;
                    return a.localeCompare(b);
                }});
            }}, []);

            const tabs = [
                {{ id: 'games', label: 'Games' }},
                {{ id: 'calendar', label: 'Calendar' }},
                {{ id: 'batters', label: 'Batters' }},
                {{ id: 'pitchers', label: 'Pitchers' }},
                {{ id: 'teams', label: 'Teams' }},
                {{ id: 'milestones', label: 'Milestones' }},
                {{ id: 'checklist', label: 'Checklist' }},
                {{ id: 'map', label: 'Map' }},
            ];

            return (
                <div className="container">
                    <StatsGrid data={{DATA.summary}} />

                    <div className="tabs">
                        {{tabs.map(tab => (
                            <button
                                key={{tab.id}}
                                className={{'tab ' + (activeTab === tab.id ? 'active' : '')}}
                                onClick={{() => setActiveTab(tab.id)}}
                            >
                                {{tab.label}}
                            </button>
                        ))}}
                    </div>

                    {{(activeTab === 'batters' || activeTab === 'pitchers' || activeTab === 'teams') && (
                        <div style={{{{display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap'}}}}>
                            <select
                                className="search-box"
                                style={{{{width: 'auto', minWidth: '150px'}}}}
                                value={{confFilter}}
                                onChange={{(e) => setConfFilter(e.target.value)}}
                            >
                                {{conferences.map(c => <option key={{c}} value={{c}}>{{c}}</option>)}}
                            </select>
                            {{(activeTab === 'batters' || activeTab === 'pitchers') && (
                                <input
                                    type="text"
                                    className="search-box"
                                    placeholder="Search by name or team..."
                                    value={{search}}
                                    onChange={{(e) => setSearch(e.target.value)}}
                                />
                            )}}
                        </div>
                    )}}

                    {{activeTab === 'games' && <GameLog games={{DATA.gameLog}} />}}
                    {{activeTab === 'calendar' && <CalendarView games={{DATA.gameLog}} />}}
                    {{activeTab === 'batters' && <BattersTable batters={{DATA.batters}} search={{search}} confFilter={{confFilter}} onPlayerClick={{handlePlayerClick}} />}}
                    {{activeTab === 'pitchers' && <PitchersTable pitchers={{DATA.pitchers}} search={{search}} confFilter={{confFilter}} onPlayerClick={{handlePlayerClick}} />}}
                    {{activeTab === 'teams' && <TeamRecords teams={{DATA.teamRecords}} confFilter={{confFilter}} />}}
                    {{activeTab === 'milestones' && (
                        <div>
                            <h3 style={{{{margin: '0 0 16px 0', color: '#1e3a5f'}}}}>Pitching Milestones</h3>
                            <MilestonesTable
                                title="No-Hitters (9+ IP, 0 H)"
                                data={{DATA.milestones.noHitters}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'BB', 'Score']}}
                            />
                            <MilestonesTable
                                title="Shutouts (9+ IP, 0 ER)"
                                data={{DATA.milestones.shutouts}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'BB']}}
                            />
                            <MilestonesTable
                                title="Complete Games (9+ IP)"
                                data={{DATA.milestones.completeGames}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}}
                            />
                            <MilestonesTable
                                title="10+ K Games"
                                data={{DATA.milestones.tenKGames}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'K', 'IP', 'H', 'ER']}}
                            />
                            <MilestonesTable
                                title="Quality Starts (6+ IP, 3 or fewer ER)"
                                data={{DATA.milestones.qualityStarts}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}}
                            />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Batting Milestones</h3>
                            <MilestonesTable
                                title="Multi-HR Games"
                                data={{DATA.milestones.multiHrGames}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'HR', 'H', 'RBI']}}
                            />
                            <MilestonesTable
                                title="Cycle Watch (3 of 4 hit types)"
                                data={{DATA.milestones.cycleWatch}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', '1B', '2B', '3B', 'HR']}}
                            />
                            <MilestonesTable
                                title="4+ Hit Games"
                                data={{DATA.milestones.fourHitGames}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'H', 'R', 'RBI']}}
                            />
                            <MilestonesTable
                                title="5+ RBI Games"
                                data={{DATA.milestones.fiveRbiGames}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'RBI', 'H', 'HR']}}
                            />
                            <MilestonesTable
                                title="Multi-SB Games"
                                data={{DATA.milestones.multiSbGames}}
                                columns={{['Date', 'Player', 'Team', 'Opponent', 'SB', 'H', 'R']}}
                            />
                        </div>
                    )}}

                    {{activeTab === 'checklist' && <Checklist checklist={{DATA.checklist}} />}}
                    {{activeTab === 'map' && <SchoolMap stadiums={{DATA.stadiumLocations}} teamsSeenHome={{DATA.teamsSeenHome}} teamsSeenAway={{DATA.teamsSeenAway}} checklist={{DATA.checklist}} />}}

                    <div className="footer">
                        Generated {generated_time} | Player links go to Baseball-Reference.com
                    </div>

                    {{selectedPlayer && (
                        <PlayerModal
                            player={{selectedPlayer}}
                            games={{selectedPlayerGames}}
                            type={{playerType}}
                            onClose={{closeModal}}
                        />
                    )}}
                </div>
            );
        }};

        ReactDOM.render(<App />, document.getElementById('root'));
    </script>
</body>
</html>'''
