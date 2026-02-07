"""
Website generator for interactive HTML output.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

from ..utils.stadiums import STADIUM_DATA, NCAA_TEAM_LOGOS
from ..utils.milb_stadiums import MILB_STADIUM_DATA, MILB_TEAM_LEAGUES, HISTORIC_MILB_TEAMS, LOGO_OVERRIDES, HISTORICAL_TEAM_LOGOS, find_stadium
from ..utils.partner_stadiums import PARTNER_TEAM_DATA, get_partner_stadium_locations
from ..utils.constants import (CONFERENCES, get_conference, SPORT_LEVEL_MAP, LEAGUE_LEVEL_MAP,
                                PRO_LEVELS, LEVEL_ORDER, LEVEL_COLORS, resolve_level_and_league)
from ..utils.helpers import normalize_team_name
from ..utils.player_ids import PlayerIDMapper


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

    # MiLB stats
    milb_game_log = processed_data.get('milb_game_log', pd.DataFrame())
    milb_batters = processed_data.get('milb_batters', pd.DataFrame())
    milb_pitchers = processed_data.get('milb_pitchers', pd.DataFrame())
    crossover_players = processed_data.get('crossover_players', pd.DataFrame())

    milb_games_count = len(milb_game_log) if isinstance(milb_game_log, pd.DataFrame) else 0
    milb_batters_count = len(milb_batters) if isinstance(milb_batters, pd.DataFrame) else 0
    milb_pitchers_count = len(milb_pitchers) if isinstance(milb_pitchers, pd.DataFrame) else 0
    crossover_count = len(crossover_players) if isinstance(crossover_players, pd.DataFrame) else 0

    # Milestone counts
    milestones = processed_data.get('milestones', {})
    hr_games_count = len(milestones.get('hr_games', []))
    ten_k_count = len(milestones.get('ten_k_games', []))

    # Build stadium locations for map
    stadium_locations = {}
    for team, info in STADIUM_DATA.items():
        lat, lng, stadium_name = info
        stadium_locations[team] = {'lat': lat, 'lng': lng, 'stadium': stadium_name, 'type': 'ncaa'}

    # Build MiLB stadium locations (includes defunct teams for historical visits)
    milb_stadium_locations = {}
    for venue_name, info in MILB_STADIUM_DATA.items():
        lat, lng, team_name, level_code, team_id, league_name = info
        resolved_level = SPORT_LEVEL_MAP.get(level_code, level_code)
        # Check for logo override, otherwise use mlbstatic
        logo_url = LOGO_OVERRIDES.get(team_id, f'https://www.mlbstatic.com/team-logos/{team_id}.svg')
        milb_stadium_locations[venue_name] = {
            'lat': lat, 'lng': lng, 'stadium': venue_name,
            'team': team_name, 'level': resolved_level, 'league': league_name, 'type': 'milb',
            'teamId': team_id, 'logo': logo_url
        }

    # Build Partner (independent league) stadium locations
    partner_stadium_locations = get_partner_stadium_locations()

    # Build partner logos mapping (team name -> logo URL)
    partner_logos = {team_name: data.get('logo') for team_name, data in PARTNER_TEAM_DATA.items() if data.get('logo')}

    # MiLB venue name mappings (old names -> current names)
    milb_venue_aliases = {
        'Calvin Falwell Field': 'Bank of the James Stadium',  # Lynchburg Hillcats
        'Perfect Game Field': 'Veterans Memorial Stadium',  # Cedar Rapids Kernels
    }

    # Track MiLB and Partner venues visited
    milb_venues_visited = set()
    partner_venues_visited = set()
    for game in raw_games:
        if game.get('format') == 'milb_api':
            venue = game.get('metadata', {}).get('venue', '')
            if venue:
                # Map old venue names to current names
                mapped_venue = milb_venue_aliases.get(venue, venue)
                milb_venues_visited.add(mapped_venue)
        elif game.get('metadata', {}).get('source') == 'partner':
            # Partner league games - track both teams' stadiums as "visited"
            metadata = game.get('metadata', {})
            home_team = metadata.get('home_team', '')
            if home_team and home_team in PARTNER_TEAM_DATA:
                stadium = PARTNER_TEAM_DATA[home_team].get('stadium')
                if stadium:
                    partner_venues_visited.add(stadium)

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

    # Build MiLB/Partner checklist organized by level/league
    milb_teams_seen_home = set()  # Teams at venues we visited
    milb_teams_seen_away = set()  # Teams we saw play (as away team at a venue we visited)

    for game in raw_games:
        if game.get('format') == 'milb_api':
            metadata = game.get('metadata', {})
            home_team = metadata.get('home_team', '')
            away_team = metadata.get('away_team', '')
            if home_team:
                milb_teams_seen_home.add(home_team)
            if away_team:
                milb_teams_seen_away.add(away_team)
        elif game.get('metadata', {}).get('source') == 'partner':
            metadata = game.get('metadata', {})
            home_team = metadata.get('home_team', '')
            away_team = metadata.get('away_team', '')
            if home_team:
                milb_teams_seen_home.add(home_team)
            if away_team:
                milb_teams_seen_away.add(away_team)

    # Organize MiLB teams by level → league
    milb_by_level = {}
    for level in LEVEL_ORDER[1:]:  # Skip 'NCAA'
        milb_by_level[level] = {}
        for league in PRO_LEVELS.get(level, []):
            milb_by_level[level][league] = []

    # Add active MiLB teams (skip defunct/historic teams)
    for venue_name, info in MILB_STADIUM_DATA.items():
        lat, lng, team_name, level_code, team_id, league_name = info
        if team_name in HISTORIC_MILB_TEAMS:
            continue
        mapped_level = SPORT_LEVEL_MAP.get(level_code, level_code)
        logo_url = LOGO_OVERRIDES.get(team_id, f'https://www.mlbstatic.com/team-logos/{team_id}.svg')
        team_entry = {
            'team': team_name,
            'venue': venue_name,
            'teamId': team_id,
            'logo': logo_url,
            'league': league_name,
            'historic': False,
        }
        if mapped_level in milb_by_level:
            if league_name in milb_by_level[mapped_level]:
                milb_by_level[mapped_level][league_name].append(team_entry)
            else:
                milb_by_level[mapped_level][league_name] = [team_entry]

    # Track team names already added from MILB_STADIUM_DATA to avoid duplicates
    seen_milb_team_names = set()
    for venue_info in MILB_STADIUM_DATA.values():
        seen_milb_team_names.add(venue_info[2])  # team_name is index 2

    # Add Partner (independent league) teams
    seen_partner_ids = set()
    for team_name, data in PARTNER_TEAM_DATA.items():
        team_id = data.get('id')
        if team_id in seen_partner_ids or team_name in seen_milb_team_names:
            continue
        seen_partner_ids.add(team_id)
        league_name = data.get('league', '')
        team_entry = {
            'team': team_name,
            'venue': data.get('stadium', ''),
            'teamId': team_id,
            'logo': data.get('logo', ''),
            'league': league_name,
            'historic': False,
        }
        if 'Independent' in milb_by_level:
            if league_name in milb_by_level['Independent']:
                milb_by_level['Independent'][league_name].append(team_entry)
            else:
                milb_by_level['Independent'][league_name] = [team_entry]

    # Build flat milb_checklist per level (with league breakdown)
    milb_checklist = {}
    for level, leagues in milb_by_level.items():
        all_teams = []
        league_data = {}
        for league_name, teams in leagues.items():
            all_teams.extend(teams)
            team_names = [t['team'] for t in teams]
            seen = len([t for t in team_names if t in milb_teams_seen_home or t in milb_teams_seen_away])
            visited = len([t for t in team_names if t in milb_teams_seen_home])
            league_data[league_name] = {
                'teams': sorted(teams, key=lambda x: x['team']),
                'total': len(teams),
                'seen': seen,
                'visited': visited,
                'teamStatus': {t['team']: 'home' if t['team'] in milb_teams_seen_home else ('away' if t['team'] in milb_teams_seen_away else 'none') for t in teams}
            }
        all_team_names = [t['team'] for t in all_teams]
        total_seen = len([t for t in all_team_names if t in milb_teams_seen_home or t in milb_teams_seen_away])
        total_visited = len([t for t in all_team_names if t in milb_teams_seen_home])
        milb_checklist[level] = {
            'teams': sorted(all_teams, key=lambda x: x['team']),
            'total': len(all_teams),
            'seen': total_seen,
            'visited': total_visited,
            'teamStatus': {t['team']: 'home' if t['team'] in milb_teams_seen_home else ('away' if t['team'] in milb_teams_seen_away else 'none') for t in all_teams},
            'leagues': league_data,
        }

    # Get game-by-game data for players
    batter_games = processed_data.get('batter_games', pd.DataFrame())
    pitcher_games = processed_data.get('pitcher_games', pd.DataFrame())

    # Build unified game log (all levels)
    unified_game_log = []

    # Add NCAA games
    ncaa_log = df_to_list(game_log)
    for game in ncaa_log:
        # Convert DateSort from "2025-06-16" to "20250616" for consistent sorting
        date_sort = game.get('DateSort', game.get('Date', ''))
        if date_sort and '-' in date_sort:
            date_sort = date_sort.replace('-', '')
        unified_game_log.append({
            'date': game.get('Date', ''),
            'date_sort': date_sort,
            'away_team': game.get('Away', ''),
            'home_team': game.get('Home', ''),
            'away_score': game.get('Away Score', 0),
            'home_score': game.get('Home Score', 0),
            'venue': game.get('Venue', ''),
            'level': 'NCAA',
            'conference': game.get('Conference', ''),
        })

    # Add MiLB games
    milb_log = df_to_list(milb_game_log)
    for game in milb_log:
        # Find team IDs for logos - use capitalized column names from DataFrame
        home_team = game.get('Home Team', '')
        away_team = game.get('Away Team', '')
        home_team_id = None
        away_team_id = None
        for venue_name, info in MILB_STADIUM_DATA.items():
            if info[2] == home_team:
                home_team_id = info[4]
            if info[2] == away_team:
                away_team_id = info[4]
        # Check partner teams for IDs/logos too
        if not home_team_id and home_team in PARTNER_TEAM_DATA:
            home_team_id = PARTNER_TEAM_DATA[home_team].get('id')
        if not away_team_id and away_team in PARTNER_TEAM_DATA:
            away_team_id = PARTNER_TEAM_DATA[away_team].get('id')

        # Parse score from combined "X-Y" format
        score_str = game.get('Score', '0-0')
        try:
            away_score, home_score = score_str.split('-')
            away_score = int(away_score)
            home_score = int(home_score)
        except:
            away_score, home_score = 0, 0

        # Use resolved level from pipeline
        resolved_level = game.get('Level', '')
        league = game.get('League', '')

        unified_game_log.append({
            'date': game.get('Date', ''),
            'date_sort': game.get('date_yyyymmdd', game.get('Date', '')),
            'away_team': away_team,
            'home_team': home_team,
            'away_score': away_score,
            'home_score': home_score,
            'venue': game.get('Venue', ''),
            'level': resolved_level,
            'league': league,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'parent_orgs': {'away': game.get('Away Parent', ''), 'home': game.get('Home Parent', '')},
        })

    # Sort by date (most recent first)
    unified_game_log.sort(key=lambda x: x.get('date_sort', ''), reverse=True)

    # Build unified batters list (all levels)
    unified_batters = []

    # Add NCAA batters
    ncaa_batters = df_to_list(batters)
    for b in ncaa_batters:
        unified_batters.append({
            'name': b.get('Name', ''),
            'team': b.get('Team', ''),
            'level': 'NCAA',
            'league': b.get('Conference', ''),
            'conference': b.get('Conference', ''),
            'g': b.get('G', 0),
            'ab': b.get('AB', 0),
            'r': b.get('R', 0),
            'h': b.get('H', 0),
            'doubles': b.get('2B', 0),
            'triples': b.get('3B', 0),
            'hr': b.get('HR', 0),
            'rbi': b.get('RBI', 0),
            'bb': b.get('BB', 0),
            'k': b.get('K', 0),
            'sb': b.get('SB', 0),
            'avg': b.get('AVG', '.000'),
            'obp': b.get('OBP', '.000'),
            'slg': b.get('SLG', '.000'),
            'bref_id': b.get('bref_id', ''),
        })

    # Initialize player ID mapper for bref_id lookups on MiLB players
    try:
        id_mapper = PlayerIDMapper(auto_download=True)
    except Exception:
        id_mapper = None

    # Add MiLB batters
    milb_batters_list = df_to_list(milb_batters)
    for b in milb_batters_list:
        team_name = b.get('Team', '')
        team_id = None
        for venue_name, info in MILB_STADIUM_DATA.items():
            if info[2] == team_name:
                team_id = info[4]
                break
        if not team_id and team_name in PARTNER_TEAM_DATA:
            team_id = PARTNER_TEAM_DATA[team_name].get('id')
        # Look up bref_id from MLBAM player_id via Chadwick register
        bref_id = ''
        pid = b.get('Player ID', '') or b.get('player_id', '')
        if pid and id_mapper and str(pid).isdigit():
            bref_id = id_mapper.get_register_from_mlbam(int(pid)) or ''
        elif pid and isinstance(pid, str) and not str(pid).isdigit():
            bref_id = pid
        resolved_level = b.get('Level', '')
        league = b.get('League', '')
        unified_batters.append({
            'name': b.get('Name', ''),
            'team': team_name,
            'level': resolved_level,
            'league': league,
            'team_id': team_id,
            'g': b.get('G', 0),
            'ab': b.get('AB', 0),
            'r': b.get('R', 0),
            'h': b.get('H', 0),
            'doubles': b.get('2B', 0),
            'triples': b.get('3B', 0),
            'hr': b.get('HR', 0),
            'rbi': b.get('RBI', 0),
            'bb': b.get('BB', 0),
            'k': b.get('K', 0),
            'sb': b.get('SB', 0),
            'avg': b.get('AVG', '.000'),
            'obp': b.get('OBP', '.000'),
            'slg': b.get('SLG', '.000'),
            'player_id': pid,
            'bref_id': bref_id,
        })

    # Build unified pitchers list (all levels)
    unified_pitchers = []

    # Add NCAA pitchers
    ncaa_pitchers = df_to_list(pitchers)
    for p in ncaa_pitchers:
        unified_pitchers.append({
            'name': p.get('Name', ''),
            'team': p.get('Team', ''),
            'level': 'NCAA',
            'league': p.get('Conference', ''),
            'conference': p.get('Conference', ''),
            'g': p.get('G', 0),
            'ip': p.get('IP', 0),
            'h': p.get('H', 0),
            'r': p.get('R', 0),
            'er': p.get('ER', 0),
            'bb': p.get('BB', 0),
            'k': p.get('K', 0),
            'hr': p.get('HR', 0),
            'era': p.get('ERA', '0.00'),
            'bref_id': p.get('bref_id', ''),
        })

    # Add MiLB pitchers
    milb_pitchers_list = df_to_list(milb_pitchers)
    for p in milb_pitchers_list:
        team_name = p.get('Team', '')
        team_id = None
        for venue_name, info in MILB_STADIUM_DATA.items():
            if info[2] == team_name:
                team_id = info[4]
                break
        if not team_id and team_name in PARTNER_TEAM_DATA:
            team_id = PARTNER_TEAM_DATA[team_name].get('id')
        # Look up bref_id from MLBAM player_id via Chadwick register
        bref_id = ''
        pid = p.get('Player ID', '') or p.get('player_id', '')
        if pid and id_mapper and str(pid).isdigit():
            bref_id = id_mapper.get_register_from_mlbam(int(pid)) or ''
        elif pid and isinstance(pid, str) and not str(pid).isdigit():
            bref_id = pid
        resolved_level = p.get('Level', '')
        league = p.get('League', '')
        unified_pitchers.append({
            'name': p.get('Name', ''),
            'team': team_name,
            'level': resolved_level,
            'league': league,
            'team_id': team_id,
            'g': p.get('G', 0),
            'ip': p.get('IP', 0),
            'h': p.get('H', 0),
            'r': p.get('R', 0),
            'er': p.get('ER', 0),
            'bb': p.get('BB', 0),
            'k': p.get('K', 0),
            'hr': p.get('HR', 0),
            'era': p.get('ERA', '0.00'),
            'player_id': pid,
            'bref_id': bref_id,
        })

    return {
        'summary': {
            'totalGames': total_games,
            'totalBatters': total_batters,
            'totalPitchers': total_pitchers,
            'totalTeams': total_teams,
            'hrGames': hr_games_count,
            'tenKGames': ten_k_count,
            'milbGames': milb_games_count,
            'milbBatters': milb_batters_count,
            'milbPitchers': milb_pitchers_count,
            'crossoverPlayers': crossover_count,
            'allGames': len(unified_game_log),
            'unifiedBatters': len(unified_batters),
            'unifiedPitchers': len(unified_pitchers),
        },
        'levelColors': LEVEL_COLORS,
        'levelOrder': LEVEL_ORDER,
        'gameLog': df_to_list(game_log),
        'batters': df_to_list(batters),
        'pitchers': df_to_list(pitchers),
        'batterGames': df_to_list(batter_games),
        'pitcherGames': df_to_list(pitcher_games),
        'teamRecords': df_to_list(team_records),
        'milestones': {
            # Batting milestones (21)
            'threeHrGames': df_to_list(milestones.get('three_hr_games', [])),
            'multiHrGames': df_to_list(milestones.get('multi_hr_games', [])),
            'hrGames': df_to_list(milestones.get('hr_games', [])),
            'fiveHitGames': df_to_list(milestones.get('five_hit_games', [])),
            'fourHitGames': df_to_list(milestones.get('four_hit_games', [])),
            'threeHitGames': df_to_list(milestones.get('three_hit_games', [])),
            'cycles': df_to_list(milestones.get('cycles', [])),
            'cycleWatch': df_to_list(milestones.get('cycle_watch', [])),
            'sixRbiGames': df_to_list(milestones.get('six_rbi_games', [])),
            'fiveRbiGames': df_to_list(milestones.get('five_rbi_games', [])),
            'fourRbiGames': df_to_list(milestones.get('four_rbi_games', [])),
            'threeRbiGames': df_to_list(milestones.get('three_rbi_games', [])),
            'multiDoubleGames': df_to_list(milestones.get('multi_double_games', [])),
            'multiTripleGames': df_to_list(milestones.get('multi_triple_games', [])),
            'multiSbGames': df_to_list(milestones.get('multi_sb_games', [])),
            'fourWalkGames': df_to_list(milestones.get('four_walk_games', [])),
            'perfectBattingGames': df_to_list(milestones.get('perfect_batting_games', [])),
            'fourRunGames': df_to_list(milestones.get('four_run_games', [])),
            'threeRunGames': df_to_list(milestones.get('three_run_games', [])),
            'hitForExtraBases': df_to_list(milestones.get('hit_for_extra_bases', [])),
            'threeTotalBasesGames': df_to_list(milestones.get('three_total_bases_games', [])),
            # Pitching milestones (22)
            'perfectGames': df_to_list(milestones.get('perfect_games', [])),
            'noHitters': df_to_list(milestones.get('no_hitters', [])),
            'oneHitters': df_to_list(milestones.get('one_hitters', [])),
            'twoHitters': df_to_list(milestones.get('two_hitters', [])),
            'shutouts': df_to_list(milestones.get('shutouts', [])),
            'cgsoNoWalks': df_to_list(milestones.get('cgso_no_walks', [])),
            'completeGames': df_to_list(milestones.get('complete_games', [])),
            'lowHitCg': df_to_list(milestones.get('low_hit_cg', [])),
            'sevenInningShutouts': df_to_list(milestones.get('seven_inning_shutouts', [])),
            'madduxGames': df_to_list(milestones.get('maddux_games', [])),
            'fifteenKGames': df_to_list(milestones.get('fifteen_k_games', [])),
            'twelveKGames': df_to_list(milestones.get('twelve_k_games', [])),
            'tenKGames': df_to_list(milestones.get('ten_k_games', [])),
            'eightKGames': df_to_list(milestones.get('eight_k_games', [])),
            'qualityStarts': df_to_list(milestones.get('quality_starts', [])),
            'dominantStarts': df_to_list(milestones.get('dominant_starts', [])),
            'efficientStarts': df_to_list(milestones.get('efficient_starts', [])),
            'highKLowBb': df_to_list(milestones.get('high_k_low_bb', [])),
            'noWalkStarts': df_to_list(milestones.get('no_walk_starts', [])),
            'scorelessRelief': df_to_list(milestones.get('scoreless_relief', [])),
            'winGames': df_to_list(milestones.get('win_games', [])),
            'saveGames': df_to_list(milestones.get('save_games', [])),
        },
        'unifiedGameLog': unified_game_log,
        'crossoverPlayers': df_to_list(crossover_players),
        'rawGames': raw_games,
        'stadiumLocations': stadium_locations,
        'milbStadiumLocations': milb_stadium_locations,
        'partnerStadiumLocations': partner_stadium_locations,
        'milbVenuesVisited': list(milb_venues_visited),
        'partnerVenuesVisited': list(partner_venues_visited),
        'checklist': checklist,
        'milbChecklist': milb_checklist,
        'teamsSeenHome': list(teams_seen_home),
        'teamsSeenAway': list(teams_seen_away),
        'venuesVisited': list(venues_visited),
        'unifiedBatters': unified_batters,
        'unifiedPitchers': unified_pitchers,
        'historicalTeamLogos': HISTORICAL_TEAM_LOGOS,
        'ncaaTeamLogos': NCAA_TEAM_LOGOS,
        'partnerLogos': partner_logos,
    }


def _generate_html(json_data: str, summary: Dict[str, Any]) -> str:
    """Generate the HTML content."""

    total_games = summary.get('totalGames', 0)
    total_batters = summary.get('totalBatters', 0)
    total_pitchers = summary.get('totalPitchers', 0)
    milb_games = summary.get('milbGames', 0)
    crossover_players = summary.get('crossoverPlayers', 0)
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Build header subtitle
    all_games = summary.get('allGames', total_games + milb_games)
    unified_batters = summary.get('unifiedBatters', total_batters + summary.get('milbBatters', 0))
    unified_pitchers = summary.get('unifiedPitchers', total_pitchers + summary.get('milbPitchers', 0))
    header_parts = [f"{all_games} Games"]
    header_parts.append(f"{unified_batters} Batters")
    header_parts.append(f"{unified_pitchers} Pitchers")
    if crossover_players > 0:
        header_parts.append(f"{crossover_players} Crossover Players")
    header_subtitle = " | ".join(header_parts)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baseball Statistics</title>
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
        <h1>Baseball Statistics</h1>
        <p>{header_subtitle} | Generated {generated_time}</p>
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

        // Shared LevelLeagueFilter component
        const LevelLeagueFilter = ({{ levelFilter, setLevelFilter, leagueFilter, setLeagueFilter, data, showSearch, searchTerm, setSearchTerm, searchPlaceholder }}) => {{
            const levelColors = DATA.levelColors || {{}};
            const levelOrder = DATA.levelOrder || ['NCAA', 'Triple-A', 'Double-A', 'High-A', 'Single-A', 'Independent'];

            // Derive available levels from data
            const availableLevels = useMemo(() => {{
                if (!data) return [];
                const levels = new Set();
                data.forEach(d => {{ if (d.level || d.Level) levels.add(d.level || d.Level); }});
                return levelOrder.filter(l => levels.has(l));
            }}, [data]);

            // Derive available leagues for selected level
            const availableLeagues = useMemo(() => {{
                if (!data || levelFilter === 'All') return [];
                const leagues = new Set();
                data.forEach(d => {{
                    const itemLevel = d.level || d.Level || '';
                    const itemLeague = d.league || d.League || d.conference || d.Conference || '';
                    if (itemLevel === levelFilter && itemLeague) leagues.add(itemLeague);
                }});
                return Array.from(leagues).sort();
            }}, [data, levelFilter]);

            const handleLevelChange = (newLevel) => {{
                setLevelFilter(newLevel);
                if (setLeagueFilter) setLeagueFilter('All');
            }};

            return (
                <div style={{{{padding: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center'}}}}>
                    <select
                        className="search-box"
                        style={{{{width: 'auto', minWidth: '120px', margin: 0}}}}
                        value={{levelFilter}}
                        onChange={{(e) => handleLevelChange(e.target.value)}}
                    >
                        <option value="All">All Levels</option>
                        {{availableLevels.map(l => <option key={{l}} value={{l}}>{{l}}</option>)}}
                    </select>
                    {{levelFilter !== 'All' && availableLeagues.length > 1 && setLeagueFilter && (
                        <select
                            className="search-box"
                            style={{{{width: 'auto', minWidth: '150px', margin: 0}}}}
                            value={{leagueFilter || 'All'}}
                            onChange={{(e) => setLeagueFilter(e.target.value)}}
                        >
                            <option value="All">All Leagues</option>
                            {{availableLeagues.map(l => <option key={{l}} value={{l}}>{{l}}</option>)}}
                        </select>
                    )}}
                    {{showSearch && (
                        <input
                            type="text"
                            className="search-box"
                            placeholder={{searchPlaceholder || 'Search...'}}
                            value={{searchTerm || ''}}
                            onChange={{(e) => setSearchTerm(e.target.value)}}
                            style={{{{minWidth: '200px', margin: 0}}}}
                        />
                    )}}
                </div>
            );
        }};

        // Helper to get level badge with proper color
        const getLevelBadgeGeneric = (level) => {{
            const levelColors = DATA.levelColors || {{}};
            const color = levelColors[level] || '#666';
            return (
                <span style={{{{
                    background: color,
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600
                }}}}>{{level}}</span>
            );
        }};

        // Helper to filter data by level and league
        const filterByLevelLeague = (data, levelFilter, leagueFilter) => {{
            let result = data;
            if (levelFilter && levelFilter !== 'All') {{
                result = result.filter(d => (d.level || d.Level) === levelFilter);
            }}
            if (leagueFilter && leagueFilter !== 'All') {{
                result = result.filter(d => (d.league || d.League || d.conference || d.Conference) === leagueFilter);
            }}
            return result;
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
                                                    <th>3B</th>
                                                    <th>HR</th>
                                                    <th>RBI</th>
                                                    <th>BB</th>
                                                    <th>K</th>
                                                    <th>SB</th>
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
                                                        <td className="text-center">{{g.triples || 0}}</td>
                                                        <td className="text-center">{{g.hr || 0}}</td>
                                                        <td className="text-center">{{g.rbi}}</td>
                                                        <td className="text-center">{{g.bb}}</td>
                                                        <td className="text-center">{{g.k}}</td>
                                                        <td className="text-center">{{g.sb || 0}}</td>
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
                    <div className="value">{{data.allGames || data.totalGames}}</div>
                    <div className="label">Total Games</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.unifiedBatters || (data.totalBatters + (data.milbBatters || 0))}}</div>
                    <div className="label">Batters</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.unifiedPitchers || (data.totalPitchers + (data.milbPitchers || 0))}}</div>
                    <div className="label">Pitchers</div>
                </div>
                <div className="stat-card">
                    <div className="value">{{data.totalTeams}}</div>
                    <div className="label">Teams</div>
                </div>
                {{data.crossoverPlayers > 0 && (
                    <div className="stat-card">
                        <div className="value">{{data.crossoverPlayers}}</div>
                        <div className="label">Crossover Players</div>
                    </div>
                )}}
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

        const UnifiedGameLog = ({{ games }}) => {{
            const [levelFilter, setLevelFilter] = useState('All');
            const [leagueFilter, setLeagueFilter] = useState('All');
            const [searchTerm, setSearchTerm] = useState('');

            const filtered = useMemo(() => {{
                let result = filterByLevelLeague(games, levelFilter, leagueFilter);
                if (searchTerm) {{
                    const s = searchTerm.toLowerCase();
                    result = result.filter(g =>
                        g.away_team?.toLowerCase().includes(s) ||
                        g.home_team?.toLowerCase().includes(s) ||
                        g.venue?.toLowerCase().includes(s)
                    );
                }}
                return result;
            }}, [games, levelFilter, leagueFilter, searchTerm]);

            const TeamCell = ({{ team, teamId, level }}) => {{
                const historicalLogo = DATA.historicalTeamLogos && DATA.historicalTeamLogos[team];
                const ncaaEspnId = DATA.ncaaTeamLogos && DATA.ncaaTeamLogos[team];
                const partnerLogo = DATA.partnerLogos && DATA.partnerLogos[team];

                // Independent (partner) teams use custom logos
                if (level === 'Independent' && partnerLogo) {{
                    return (
                        <div style={{{{display: 'flex', alignItems: 'center', gap: '8px'}}}}>
                            <img src={{partnerLogo}} style={{{{width: '20px', height: '20px', objectFit: 'contain'}}}} onError={{(e) => e.target.style.display = 'none'}} />
                            <span>{{team}}</span>
                        </div>
                    );
                }}

                // Pro teams (any non-NCAA level) with team ID or historical logo
                if (level !== 'NCAA' && (teamId || historicalLogo)) {{
                    const logoSrc = historicalLogo || `https://www.mlbstatic.com/team-logos/${{teamId}}.svg`;
                    return (
                        <div style={{{{display: 'flex', alignItems: 'center', gap: '8px'}}}}>
                            <img src={{logoSrc}} style={{{{width: '20px', height: '20px', objectFit: 'contain'}}}} onError={{(e) => e.target.style.display = 'none'}} />
                            <span>{{team}}</span>
                        </div>
                    );
                }}

                if (level === 'NCAA' && ncaaEspnId) {{
                    return (
                        <div style={{{{display: 'flex', alignItems: 'center', gap: '8px'}}}}>
                            <img src={{`https://a.espncdn.com/i/teamlogos/ncaa/500/${{ncaaEspnId}}.png`}} style={{{{width: '20px', height: '20px', objectFit: 'contain'}}}} onError={{(e) => e.target.style.display = 'none'}} />
                            <span>{{team}}</span>
                        </div>
                    );
                }}

                return <span>{{team}}</span>;
            }};

            const levelColors = DATA.levelColors || {{}};

            return (
                <div className="panel">
                    <div className="panel-header"><h2>All Games ({{filtered.length}})</h2></div>
                    <LevelLeagueFilter levelFilter={{levelFilter}} setLevelFilter={{setLevelFilter}} leagueFilter={{leagueFilter}} setLeagueFilter={{setLeagueFilter}} data={{games}} showSearch={{true}} searchTerm={{searchTerm}} setSearchTerm={{setSearchTerm}} searchPlaceholder="Search teams or venues..." />
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Level</th>
                                    <th>Away</th>
                                    <th className="text-center">Score</th>
                                    <th>Home</th>
                                    <th>Venue</th>
                                </tr>
                            </thead>
                            <tbody>
                                {{filtered.map((g, i) => (
                                    <tr key={{i}} style={{{{borderLeft: `4px solid ${{levelColors[g.level] || '#ccc'}}`}}}}>
                                        <td>{{g.date}}</td>
                                        <td>{{getLevelBadgeGeneric(g.level)}}</td>
                                        <td><TeamCell team={{g.away_team}} teamId={{g.away_team_id}} level={{g.level}} /></td>
                                        <td className="text-center">{{g.away_score}} - {{g.home_score}}</td>
                                        <td><TeamCell team={{g.home_team}} teamId={{g.home_team_id}} level={{g.level}} /></td>
                                        <td>{{g.venue}}</td>
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
                                    <SortableHeader label="3B" sortKey="3B" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="HR" sortKey="HR" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="RBI" sortKey="RBI" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="BB" sortKey="BB" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="K" sortKey="K" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="SB" sortKey="SB" sortConfig={{sortConfig}} onSort={{requestSort}} />
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
                                        <td className="text-center">{{b['3B']}}</td>
                                        <td className="text-center">{{b.HR}}</td>
                                        <td className="text-center">{{b.RBI}}</td>
                                        <td className="text-center">{{b.BB}}</td>
                                        <td className="text-center">{{b.K}}</td>
                                        <td className="text-center">{{b.SB}}</td>
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

        const TeamRecords = ({{ teams }}) => {{
            const [levelFilter, setLevelFilter] = useState('All');
            const [leagueFilter, setLeagueFilter] = useState('All');

            const filtered = useMemo(() => {{
                if (!teams) return [];
                return filterByLevelLeague(teams, levelFilter, leagueFilter);
            }}, [teams, levelFilter, leagueFilter]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'W', direction: 'desc' }});

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Team Records ({{filtered.length}})</h2></div>
                    <LevelLeagueFilter
                        levelFilter={{levelFilter}}
                        setLevelFilter={{setLevelFilter}}
                        leagueFilter={{leagueFilter}}
                        setLeagueFilter={{setLeagueFilter}}
                        data={{teams}}
                    />
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Level" sortKey="Level" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Team" sortKey="Team" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="League" sortKey="League" sortConfig={{sortConfig}} onSort={{requestSort}} />
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
                                        <td>{{getLevelBadgeGeneric(t.Level)}}</td>
                                        <td>{{t.Team}}</td>
                                        <td>{{t.League}}</td>
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

        const MilestonesTable = ({{ title, data, columns, levelFilter, leagueFilter }}) => {{
            const filtered = useMemo(() => {{
                if (!data) return [];
                return filterByLevelLeague(data, levelFilter, leagueFilter);
            }}, [data, levelFilter, leagueFilter]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'Date', direction: 'desc' }});

            if (!filtered || filtered.length === 0) return null;
            const allColumns = ['Level', ...columns];
            return (
                <div className="panel" style={{{{marginTop: '16px'}}}}>
                    <div className="panel-header"><h2>{{title}} ({{filtered.length}})</h2></div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    {{allColumns.map(col => (
                                        <SortableHeader key={{col}} label={{col}} sortKey={{col}} sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    ))}}
                                </tr>
                            </thead>
                            <tbody>
                                {{items.slice(0, 50).map((row, i) => (
                                    <tr key={{i}}>
                                        {{allColumns.map(col => (
                                            <td key={{col}} className="text-center">
                                                {{col === 'Level' ? getLevelBadgeGeneric(row[col]) : row[col]}}
                                            </td>
                                        ))}}
                                    </tr>
                                ))}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const Checklist = ({{ checklist, milbChecklist }}) => {{
            const [expandedSection, setExpandedSection] = useState(null);
            const [expandedLeague, setExpandedLeague] = useState(null);
            const levelColors = DATA.levelColors || {{}};
            const levelOrder = DATA.levelOrder || ['NCAA', 'Triple-A', 'Double-A', 'High-A', 'Single-A', 'Independent'];

            // NCAA stats
            const ncaaStats = useMemo(() => {{
                let totalTeams = 0, totalSeen = 0, totalVisited = 0;
                Object.values(checklist || {{}}).forEach(c => {{
                    totalTeams += c.total;
                    totalSeen += c.seen;
                    totalVisited += c.visited;
                }});
                return {{ total: totalTeams, seen: totalSeen, visited: totalVisited }};
            }}, [checklist]);

            // Pro stats
            const proStats = useMemo(() => {{
                let totalTeams = 0, totalSeen = 0, totalVisited = 0;
                Object.values(milbChecklist || {{}}).forEach(c => {{
                    totalTeams += c.total;
                    totalSeen += c.seen;
                    totalVisited += c.visited;
                }});
                return {{ total: totalTeams, seen: totalSeen, visited: totalVisited }};
            }}, [milbChecklist]);

            const grandTotal = {{
                total: ncaaStats.total + proStats.total,
                seen: ncaaStats.seen + proStats.seen,
                visited: ncaaStats.visited + proStats.visited,
            }};

            const toggleSection = (key) => {{
                setExpandedSection(expandedSection === key ? null : key);
                setExpandedLeague(null);
            }};

            const toggleLeague = (key) => {{
                setExpandedLeague(expandedLeague === key ? null : key);
            }};

            // NCAA conferences sorted
            const ncaaConferences = useMemo(() => {{
                return Object.keys(checklist || {{}}).sort();
            }}, [checklist]);

            // Pro levels in order
            const proLevels = levelOrder.filter(l => l !== 'NCAA' && milbChecklist && milbChecklist[l]);

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Team Checklist</h2></div>
                    <div style={{{{padding: '20px'}}}}>
                        <div style={{{{display: 'flex', gap: '24px', marginBottom: '20px', flexWrap: 'wrap'}}}}>
                            <div style={{{{background: '#f0f0f0', padding: '12px 24px', borderRadius: '8px', textAlign: 'center'}}}}>
                                <div style={{{{fontSize: '24px', fontWeight: 'bold', color: '#333'}}}}>{{grandTotal.seen}}/{{grandTotal.total}}</div>
                                <div style={{{{fontSize: '14px', color: '#666'}}}}>Teams Seen</div>
                            </div>
                            <div style={{{{background: '#f0f0f0', padding: '12px 24px', borderRadius: '8px', textAlign: 'center'}}}}>
                                <div style={{{{fontSize: '24px', fontWeight: 'bold', color: '#27ae60'}}}}>{{grandTotal.visited}}</div>
                                <div style={{{{fontSize: '14px', color: '#666'}}}}>Stadiums Visited</div>
                            </div>
                            <div style={{{{background: '#f0f0f0', padding: '12px 24px', borderRadius: '8px', textAlign: 'center'}}}}>
                                <div style={{{{fontSize: '24px', fontWeight: 'bold', color: '#333'}}}}>{{grandTotal.total > 0 ? Math.round((grandTotal.seen / grandTotal.total) * 100) : 0}}%</div>
                                <div style={{{{fontSize: '14px', color: '#666'}}}}>Progress</div>
                            </div>
                        </div>

                        {{/* Per-level summary */}}
                        <div style={{{{display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap'}}}}>
                            <div style={{{{padding: '8px 16px', borderRadius: '6px', background: levelColors['NCAA'] || '#28a745', color: 'white', fontSize: '13px'}}}}>
                                NCAA: {{ncaaStats.seen}}/{{ncaaStats.total}}
                            </div>
                            {{proLevels.map(level => {{
                                const data = milbChecklist[level] || {{ total: 0, seen: 0 }};
                                return (
                                    <div key={{level}} style={{{{padding: '8px 16px', borderRadius: '6px', background: levelColors[level] || '#666', color: 'white', fontSize: '13px'}}}}>
                                        {{level}}: {{data.seen}}/{{data.total}}
                                    </div>
                                );
                            }})}}
                        </div>

                        <div style={{{{display: 'flex', flexDirection: 'column', gap: '8px'}}}}>
                            {{/* NCAA Section */}}
                            <div>
                                <div
                                    onClick={{() => toggleSection('NCAA')}}
                                    style={{{{
                                        padding: '14px 18px',
                                        background: '#f8f9fa',
                                        borderRadius: expandedSection === 'NCAA' ? '8px 8px 0 0' : '8px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        border: '1px solid #dee2e6',
                                        borderBottom: expandedSection === 'NCAA' ? 'none' : '1px solid #dee2e6',
                                        borderLeft: `4px solid ${{levelColors['NCAA'] || '#28a745'}}`
                                    }}}}
                                >
                                    <div style={{{{display: 'flex', alignItems: 'center', gap: '12px'}}}}>
                                        <span style={{{{fontSize: '18px'}}}}>{{expandedSection === 'NCAA' ? '▼' : '▶'}}</span>
                                        {{getLevelBadgeGeneric('NCAA')}}
                                        <span style={{{{fontWeight: 600, fontSize: '16px'}}}}>NCAA</span>
                                    </div>
                                    <div style={{{{display: 'flex', alignItems: 'center', gap: '16px'}}}}>
                                        <span style={{{{color: '#666'}}}}>{{ncaaStats.seen}}/{{ncaaStats.total}} seen</span>
                                        <div style={{{{width: '100px', height: '8px', background: '#e0e0e0', borderRadius: '4px', overflow: 'hidden'}}}}>
                                            <div style={{{{width: `${{ncaaStats.total > 0 ? Math.round((ncaaStats.seen / ncaaStats.total) * 100) : 0}}%`, height: '100%', background: levelColors['NCAA'] || '#28a745', borderRadius: '4px'}}}}></div>
                                        </div>
                                        <span style={{{{fontWeight: 500, minWidth: '40px'}}}}>{{ncaaStats.total > 0 ? Math.round((ncaaStats.seen / ncaaStats.total) * 100) : 0}}%</span>
                                    </div>
                                </div>
                                {{expandedSection === 'NCAA' && (
                                    <div style={{{{border: '1px solid #dee2e6', borderTop: 'none', borderRadius: '0 0 8px 8px', background: 'white', padding: '8px'}}}}>
                                        {{ncaaConferences.map(conf => {{
                                            const confData = checklist[conf] || {{ teams: [], total: 0, seen: 0, visited: 0, teamStatus: {{}} }};
                                            const isLeagueExpanded = expandedLeague === 'ncaa-' + conf;
                                            const pct = confData.total > 0 ? Math.round((confData.seen / confData.total) * 100) : 0;
                                            return (
                                                <div key={{conf}} style={{{{marginBottom: '4px'}}}}>
                                                    <div
                                                        onClick={{() => toggleLeague('ncaa-' + conf)}}
                                                        style={{{{
                                                            padding: '10px 14px',
                                                            background: '#fafafa',
                                                            borderRadius: isLeagueExpanded ? '6px 6px 0 0' : '6px',
                                                            cursor: 'pointer',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'space-between',
                                                        }}}}
                                                    >
                                                        <div style={{{{display: 'flex', alignItems: 'center', gap: '8px'}}}}>
                                                            <span style={{{{fontSize: '14px'}}}}>{{isLeagueExpanded ? '▼' : '▶'}}</span>
                                                            <span style={{{{fontWeight: 500}}}}>{{conf}}</span>
                                                        </div>
                                                        <div style={{{{display: 'flex', alignItems: 'center', gap: '12px'}}}}>
                                                            <span style={{{{fontSize: '13px', color: '#666'}}}}>{{confData.seen}}/{{confData.total}}</span>
                                                            <div style={{{{width: '60px', height: '6px', background: '#e0e0e0', borderRadius: '3px', overflow: 'hidden'}}}}>
                                                                <div style={{{{width: `${{pct}}%`, height: '100%', background: '#27ae60', borderRadius: '3px'}}}}></div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    {{isLeagueExpanded && (
                                                        <div style={{{{padding: '12px', background: 'white', borderRadius: '0 0 6px 6px'}}}}>
                                                            <div style={{{{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px'}}}}>
                                                                {{confData.teams.sort().map(team => {{
                                                                    const status = confData.teamStatus[team] || 'none';
                                                                    return (
                                                                        <div key={{team}} style={{{{
                                                                            padding: '8px 12px',
                                                                            borderRadius: '6px',
                                                                            background: status === 'home' ? '#d4edda' : status === 'away' ? '#cce5ff' : '#f8f9fa',
                                                                            border: `1px solid ${{status === 'home' ? '#28a745' : status === 'away' ? '#007bff' : '#dee2e6'}}`,
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: '8px'
                                                                        }}}}>
                                                                            <span style={{{{
                                                                                width: '10px',
                                                                                height: '10px',
                                                                                borderRadius: '50%',
                                                                                background: status === 'home' ? '#28a745' : status === 'away' ? '#007bff' : '#ccc'
                                                                            }}}}></span>
                                                                            <span style={{{{flex: 1, fontWeight: status !== 'none' ? 500 : 400, fontSize: '14px'}}}}>{{team}}</span>
                                                                        </div>
                                                                    );
                                                                }})}}
                                                            </div>
                                                        </div>
                                                    )}}
                                                </div>
                                            );
                                        }})}}
                                    </div>
                                )}}
                            </div>

                            {{/* Pro level sections */}}
                            {{proLevels.map(level => {{
                                const levelData = milbChecklist[level] || {{ teams: [], total: 0, seen: 0, visited: 0, teamStatus: {{}}, leagues: {{}} }};
                                const isExpanded = expandedSection === level;
                                const levelPct = levelData.total > 0 ? Math.round((levelData.seen / levelData.total) * 100) : 0;
                                const leagues = levelData.leagues ? Object.keys(levelData.leagues).sort() : [];
                                return (
                                    <div key={{level}}>
                                        <div
                                            onClick={{() => toggleSection(level)}}
                                            style={{{{
                                                padding: '14px 18px',
                                                background: '#f8f9fa',
                                                borderRadius: isExpanded ? '8px 8px 0 0' : '8px',
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'space-between',
                                                border: '1px solid #dee2e6',
                                                borderBottom: isExpanded ? 'none' : '1px solid #dee2e6',
                                                borderLeft: `4px solid ${{levelColors[level] || '#666'}}`
                                            }}}}
                                        >
                                            <div style={{{{display: 'flex', alignItems: 'center', gap: '12px'}}}}>
                                                <span style={{{{fontSize: '18px'}}}}>{{isExpanded ? '▼' : '▶'}}</span>
                                                {{getLevelBadgeGeneric(level)}}
                                                <span style={{{{fontWeight: 600, fontSize: '16px'}}}}>{{level}}</span>
                                            </div>
                                            <div style={{{{display: 'flex', alignItems: 'center', gap: '16px'}}}}>
                                                <span style={{{{color: '#666'}}}}>{{levelData.seen}}/{{levelData.total}} seen</span>
                                                <div style={{{{width: '100px', height: '8px', background: '#e0e0e0', borderRadius: '4px', overflow: 'hidden'}}}}>
                                                    <div style={{{{width: `${{levelPct}}%`, height: '100%', background: levelColors[level] || '#666', borderRadius: '4px'}}}}></div>
                                                </div>
                                                <span style={{{{fontWeight: 500, minWidth: '40px'}}}}>{{levelPct}}%</span>
                                            </div>
                                        </div>
                                        {{isExpanded && (
                                            <div style={{{{border: '1px solid #dee2e6', borderTop: 'none', borderRadius: '0 0 8px 8px', background: 'white', padding: '8px'}}}}>
                                                {{leagues.length > 1 ? leagues.map(league => {{
                                                    const lgData = levelData.leagues[league] || {{ teams: [], total: 0, seen: 0, visited: 0, teamStatus: {{}} }};
                                                    const isLgExpanded = expandedLeague === level + '-' + league;
                                                    const lgPct = lgData.total > 0 ? Math.round((lgData.seen / lgData.total) * 100) : 0;
                                                    return (
                                                        <div key={{league}} style={{{{marginBottom: '4px'}}}}>
                                                            <div
                                                                onClick={{() => toggleLeague(level + '-' + league)}}
                                                                style={{{{
                                                                    padding: '10px 14px',
                                                                    background: '#fafafa',
                                                                    borderRadius: isLgExpanded ? '6px 6px 0 0' : '6px',
                                                                    cursor: 'pointer',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    justifyContent: 'space-between',
                                                                }}}}
                                                            >
                                                                <div style={{{{display: 'flex', alignItems: 'center', gap: '8px'}}}}>
                                                                    <span style={{{{fontSize: '14px'}}}}>{{isLgExpanded ? '▼' : '▶'}}</span>
                                                                    <span style={{{{fontWeight: 500}}}}>{{league}}</span>
                                                                </div>
                                                                <div style={{{{display: 'flex', alignItems: 'center', gap: '12px'}}}}>
                                                                    <span style={{{{fontSize: '13px', color: '#666'}}}}>{{lgData.seen}}/{{lgData.total}}</span>
                                                                    <div style={{{{width: '60px', height: '6px', background: '#e0e0e0', borderRadius: '3px', overflow: 'hidden'}}}}>
                                                                        <div style={{{{width: `${{lgPct}}%`, height: '100%', background: levelColors[level] || '#666', borderRadius: '3px'}}}}></div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            {{isLgExpanded && (
                                                                <div style={{{{padding: '12px', background: 'white', borderRadius: '0 0 6px 6px'}}}}>
                                                                    <div style={{{{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px'}}}}>
                                                                        {{lgData.teams.sort((a, b) => a.team.localeCompare(b.team)).map(({{ team, venue, teamId, logo }}) => {{
                                                                            const status = lgData.teamStatus[team] || 'none';
                                                                            return (
                                                                                <div key={{team}} style={{{{
                                                                                    padding: '8px 12px',
                                                                                    borderRadius: '6px',
                                                                                    background: status === 'home' ? '#fff3e6' : status === 'away' ? '#e6f3ff' : '#f8f9fa',
                                                                                    border: `1px solid ${{status === 'home' ? levelColors[level] || '#ff6b35' : status === 'away' ? '#007bff' : '#dee2e6'}}`,
                                                                                    display: 'flex',
                                                                                    alignItems: 'center',
                                                                                    gap: '10px'
                                                                                }}}}>
                                                                                    <img
                                                                                        src={{logo}}
                                                                                        style={{{{width: '24px', height: '24px', objectFit: 'contain'}}}}
                                                                                        onError={{(e) => {{ e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}}}
                                                                                    />
                                                                                    <span style={{{{display: 'none', width: '24px', height: '24px', alignItems: 'center', justifyContent: 'center', fontSize: '16px'}}}}>⚾</span>
                                                                                    <div style={{{{flex: 1}}}}>
                                                                                        <div style={{{{fontWeight: status !== 'none' ? 500 : 400, fontSize: '14px'}}}}>{{team}}</div>
                                                                                        <div style={{{{fontSize: '11px', color: '#666'}}}}>{{venue}}</div>
                                                                                    </div>
                                                                                </div>
                                                                            );
                                                                        }})}}
                                                                    </div>
                                                                </div>
                                                            )}}
                                                        </div>
                                                    );
                                                }}) : (
                                                    <div style={{{{padding: '12px'}}}}>
                                                        <div style={{{{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px'}}}}>
                                                            {{levelData.teams.sort((a, b) => a.team.localeCompare(b.team)).map(({{ team, venue, teamId, logo }}) => {{
                                                                const status = levelData.teamStatus[team] || 'none';
                                                                return (
                                                                    <div key={{team}} style={{{{
                                                                        padding: '8px 12px',
                                                                        borderRadius: '6px',
                                                                        background: status === 'home' ? '#fff3e6' : status === 'away' ? '#e6f3ff' : '#f8f9fa',
                                                                        border: `1px solid ${{status === 'home' ? levelColors[level] || '#ff6b35' : status === 'away' ? '#007bff' : '#dee2e6'}}`,
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        gap: '10px'
                                                                    }}}}>
                                                                        <img
                                                                            src={{logo}}
                                                                            style={{{{width: '24px', height: '24px', objectFit: 'contain'}}}}
                                                                            onError={{(e) => {{ e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}}}
                                                                        />
                                                                        <span style={{{{display: 'none', width: '24px', height: '24px', alignItems: 'center', justifyContent: 'center', fontSize: '16px'}}}}>⚾</span>
                                                                        <div style={{{{flex: 1}}}}>
                                                                            <div style={{{{fontWeight: status !== 'none' ? 500 : 400, fontSize: '14px'}}}}>{{team}}</div>
                                                                            <div style={{{{fontSize: '11px', color: '#666'}}}}>{{venue}}</div>
                                                                        </div>
                                                                    </div>
                                                                );
                                                            }})}}
                                                        </div>
                                                    </div>
                                                )}}
                                            </div>
                                        )}}
                                    </div>
                                );
                            }})}}
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

        const SchoolMap = ({{ stadiums, teamsSeenHome, teamsSeenAway, checklist, milbStadiums, milbVenuesVisited, partnerStadiums, partnerVenuesVisited }}) => {{
            const mapRef = useRef(null);
            const mapInstance = useRef(null);
            const markersRef = useRef([]);
            const [selectedConf, setSelectedConf] = useState('All');
            const [filter, setFilter] = useState('all');
            const [showMilb, setShowMilb] = useState(true);
            const [showPartner, setShowPartner] = useState(true);

            const hasMilbData = milbStadiums && Object.keys(milbStadiums).length > 0;
            const hasPartnerData = partnerStadiums && Object.keys(partnerStadiums).length > 0;

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

                // Get NCAA teams to show
                let teamsToShow = [];
                if (selectedConf === 'All') {{
                    Object.values(checklist).forEach(c => {{
                        teamsToShow.push(...c.teams);
                    }});
                }} else if (selectedConf === 'MiLB') {{
                    // MiLB only mode - skip NCAA teams
                    teamsToShow = [];
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

                // Add NCAA markers
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

                // Add MiLB markers if enabled
                if (showMilb && milbStadiums && (selectedConf === 'All' || selectedConf === 'MiLB')) {{
                    Object.entries(milbStadiums).forEach(([venueName, info]) => {{
                        const isVisited = milbVenuesVisited && milbVenuesVisited.includes(venueName);

                        // Apply filter
                        if (filter === 'visited' && !isVisited) return;
                        if (filter === 'unseen' && isVisited) return;
                        if (filter === 'seen' && !isVisited) return;

                        const opacity = isVisited ? 1.0 : 0.5;
                        const size = isVisited ? 28 : 22;

                        const teamInitial = info.team.charAt(0);
                        const icon = L.divIcon({{
                            className: 'logo-marker',
                            html: `<div style="width: ${{size}}px; height: ${{size}}px; opacity: ${{opacity}}; background: white; border-radius: 50%; padding: 2px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); ${{isVisited ? 'border: 2px solid #ff6b35;' : ''}} display: flex; align-items: center; justify-content: center;">
                                <img src="${{info.logo}}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
                                <span style="display: none; font-weight: bold; font-size: ${{size*0.5}}px; color: #333; align-items: center; justify-content: center; width: 100%; height: 100%;">⚾</span>
                            </div>`,
                            iconSize: [size, size],
                            iconAnchor: [size/2, size/2]
                        }});

                        const marker = L.marker([info.lat, info.lng], {{ icon }})
                            .bindPopup(`<div style="text-align:center;"><img src="${{info.logo}}" style="width:50px;height:50px;margin-bottom:8px;" onerror="this.outerHTML='<span style=\\'font-size:40px;\\'>⚾</span>'" /><br><strong>${{info.team}}</strong><br>${{venueName}}<br><em>MiLB (${{info.level}}) - ${{isVisited ? 'Visited' : 'Not Visited'}}</em></div>`)
                            .addTo(mapInstance.current);
                        markersRef.current.push(marker);
                    }});
                }}

                // Add Partner (independent league) markers if enabled
                if (showPartner && partnerStadiums && (selectedConf === 'All' || selectedConf === 'Partner')) {{
                    Object.entries(partnerStadiums).forEach(([stadiumName, info]) => {{
                        const isVisited = partnerVenuesVisited && partnerVenuesVisited.includes(stadiumName);

                        // Apply filter
                        if (filter === 'visited' && !isVisited) return;
                        if (filter === 'unseen' && isVisited) return;
                        if (filter === 'seen' && !isVisited) return;

                        const opacity = isVisited ? 1.0 : 0.5;
                        const size = isVisited ? 26 : 20;

                        const icon = L.divIcon({{
                            className: 'logo-marker',
                            html: `<div style="width: ${{size}}px; height: ${{size}}px; opacity: ${{opacity}}; background: white; border-radius: 50%; padding: 2px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); ${{isVisited ? 'border: 2px solid #9c27b0;' : ''}} display: flex; align-items: center; justify-content: center;">
                                <img src="${{info.logo}}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
                                <span style="display: none; font-weight: bold; font-size: ${{size*0.5}}px; color: #333; align-items: center; justify-content: center; width: 100%; height: 100%;">⚾</span>
                            </div>`,
                            iconSize: [size, size],
                            iconAnchor: [size/2, size/2]
                        }});

                        const marker = L.marker([info.lat, info.lng], {{ icon }})
                            .bindPopup(`<div style="text-align:center;"><img src="${{info.logo}}" style="width:50px;height:50px;margin-bottom:8px;" onerror="this.outerHTML='<span style=\\'font-size:40px;\\'>⚾</span>'" /><br><strong>${{info.team}}</strong><br>${{stadiumName}}<br><em>${{info.league}} - ${{isVisited ? 'Visited' : 'Not Visited'}}</em></div>`)
                            .addTo(mapInstance.current);
                        markersRef.current.push(marker);
                    }});
                }}
            }}, [stadiums, teamsSeenHome, teamsSeenAway, selectedConf, filter, checklist, showMilb, milbStadiums, milbVenuesVisited, showPartner, partnerStadiums, partnerVenuesVisited]);

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Stadium Map</h2></div>
                    <div style={{{{padding: '16px'}}}}>
                        <div style={{{{marginBottom: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center'}}}}>
                            <select
                                className="search-box"
                                style={{{{width: 'auto', minWidth: '150px', margin: 0}}}}
                                value={{selectedConf}}
                                onChange={{(e) => setSelectedConf(e.target.value)}}
                            >
                                {{conferences.map(c => <option key={{c}} value={{c}}>{{c}}</option>)}}
                                {{hasMilbData && <option value="MiLB">MiLB Only</option>}}
                            </select>
                            <select
                                className="search-box"
                                style={{{{width: 'auto', minWidth: '150px', margin: 0}}}}
                                value={{filter}}
                                onChange={{(e) => setFilter(e.target.value)}}
                            >
                                <option value="all">All Venues</option>
                                <option value="seen">Seen</option>
                                <option value="visited">Visited</option>
                                <option value="unseen">Not Seen</option>
                            </select>
                            {{hasMilbData && (
                                <label style={{{{display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer'}}}}>
                                    <input
                                        type="checkbox"
                                        checked={{showMilb}}
                                        onChange={{(e) => setShowMilb(e.target.checked)}}
                                    />
                                    Show MiLB
                                </label>
                            )}}
                            {{hasPartnerData && (
                                <label style={{{{display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer'}}}}>
                                    <input
                                        type="checkbox"
                                        checked={{showPartner}}
                                        onChange={{(e) => setShowPartner(e.target.checked)}}
                                    />
                                    Show Partner
                                </label>
                            )}}
                        </div>
                        <div ref={{mapRef}} style={{{{height: '500px', borderRadius: '8px', border: '1px solid #ddd'}}}}></div>
                        <div style={{{{marginTop: '12px', display: 'flex', gap: '16px', fontSize: '14px', color: '#666', flexWrap: 'wrap', alignItems: 'center'}}}}>
                            <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#28a745', marginRight: '4px'}}}}></span> NCAA Visited</span>
                            <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#007bff', marginRight: '4px'}}}}></span> NCAA Seen (Away)</span>
                            <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: '#999', marginRight: '4px'}}}}></span> NCAA Not Seen</span>
                            {{hasMilbData && (
                                <span><span style={{{{display: 'inline-block', width: '16px', height: '16px', borderRadius: '50%', border: '2px solid #ff6b35', background: 'white', marginRight: '4px'}}}}></span> MiLB Visited (logo)</span>
                            )}}
                            {{hasMilbData && (
                                <span><span style={{{{display: 'inline-block', width: '14px', height: '14px', borderRadius: '50%', background: 'white', opacity: 0.5, marginRight: '4px', boxShadow: '0 1px 3px rgba(0,0,0,0.2)'}}}}></span> MiLB (logo)</span>
                            )}}
                            {{hasPartnerData && (
                                <span><span style={{{{display: 'inline-block', width: '14px', height: '14px', borderRadius: '50%', border: '2px solid #9c27b0', background: 'white', marginRight: '4px'}}}}></span> Partner Visited (logo)</span>
                            )}}
                            {{hasPartnerData && (
                                <span><span style={{{{display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', background: 'white', opacity: 0.5, marginRight: '4px', boxShadow: '0 1px 3px rgba(0,0,0,0.2)'}}}}></span> Partner (logo)</span>
                            )}}
                        </div>
                    </div>
                </div>
            );
        }};

        const CalendarView = ({{ games }}) => {{
            const [selectedDay, setSelectedDay] = useState(null);
            const [levelFilter, setLevelFilter] = useState('All');
            const [leagueFilter, setLeagueFilter] = useState('All');

            const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

            // Filter games by level and league
            const filteredGames = useMemo(() => {{
                return filterByLevelLeague(games || [], levelFilter, leagueFilter);
            }}, [games, levelFilter, leagueFilter]);

            // Group games by month-day (ignoring year) - uses unified format
            const gamesByDay = useMemo(() => {{
                const map = {{}};
                filteredGames.forEach(game => {{
                    const date = game.date;
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
            }}, [filteredGames]);

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

            // Get team logo
            const getTeamLogo = (team, teamId, level) => {{
                const historicalLogo = DATA.historicalTeamLogos && DATA.historicalTeamLogos[team];
                const ncaaEspnId = DATA.ncaaTeamLogos && DATA.ncaaTeamLogos[team];
                const partnerLogo = DATA.partnerLogos && DATA.partnerLogos[team];

                if (level === 'Independent' && partnerLogo) {{
                    return <img src={{partnerLogo}} style={{{{width: '16px', height: '16px', objectFit: 'contain', marginRight: '6px'}}}} onError={{(e) => e.target.style.display = 'none'}} />;
                }}
                if (level !== 'NCAA' && (teamId || historicalLogo)) {{
                    const logoSrc = historicalLogo || `https://www.mlbstatic.com/team-logos/${{teamId}}.svg`;
                    return <img src={{logoSrc}} style={{{{width: '16px', height: '16px', objectFit: 'contain', marginRight: '6px'}}}} onError={{(e) => e.target.style.display = 'none'}} />;
                }}
                if (level === 'NCAA' && ncaaEspnId) {{
                    return <img src={{`https://a.espncdn.com/i/teamlogos/ncaa/500/${{ncaaEspnId}}.png`}} style={{{{width: '16px', height: '16px', objectFit: 'contain', marginRight: '6px'}}}} onError={{(e) => e.target.style.display = 'none'}} />;
                }}
                return null;
            }};

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Games by Date (All Years)</h2></div>
                    <div style={{{{padding: '20px'}}}}>
                        <div style={{{{marginBottom: '16px', display: 'flex', gap: '12px', alignItems: 'center'}}}}>
                            <LevelLeagueFilter
                                levelFilter={{levelFilter}}
                                setLevelFilter={{(v) => {{ setLevelFilter(v); setSelectedDay(null); }}}}
                                leagueFilter={{leagueFilter}}
                                setLeagueFilter={{setLeagueFilter}}
                                data={{games}}
                            />
                            <span style={{{{fontSize: '14px', color: '#666'}}}}>{{filteredGames.length}} games</span>
                        </div>

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

                        <div style={{{{marginBottom: '16px', display: 'flex', gap: '16px', fontSize: '14px', alignItems: 'center', flexWrap: 'wrap'}}}}>
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
                            <span style={{{{marginLeft: 'auto', display: 'flex', gap: '12px'}}}}>
                                {{(DATA.levelOrder || []).map(l => (
                                    <span key={{l}} style={{{{display: 'flex', alignItems: 'center', gap: '4px'}}}}>
                                        <span style={{{{width: '12px', height: '12px', borderRadius: '3px', background: (DATA.levelColors || {{}})[l] || '#666'}}}}></span>
                                        <span style={{{{fontSize: '12px', color: '#666'}}}}>{{l}}</span>
                                    </span>
                                ))}}
                            </span>
                        </div>

                        {{selectedDay && selectedGames.length > 0 && (
                            <div style={{{{marginTop: '16px'}}}}>
                                <h4 style={{{{margin: '0 0 12px 0', color: '#1e3a5f'}}}}>
                                    Games on {{MONTHS[parseInt(selectedDay.split('-')[0], 10) - 1]}} {{selectedDay.split('-')[1]}} ({{selectedGames.length}})
                                </h4>
                                <div className="table-container" style={{{{maxHeight: '400px'}}}}>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Year</th>
                                                <th>Level</th>
                                                <th>Away</th>
                                                <th className="text-center">Score</th>
                                                <th>Home</th>
                                                <th>Venue</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {{selectedGames.sort((a, b) => {{
                                                const yearA = a.date?.split('/')[2] || '0';
                                                const yearB = b.date?.split('/')[2] || '0';
                                                return yearB.localeCompare(yearA);
                                            }}).map((g, i) => (
                                                <tr key={{i}} style={{{{borderLeft: `4px solid ${{(DATA.levelColors || {{}})[g.level] || '#ccc'}}`}}}}>
                                                    <td>{{g.date?.split('/')[2]}}</td>
                                                    <td>{{getLevelBadgeGeneric(g.level)}}</td>
                                                    <td>
                                                        <div style={{{{display: 'flex', alignItems: 'center'}}}}>
                                                            {{getTeamLogo(g.away_team, g.away_team_id, g.level)}}
                                                            <span>{{g.away_team}}</span>
                                                        </div>
                                                    </td>
                                                    <td className="text-center">{{g.away_score}} - {{g.home_score}}</td>
                                                    <td>
                                                        <div style={{{{display: 'flex', alignItems: 'center'}}}}>
                                                            {{getTeamLogo(g.home_team, g.home_team_id, g.level)}}
                                                            <span>{{g.home_team}}</span>
                                                        </div>
                                                    </td>
                                                    <td>{{g.venue}}</td>
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

        const UnifiedBattersTable = ({{ batters }}) => {{
            const [levelFilter, setLevelFilter] = useState('All');
            const [leagueFilter, setLeagueFilter] = useState('All');
            const [searchTerm, setSearchTerm] = useState('');

            const filtered = useMemo(() => {{
                if (!batters) return [];
                let result = filterByLevelLeague(batters, levelFilter, leagueFilter);
                if (searchTerm) {{
                    const s = searchTerm.toLowerCase();
                    result = result.filter(b =>
                        b.name?.toLowerCase().includes(s) ||
                        b.team?.toLowerCase().includes(s)
                    );
                }}
                return result;
            }}, [batters, levelFilter, leagueFilter, searchTerm]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'h', direction: 'desc' }});

            const getTeamLogo = (player) => {{
                if (player.level === 'NCAA') {{
                    const espnId = DATA.ncaaTeamLogos && DATA.ncaaTeamLogos[player.team];
                    if (espnId) return `https://a.espncdn.com/i/teamlogos/ncaa/500/${{espnId}}.png`;
                    return null;
                }}
                if (player.level === 'Independent') {{
                    const partnerLogo = DATA.partnerLogos && DATA.partnerLogos[player.team];
                    if (partnerLogo) return partnerLogo;
                }}
                if (player.team_id) {{
                    return `https://www.mlbstatic.com/team-logos/${{player.team_id}}.svg`;
                }}
                return null;
            }};

            if (!batters || batters.length === 0) {{
                return (
                    <div className="panel">
                        <div className="panel-header"><h2>All Batters</h2></div>
                        <div style={{{{padding: '20px', textAlign: 'center', color: '#666'}}}}>
                            No batting data available.
                        </div>
                    </div>
                );
            }}

            return (
                <div className="panel">
                    <div className="panel-header">
                        <h2>All Batters ({{filtered.length}})</h2>
                    </div>
                    <LevelLeagueFilter
                        levelFilter={{levelFilter}}
                        setLevelFilter={{setLevelFilter}}
                        leagueFilter={{leagueFilter}}
                        setLeagueFilter={{setLeagueFilter}}
                        data={{batters}}
                        showSearch={{true}}
                        searchTerm={{searchTerm}}
                        setSearchTerm={{setSearchTerm}}
                        searchPlaceholder="Search by name or team..."
                    />
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Level" sortKey="level" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Name" sortKey="name" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Team" sortKey="team" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="G" sortKey="g" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="AB" sortKey="ab" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="R" sortKey="r" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="H" sortKey="h" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="2B" sortKey="doubles" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="3B" sortKey="triples" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="HR" sortKey="hr" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="RBI" sortKey="rbi" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="BB" sortKey="bb" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="K" sortKey="k" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="SB" sortKey="sb" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="AVG" sortKey="avg" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                </tr>
                            </thead>
                            <tbody>
                                {{items.slice(0, 200).map((b, i) => {{
                                    const logo = getTeamLogo(b);
                                    return (
                                        <tr key={{i}}>
                                            <td>{{getLevelBadgeGeneric(b.level)}}</td>
                                            <td>
                                                {{b.bref_id ? (
                                                    <a href={{BREF_BASE + b.bref_id}} target="_blank" style={{{{color: '#1e3a5f', textDecoration: 'none'}}}}>
                                                        {{b.name}} <span style={{{{fontSize: '10px'}}}}>↗</span>
                                                    </a>
                                                ) : b.name}}
                                            </td>
                                            <td>
                                                <div style={{{{display: 'flex', alignItems: 'center', gap: '6px'}}}}>
                                                    {{logo && (
                                                        <img
                                                            src={{logo}}
                                                            alt=""
                                                            style={{{{width: '20px', height: '20px', objectFit: 'contain'}}}}
                                                            onError={{(e) => {{ e.target.style.display = 'none'; }}}}
                                                        />
                                                    )}}
                                                    {{b.team}}
                                                </div>
                                            </td>
                                            <td className="text-center">{{b.g}}</td>
                                            <td className="text-center">{{b.ab}}</td>
                                            <td className="text-center">{{b.r}}</td>
                                            <td className="text-center">{{b.h}}</td>
                                            <td className="text-center">{{b.doubles}}</td>
                                            <td className="text-center">{{b.triples}}</td>
                                            <td className="text-center">{{b.hr}}</td>
                                            <td className="text-center">{{b.rbi}}</td>
                                            <td className="text-center">{{b.bb}}</td>
                                            <td className="text-center">{{b.k}}</td>
                                            <td className="text-center">{{b.sb}}</td>
                                            <td className="text-center">{{b.avg}}</td>
                                        </tr>
                                    );
                                }})}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const UnifiedPitchersTable = ({{ pitchers }}) => {{
            const [levelFilter, setLevelFilter] = useState('All');
            const [leagueFilter, setLeagueFilter] = useState('All');
            const [searchTerm, setSearchTerm] = useState('');

            const filtered = useMemo(() => {{
                if (!pitchers) return [];
                let result = filterByLevelLeague(pitchers, levelFilter, leagueFilter);
                if (searchTerm) {{
                    const s = searchTerm.toLowerCase();
                    result = result.filter(p =>
                        p.name?.toLowerCase().includes(s) ||
                        p.team?.toLowerCase().includes(s)
                    );
                }}
                return result;
            }}, [pitchers, levelFilter, leagueFilter, searchTerm]);

            const {{ items, sortConfig, requestSort }} = useSortableData(filtered, {{ key: 'k', direction: 'desc' }});

            const getTeamLogo = (player) => {{
                if (player.level === 'NCAA') {{
                    const espnId = DATA.ncaaTeamLogos && DATA.ncaaTeamLogos[player.team];
                    if (espnId) return `https://a.espncdn.com/i/teamlogos/ncaa/500/${{espnId}}.png`;
                    return null;
                }}
                if (player.level === 'Independent') {{
                    const partnerLogo = DATA.partnerLogos && DATA.partnerLogos[player.team];
                    if (partnerLogo) return partnerLogo;
                }}
                if (player.team_id) {{
                    return `https://www.mlbstatic.com/team-logos/${{player.team_id}}.svg`;
                }}
                return null;
            }};

            if (!pitchers || pitchers.length === 0) {{
                return (
                    <div className="panel">
                        <div className="panel-header"><h2>All Pitchers</h2></div>
                        <div style={{{{padding: '20px', textAlign: 'center', color: '#666'}}}}>
                            No pitching data available.
                        </div>
                    </div>
                );
            }}

            return (
                <div className="panel">
                    <div className="panel-header">
                        <h2>All Pitchers ({{filtered.length}})</h2>
                    </div>
                    <LevelLeagueFilter
                        levelFilter={{levelFilter}}
                        setLevelFilter={{setLevelFilter}}
                        leagueFilter={{leagueFilter}}
                        setLeagueFilter={{setLeagueFilter}}
                        data={{pitchers}}
                        showSearch={{true}}
                        searchTerm={{searchTerm}}
                        setSearchTerm={{setSearchTerm}}
                        searchPlaceholder="Search by name or team..."
                    />
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <SortableHeader label="Level" sortKey="level" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Name" sortKey="name" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="Team" sortKey="team" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="G" sortKey="g" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="IP" sortKey="ip" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="H" sortKey="h" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="R" sortKey="r" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="ER" sortKey="er" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="BB" sortKey="bb" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="K" sortKey="k" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="HR" sortKey="hr" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                    <SortableHeader label="ERA" sortKey="era" sortConfig={{sortConfig}} onSort={{requestSort}} />
                                </tr>
                            </thead>
                            <tbody>
                                {{items.slice(0, 200).map((p, i) => {{
                                    const logo = getTeamLogo(p);
                                    return (
                                        <tr key={{i}}>
                                            <td>{{getLevelBadgeGeneric(p.level)}}</td>
                                            <td>
                                                {{p.bref_id ? (
                                                    <a href={{BREF_BASE + p.bref_id}} target="_blank" style={{{{color: '#1e3a5f', textDecoration: 'none'}}}}>
                                                        {{p.name}} <span style={{{{fontSize: '10px'}}}}>↗</span>
                                                    </a>
                                                ) : p.name}}
                                            </td>
                                            <td>
                                                <div style={{{{display: 'flex', alignItems: 'center', gap: '6px'}}}}>
                                                    {{logo && (
                                                        <img
                                                            src={{logo}}
                                                            alt=""
                                                            style={{{{width: '20px', height: '20px', objectFit: 'contain'}}}}
                                                            onError={{(e) => {{ e.target.style.display = 'none'; }}}}
                                                        />
                                                    )}}
                                                    {{p.team}}
                                                </div>
                                            </td>
                                            <td className="text-center">{{p.g}}</td>
                                            <td className="text-center">{{p.ip}}</td>
                                            <td className="text-center">{{p.h}}</td>
                                            <td className="text-center">{{p.r}}</td>
                                            <td className="text-center">{{p.er}}</td>
                                            <td className="text-center">{{p.bb}}</td>
                                            <td className="text-center">{{p.k}}</td>
                                            <td className="text-center">{{p.hr}}</td>
                                            <td className="text-center">{{p.era}}</td>
                                        </tr>
                                    );
                                }})}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }};

        const CrossoverPlayers = ({{ players }}) => {{
            const [expandedPlayer, setExpandedPlayer] = useState(null);
            const [searchTerm, setSearchTerm] = useState('');
            const {{ items, sortConfig, requestSort }} = useSortableData(players, {{ key: 'Total Games', direction: 'desc' }});

            const filtered = useMemo(() => {{
                if (!searchTerm) return items;
                const s = searchTerm.toLowerCase();
                return items.filter(p =>
                    p.Name?.toLowerCase().includes(s) ||
                    p['NCAA Teams']?.toLowerCase().includes(s) ||
                    p['MiLB Teams']?.toLowerCase().includes(s)
                );
            }}, [items, searchTerm]);

            if (!players || players.length === 0) {{
                return (
                    <div className="panel">
                        <div className="panel-header"><h2>Crossover Players</h2></div>
                        <div style={{{{padding: '20px', textAlign: 'center', color: '#666'}}}}>
                            No crossover players found. Crossover players are those seen at multiple levels (NCAA, MiLB).
                        </div>
                    </div>
                );
            }}

            const levelColors = DATA.levelColors || {{}};

            const PlayerTimeline = ({{ player }}) => {{
                const levels = [];
                if (player['NCAA Games'] > 0) levels.push({{ level: 'NCAA', games: player['NCAA Games'], teams: player['NCAA Teams'] }});
                if (player['MiLB Games'] > 0) levels.push({{ level: 'MiLB', games: player['MiLB Games'], teams: player['MiLB Teams'] }});

                return (
                    <div style={{{{padding: '16px', background: '#f8f9fa', borderRadius: '8px', marginTop: '8px'}}}}>
                        <div style={{{{display: 'flex', alignItems: 'center', marginBottom: '16px'}}}}>
                            <div style={{{{fontSize: '18px', fontWeight: 600}}}}>{{player.Name}}</div>
                            {{player['BBRef ID'] && (
                                <a href={{BREF_BASE + player['BBRef ID']}} target="_blank"
                                   style={{{{marginLeft: '8px', fontSize: '12px', color: '#007bff'}}}}>
                                    View on Baseball Reference ↗
                                </a>
                            )}}
                        </div>
                        <div style={{{{display: 'flex', alignItems: 'stretch', gap: '0'}}}}>
                            {{levels.map((l, idx) => (
                                <React.Fragment key={{l.level}}>
                                    <div style={{{{
                                        flex: 1,
                                        padding: '16px',
                                        background: 'white',
                                        borderRadius: idx === 0 ? '8px 0 0 8px' : idx === levels.length - 1 ? '0 8px 8px 0' : '0',
                                        borderTop: `4px solid ${{levelColors[l.level]}}`,
                                        textAlign: 'center'
                                    }}}}>
                                        <div style={{{{
                                            display: 'inline-block',
                                            padding: '4px 12px',
                                            background: levelColors[l.level],
                                            color: 'white',
                                            borderRadius: '4px',
                                            fontWeight: 600,
                                            marginBottom: '8px'
                                        }}}}>{{l.level}}</div>
                                        <div style={{{{fontSize: '24px', fontWeight: 'bold', marginBottom: '4px'}}}}>{{l.games}}</div>
                                        <div style={{{{fontSize: '12px', color: '#666', marginBottom: '8px'}}}}>game{{l.games !== 1 ? 's' : ''}}</div>
                                        <div style={{{{fontSize: '13px', color: '#333'}}}}>{{l.teams}}</div>
                                    </div>
                                    {{idx < levels.length - 1 && (
                                        <div style={{{{display: 'flex', alignItems: 'center', padding: '0 8px', background: 'white'}}}}>
                                            <span style={{{{fontSize: '24px', color: '#ccc'}}}}>→</span>
                                        </div>
                                    )}}
                                </React.Fragment>
                            ))}}
                        </div>
                    </div>
                );
            }};

            return (
                <div className="panel">
                    <div className="panel-header"><h2>Crossover Players - Seen at Multiple Levels ({{filtered.length}})</h2></div>
                    <div style={{{{padding: '16px'}}}}>
                        <input
                            type="text"
                            className="search-box"
                            placeholder="Search players or teams..."
                            value={{searchTerm}}
                            onChange={{(e) => setSearchTerm(e.target.value)}}
                            style={{{{marginBottom: '16px', maxWidth: '300px'}}}}
                        />
                    </div>
                    <div style={{{{padding: '0 16px 16px'}}}}>
                        {{filtered.map((p, i) => (
                            <div key={{i}} style={{{{marginBottom: '8px'}}}}>
                                <div
                                    onClick={{() => setExpandedPlayer(expandedPlayer === i ? null : i)}}
                                    style={{{{
                                        padding: '12px 16px',
                                        background: 'white',
                                        borderRadius: expandedPlayer === i ? '8px 8px 0 0' : '8px',
                                        border: '1px solid #dee2e6',
                                        borderBottom: expandedPlayer === i ? 'none' : '1px solid #dee2e6',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between'
                                    }}}}
                                >
                                    <div style={{{{display: 'flex', alignItems: 'center', gap: '16px'}}}}>
                                        <span style={{{{fontSize: '16px'}}}}>{{expandedPlayer === i ? '▼' : '▶'}}</span>
                                        <span style={{{{fontWeight: 600}}}}>{{p.Name}}</span>
                                        <div style={{{{display: 'flex', gap: '4px'}}}}>
                                            {{p['NCAA Games'] > 0 && <span style={{{{background: '#28a745', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '11px'}}}}>NCAA</span>}}
                                            {{p['MiLB Games'] > 0 && <span style={{{{background: '#ff6b35', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '11px'}}}}>MiLB</span>}}
                                        </div>
                                    </div>
                                    <div style={{{{display: 'flex', alignItems: 'center', gap: '24px', color: '#666'}}}}>
                                        <span>{{p['Total Games']}} total games</span>
                                    </div>
                                </div>
                                {{expandedPlayer === i && (
                                    <div style={{{{
                                        border: '1px solid #dee2e6',
                                        borderTop: 'none',
                                        borderRadius: '0 0 8px 8px',
                                        padding: '16px',
                                        background: '#fafafa'
                                    }}}}>
                                        <PlayerTimeline player={{p}} />
                                    </div>
                                )}}
                            </div>
                        ))}}
                    </div>
                </div>
            );
        }};

        const App = () => {{
            const [activeTab, setActiveTab] = useState('allGames');
            const [selectedPlayer, setSelectedPlayer] = useState(null);
            const [playerType, setPlayerType] = useState(null);
            const [milestoneLevelFilter, setMilestoneLevelFilter] = useState('All');
            const [milestoneLeagueFilter, setMilestoneLeagueFilter] = useState('All');

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

            // Collect all milestone data for LevelLeagueFilter derivation
            const allMilestoneData = useMemo(() => {{
                const all = [];
                Object.values(DATA.milestones || {{}}).forEach(arr => {{
                    if (Array.isArray(arr)) all.push(...arr);
                }});
                return all;
            }}, []);

            const hasCrossover = DATA.crossoverPlayers && DATA.crossoverPlayers.length > 0;

            const tabs = [
                {{ id: 'allGames', label: 'All Games' }},
                {{ id: 'calendar', label: 'Calendar' }},
                {{ id: 'unifiedBatters', label: 'Batters' }},
                {{ id: 'unifiedPitchers', label: 'Pitchers' }},
                {{ id: 'teams', label: 'Teams' }},
                {{ id: 'milestones', label: 'Milestones' }},
                ...(hasCrossover ? [{{ id: 'crossover', label: 'Crossover' }}] : []),
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

                    {{activeTab === 'allGames' && <UnifiedGameLog games={{DATA.unifiedGameLog}} />}}
                    {{activeTab === 'calendar' && <CalendarView games={{DATA.unifiedGameLog}} />}}
                    {{activeTab === 'teams' && <TeamRecords teams={{DATA.teamRecords}} />}}
                    {{activeTab === 'milestones' && (
                        <div>
                            <LevelLeagueFilter
                                levelFilter={{milestoneLevelFilter}}
                                setLevelFilter={{setMilestoneLevelFilter}}
                                leagueFilter={{milestoneLeagueFilter}}
                                setLeagueFilter={{setMilestoneLeagueFilter}}
                                data={{allMilestoneData}}
                            />

                            <h3 style={{{{margin: '0 0 16px 0', color: '#1e3a5f'}}}}>Elite Pitching Performances</h3>
                            <MilestonesTable title="Perfect Games" data={{DATA.milestones.perfectGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'Score']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="No-Hitters" data={{DATA.milestones.noHitters}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'BB', 'Score']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="One-Hitters" data={{DATA.milestones.oneHitters}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'H', 'K', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Two-Hitters" data={{DATA.milestones.twoHitters}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'H', 'K', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Maddux Games (CG, <100 pitches)" data={{DATA.milestones.madduxGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'H', 'K', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Complete Games & Shutouts</h3>
                            <MilestonesTable title="CGSO No Walks" data={{DATA.milestones.cgsoNoWalks}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'H', 'K']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Shutouts" data={{DATA.milestones.shutouts}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'BB']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="7+ IP Shutouts" data={{DATA.milestones.sevenInningShutouts}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'BB']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Complete Games" data={{DATA.milestones.completeGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Low-Hit CG" data={{DATA.milestones.lowHitCg}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'H', 'K', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Strikeout Performances</h3>
                            <MilestonesTable title="15+ K Games" data={{DATA.milestones.fifteenKGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'K', 'IP', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="12+ K Games" data={{DATA.milestones.twelveKGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'K', 'IP', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="10+ K Games" data={{DATA.milestones.tenKGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'K', 'IP', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="8+ K Games" data={{DATA.milestones.eightKGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'K', 'IP', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Quality Pitching</h3>
                            <MilestonesTable title="Quality Starts (6+ IP, ≤3 ER)" data={{DATA.milestones.qualityStarts}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Dominant Starts" data={{DATA.milestones.dominantStarts}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Efficient Starts" data={{DATA.milestones.efficientStarts}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="High K/Low BB" data={{DATA.milestones.highKLowBb}} columns={{['Date', 'Player', 'Team', 'Opponent', 'K', 'BB', 'IP', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="No-Walk Starts" data={{DATA.milestones.noWalkStarts}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Scoreless Relief" data={{DATA.milestones.scorelessRelief}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Wins" data={{DATA.milestones.winGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H', 'ER']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Saves" data={{DATA.milestones.saveGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'IP', 'K', 'H']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Big Batting Performances</h3>
                            <MilestonesTable title="3+ HR Games" data={{DATA.milestones.threeHrGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'HR', 'H', 'RBI', 'R']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Multi-HR Games" data={{DATA.milestones.multiHrGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'HR', 'H', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="HR Games" data={{DATA.milestones.hrGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'HR', 'H', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Cycles" data={{DATA.milestones.cycles}} columns={{['Date', 'Player', 'Team', 'Opponent', '1B', '2B', '3B', 'HR']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Cycle Watch (3 of 4)" data={{DATA.milestones.cycleWatch}} columns={{['Date', 'Player', 'Team', 'Opponent', '1B', '2B', '3B', 'HR']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Hit Milestones</h3>
                            <MilestonesTable title="5+ Hit Games" data={{DATA.milestones.fiveHitGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'H', 'R', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="4+ Hit Games" data={{DATA.milestones.fourHitGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'H', 'R', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="3+ Hit Games" data={{DATA.milestones.threeHitGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'H', 'R', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Multi-Double Games" data={{DATA.milestones.multiDoubleGames}} columns={{['Date', 'Player', 'Team', 'Opponent', '2B', 'H', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Multi-Triple Games" data={{DATA.milestones.multiTripleGames}} columns={{['Date', 'Player', 'Team', 'Opponent', '3B', 'H', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="2+ XBH Games" data={{DATA.milestones.hitForExtraBases}} columns={{['Date', 'Player', 'Team', 'Opponent', 'H', '2B', '3B', 'HR']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="8+ Total Bases" data={{DATA.milestones.threeTotalBasesGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'H', 'HR', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="Perfect Batting (3+ H, 0 K)" data={{DATA.milestones.perfectBattingGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'H', 'AB', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Run Production</h3>
                            <MilestonesTable title="6+ RBI Games" data={{DATA.milestones.sixRbiGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'RBI', 'H', 'HR']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="5+ RBI Games" data={{DATA.milestones.fiveRbiGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'RBI', 'H', 'HR']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="4+ RBI Games" data={{DATA.milestones.fourRbiGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'RBI', 'H', 'HR']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="4+ Run Games" data={{DATA.milestones.fourRunGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'R', 'H', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="3+ Run Games" data={{DATA.milestones.threeRunGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'R', 'H', 'RBI']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />

                            <h3 style={{{{margin: '32px 0 16px 0', color: '#1e3a5f'}}}}>Baserunning & Patience</h3>
                            <MilestonesTable title="Multi-SB Games" data={{DATA.milestones.multiSbGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'SB', 'H', 'R']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                            <MilestonesTable title="4+ Walk Games" data={{DATA.milestones.fourWalkGames}} columns={{['Date', 'Player', 'Team', 'Opponent', 'BB', 'H', 'R']}} levelFilter={{milestoneLevelFilter}} leagueFilter={{milestoneLeagueFilter}} />
                        </div>
                    )}}

                    {{activeTab === 'crossover' && <CrossoverPlayers players={{DATA.crossoverPlayers}} />}}

                    {{activeTab === 'unifiedBatters' && <UnifiedBattersTable batters={{DATA.unifiedBatters}} />}}
                    {{activeTab === 'unifiedPitchers' && <UnifiedPitchersTable pitchers={{DATA.unifiedPitchers}} />}}

                    {{activeTab === 'checklist' && <Checklist checklist={{DATA.checklist}} milbChecklist={{DATA.milbChecklist}} />}}
                    {{activeTab === 'map' && <SchoolMap stadiums={{DATA.stadiumLocations}} teamsSeenHome={{DATA.teamsSeenHome}} teamsSeenAway={{DATA.teamsSeenAway}} checklist={{DATA.checklist}} milbStadiums={{DATA.milbStadiumLocations}} milbVenuesVisited={{DATA.milbVenuesVisited}} partnerStadiums={{DATA.partnerStadiumLocations}} partnerVenuesVisited={{DATA.partnerVenuesVisited}} />}}

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
