"""
Baseball constants and configuration.
"""

import os
from pathlib import Path


def _find_project_root() -> Path:
    """Find the project root directory."""
    env_base = os.environ.get("NCAAB_PROCESSOR_DIR")
    if env_base:
        path = Path(env_base).expanduser()
        if path.exists():
            return path

    # Look for marker files
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "ncaab_parser.py").exists():
            return parent
        if (parent / ".project_root").exists():
            return parent

    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = _find_project_root()
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ROSTERS_DIR = BASE_DIR / "rosters"
OUTPUT_DIR = BASE_DIR / "html_output"
PDF_DIR = BASE_DIR / "pdfs"

# MiLB directories and API
MILB_DIR = BASE_DIR / "milb"
MILB_CACHE_DIR = MILB_DIR / "cache"
MILB_GAME_IDS_FILE = MILB_DIR / "game_ids.txt"
MILB_API_BASE = "https://statsapi.mlb.com/api/v1"

# Partner Leagues (independent leagues: Pioneer, Atlantic, American Association, Frontier)
PARTNER_DIR = BASE_DIR / "partner"
PARTNER_CACHE_DIR = PARTNER_DIR / "cache"
PARTNER_GAME_IDS_FILE = PARTNER_DIR / "game_ids.txt"


# === BASEBALL STAT COLUMNS ===

BATTING_STATS = [
    'ab',       # At Bats
    'r',        # Runs
    'h',        # Hits
    'rbi',      # Runs Batted In
    'bb',       # Walks
    'k',        # Strikeouts
    'po',       # Put Outs
    'a',        # Assists
    'lob',      # Left on Base
]

PITCHING_STATS = [
    'ip',       # Innings Pitched
    'h',        # Hits Allowed
    'r',        # Runs Allowed
    'er',       # Earned Runs
    'bb',       # Walks
    'k',        # Strikeouts
    'bf',       # Batters Faced
    'np',       # Number of Pitches
]

# Baseball milestones
BATTING_MILESTONES = {
    'multi_hr_games': {'stat': 'hr', 'min': 2, 'label': 'Multi-HR Games'},
    'hr_games': {'stat': 'hr', 'min': 1, 'label': 'HR Games'},
    'four_hit_games': {'stat': 'h', 'min': 4, 'label': '4+ Hit Games'},
    'three_hit_games': {'stat': 'h', 'min': 3, 'label': '3+ Hit Games'},
    'five_rbi_games': {'stat': 'rbi', 'min': 5, 'label': '5+ RBI Games'},
    'four_rbi_games': {'stat': 'rbi', 'min': 4, 'label': '4+ RBI Games'},
    'three_rbi_games': {'stat': 'rbi', 'min': 3, 'label': '3+ RBI Games'},
    'multi_sb_games': {'stat': 'sb', 'min': 2, 'label': 'Multi-SB Games'},
    'three_run_games': {'stat': 'r', 'min': 3, 'label': '3+ Run Games'},
    'cycle_watch': {'special': 'cycle', 'label': 'Cycle Watch (3 of 4)'},
}

PITCHING_MILESTONES = {
    'fifteen_k_games': {'stat': 'k', 'min': 15, 'label': '15+ K Games'},
    'ten_k_games': {'stat': 'k', 'min': 10, 'label': '10+ K Games'},
    'complete_games': {'special': 'cg', 'label': 'Complete Games'},
    'shutouts': {'special': 'sho', 'label': 'Shutouts'},
    'no_hitters': {'special': 'no_hitter', 'label': 'No-Hitters'},
    'quality_starts': {'special': 'qs', 'label': 'Quality Starts (6+ IP, 3 or fewer ER)'},
}


# Conference data - current (2025) memberships from Wikipedia
CONFERENCES = {
    'ACC': ['Boston College', 'California', 'Clemson', 'Duke', 'Florida State', 'Georgia Tech',
            'Louisville', 'Miami', 'NC State', 'North Carolina', 'Notre Dame', 'Pittsburgh',
            'Stanford', 'Virginia', 'Virginia Tech', 'Wake Forest'],
    'SEC': ['Alabama', 'Arkansas', 'Auburn', 'Florida', 'Georgia', 'Kentucky', 'LSU',
            'Mississippi State', 'Missouri', 'Oklahoma', 'Ole Miss', 'South Carolina',
            'Tennessee', 'Texas', 'Texas A&M', 'Vanderbilt'],
    'Big 12': ['Arizona', 'Arizona State', 'Baylor', 'BYU', 'Cincinnati',
               'Houston', 'Kansas', 'Kansas State', 'Oklahoma State', 'TCU',
               'Texas Tech', 'UCF', 'Utah', 'West Virginia'],
    'Big Ten': ['Illinois', 'Indiana', 'Iowa', 'Maryland', 'Michigan', 'Michigan State',
                'Minnesota', 'Nebraska', 'Northwestern', 'Ohio State', 'Oregon',
                'Penn State', 'Purdue', 'Rutgers', 'UCLA', 'USC', 'Washington'],
    'DI Independent': ['Oregon State'],
    'WCC': ['Gonzaga', 'LMU', 'Pacific', 'Pepperdine', 'Portland', "Saint Mary's",
            'San Diego', 'San Francisco', 'Santa Clara', 'Seattle'],
    'Mountain West': ['Air Force', 'Fresno State', 'Grand Canyon', 'Nevada', 'New Mexico',
                      'San Diego State', 'San Jose State', 'UNLV', 'Washington State'],
    'Missouri Valley': ['Belmont', 'Bradley', 'Evansville', 'Illinois State', 'Indiana State',
                        'Murray State', 'Southern Illinois', 'UIC', 'Valparaiso'],
    'WAC': ['Abilene Christian', 'California Baptist', 'Sacramento State', 'Tarleton State',
            'UT Arlington', 'Utah Tech', 'Utah Valley'],
    'Summit League': ['North Dakota State', 'Northern Colorado', 'Omaha', 'Oral Roberts',
                      'South Dakota State', 'St. Thomas'],
    'Big East': ['Butler', 'Creighton', 'Georgetown', 'Seton Hall', "St. John's",
                 'UConn', 'Villanova', 'Xavier'],
    'Sun Belt': ['Appalachian State', 'Arkansas State', 'Coastal Carolina', 'Georgia Southern',
                 'Georgia State', 'James Madison', 'Louisiana', 'Louisiana-Monroe', 'Marshall',
                 'Old Dominion', 'South Alabama', 'Southern Miss', 'Texas State', 'Troy'],
    'Southern': ['ETSU', 'Mercer', 'Samford', 'The Citadel', 'UNC Greensboro', 'VMI',
                 'Western Carolina', 'Wofford'],
    'Northeast': ['Central Connecticut', 'Coppin State', 'Delaware State', 'Fairleigh Dickinson',
                  'Le Moyne', 'LIU', 'Mercyhurst', 'New Haven', 'Norfolk State', 'Stonehill',
                  'UMES', 'Wagner'],
    'Big West': ['Cal Poly', 'Cal State Fullerton', 'CSU Bakersfield', 'CSUN', 'Hawaii',
                 'Long Beach State', 'UC Davis', 'UC Irvine', 'UC Riverside',
                 'UC San Diego', 'UC Santa Barbara'],
    'American': ['Charlotte', 'East Carolina', 'FAU', 'Memphis', 'Rice', 'Tulane',
                 'UAB', 'USF', 'UTSA', 'Wichita State'],
    'Atlantic 10': ['Davidson', 'Dayton', 'Fordham', 'George Mason', 'George Washington',
                    'La Salle', 'Rhode Island', 'Richmond', "Saint Joseph's", 'Saint Louis',
                    'St. Bonaventure', 'VCU'],
    'Conference USA': ['Dallas Baptist', 'Delaware', 'FIU', 'Jacksonville State', 'Kennesaw State',
                       'Liberty', 'Louisiana Tech', 'Middle Tennessee', 'Missouri State',
                       'New Mexico State', 'Sam Houston', 'WKU'],
    'CAA': ['Campbell', 'Charleston', 'Elon', 'Hofstra', 'Monmouth', 'North Carolina A&T',
            'Northeastern', 'Stony Brook', 'Towson', 'UNC Wilmington', 'William & Mary'],
    'Ohio Valley': ['Eastern Illinois', 'Lindenwood', 'Little Rock', 'Morehead State',
                    'SIU Edwardsville', 'Southeast Missouri', 'Southern Indiana',
                    'Tennessee Tech', 'UT Martin', 'Western Illinois'],
    'ASUN': ['Austin Peay', 'Bellarmine', 'Central Arkansas', 'Eastern Kentucky', 'FGCU',
             'Jacksonville', 'Lipscomb', 'North Alabama', 'North Florida', 'Queens',
             'Stetson', 'West Georgia'],
    'Southland': ['Houston Christian', 'Lamar', 'McNeese', 'New Orleans', 'Nicholls',
                  'Northwestern State', 'Southeastern Louisiana', 'Stephen F. Austin',
                  'Texas A&M-Corpus Christi', 'UTRGV', 'UIW'],
    'Big South': ['Charleston Southern', 'Gardner-Webb', 'High Point', 'Longwood',
                  'Presbyterian', 'Radford', 'UNC Asheville', 'USC Upstate', 'Winthrop'],
    'Horizon League': ['Milwaukee', 'Northern Kentucky', 'Oakland',
                       'Wright State', 'Youngstown State'],
    'Ivy League': ['Brown', 'Columbia', 'Cornell', 'Dartmouth', 'Harvard', 'Penn',
                   'Princeton', 'Yale'],
    'MAAC': ['Canisius', 'Fairfield', 'Iona', 'Manhattan', 'Marist', 'Merrimack',
             "Mount St. Mary's", 'Niagara', 'Quinnipiac', 'Rider', 'Sacred Heart',
             "Saint Peter's", 'Siena'],
    'MAC': ['Akron', 'Ball State', 'Bowling Green', 'Central Michigan', 'Eastern Michigan',
            'Kent State', 'UMass', 'Miami (OH)', 'NIU', 'Ohio', 'Toledo', 'Western Michigan'],
    'Patriot League': ['Army', 'Bucknell', 'Holy Cross', 'Lafayette', 'Lehigh', 'Navy'],
    'SWAC': ['Alabama A&M', 'Alabama State', 'Alcorn State', 'Arkansas-Pine Bluff',
             'Bethune-Cookman', 'Florida A&M', 'Grambling State', 'Jackson State',
             'Mississippi Valley State', 'Prairie View A&M', 'Southern', 'Texas Southern'],
    'America East': ['Albany', 'Binghamton', 'Bryant', 'Maine', 'NJIT', 'UMBC', 'UMass Lowell'],
}

# Teams that changed conferences (team -> list of (end_year, old_conference))
# If a team is listed here, years <= end_year use old_conference
CONFERENCE_CHANGES = {
    # 2024 Pac-12 realignment
    'California': [(2023, 'Pac-12')],
    'Stanford': [(2023, 'Pac-12')],
    'UCLA': [(2023, 'Pac-12')],
    'USC': [(2023, 'Pac-12')],
    'Arizona': [(2023, 'Pac-12')],
    'Arizona State': [(2023, 'Pac-12')],
    'Utah': [(2023, 'Pac-12')],
    'Oregon': [(2023, 'Pac-12')],
    'Washington': [(2023, 'Pac-12')],
    'Oregon State': [(2023, 'Pac-12')],
    'Washington State': [(2023, 'Pac-12')],
    # Oklahoma and Texas to SEC (2024)
    'Oklahoma': [(2023, 'Big 12')],
    'Texas': [(2023, 'Big 12')],
}

# Team name aliases (alternate names -> canonical name)
TEAM_ALIASES = {
    'Cal': 'California',
    'Ole Miss': 'Mississippi',
    'Miami (FL)': 'Miami',
    'LSU': 'LSU',
    'TCU': 'TCU',
    'UCF': 'UCF',
    'USC': 'USC',
    'UCLA': 'UCLA',
    'UNLV': 'UNLV',
    'UIC': 'UIC',
    'SMU': 'SMU',
    'BYU': 'BYU',
    'LMU': 'Loyola Marymount',
    'UTAH': 'Utah',
    'Loyola Marymount': 'LMU',
}


def get_conference(team: str, year: int = None) -> str:
    """Get conference for a team, optionally for a specific year.

    Args:
        team: Team name
        year: Optional year for historical conference lookup

    Returns:
        Conference name or 'Other' if not found
    """
    # Normalize team name
    canonical = TEAM_ALIASES.get(team, team)

    # Check for historical conference changes
    if year and canonical in CONFERENCE_CHANGES:
        for end_year, old_conf in CONFERENCE_CHANGES[canonical]:
            if year <= end_year:
                return old_conf

    # Look up current conference
    for conf, teams in CONFERENCES.items():
        if canonical in teams or team in teams:
            return conf
    return 'Other'


def get_all_conferences() -> list:
    """Get list of all conference names."""
    return list(CONFERENCES.keys())


# === PRO LEVEL / LEAGUE MAPPINGS ===

# Maps API sport_level codes and stadium level codes to display names
SPORT_LEVEL_MAP = {
    'AAA': 'Triple-A',
    'AA': 'Double-A',
    'A+': 'High-A',
    'A': 'Single-A',
    'Rookie': 'Independent',
    'Partner': 'Independent',
}

# Maps league names to their level
LEAGUE_LEVEL_MAP = {
    # Triple-A
    'International League': 'Triple-A',
    'Pacific Coast League': 'Triple-A',
    # Double-A
    'Eastern League': 'Double-A',
    'Southern League': 'Double-A',
    'Texas League': 'Double-A',
    # High-A
    'Midwest League': 'High-A',
    'South Atlantic League': 'High-A',
    'Northwest League': 'High-A',
    # Single-A
    'Carolina League': 'Single-A',
    'California League': 'Single-A',
    'Florida State League': 'Single-A',
    # Independent / Partner
    'Pioneer League': 'Independent',
    'Atlantic League': 'Independent',
    'American Association': 'Independent',
    'Frontier League': 'Independent',
}

# Ordered display levels with their associated leagues
PRO_LEVELS = {
    'Triple-A': ['International League', 'Pacific Coast League'],
    'Double-A': ['Eastern League', 'Southern League', 'Texas League'],
    'High-A': ['Midwest League', 'South Atlantic League', 'Northwest League'],
    'Single-A': ['Carolina League', 'California League', 'Florida State League'],
    'Independent': ['Pioneer League', 'Atlantic League', 'American Association', 'Frontier League'],
}

# Ordered list of all levels for consistent display
LEVEL_ORDER = ['NCAA', 'Triple-A', 'Double-A', 'High-A', 'Single-A', 'Independent']

# Colors for each level
LEVEL_COLORS = {
    'NCAA': '#28a745',
    'Triple-A': '#d4380d',
    'Double-A': '#ff6b35',
    'High-A': '#fa8c16',
    'Single-A': '#1890ff',
    'Rookie': '#17a2b8',
    'Independent': '#9c27b0',
    'Combined': '#1e3a5f',
}


def resolve_level_and_league(metadata: dict, team_name: str = '') -> tuple:
    """Resolve the display level and league for a game or team.

    Args:
        metadata: Game metadata dict (may contain 'source', 'league', 'sport_level', etc.)
        team_name: Optional team name for partner league lookup

    Returns:
        Tuple of (level, league) e.g. ('Single-A', 'California League')
    """
    from ..utils.partner_stadiums import PARTNER_TEAM_DATA, get_canonical_team_name

    source = metadata.get('source', '')

    # Partner league games
    if source == 'partner':
        canonical = get_canonical_team_name(team_name)
        partner_data = PARTNER_TEAM_DATA.get(canonical, {})
        league = partner_data.get('league', '')
        return ('Independent', league)

    # MiLB games - try league name first
    league_info = metadata.get('league', {})
    league_name = ''
    if isinstance(league_info, dict):
        league_name = league_info.get('home', '') or league_info.get('away', '')
    elif isinstance(league_info, str):
        league_name = league_info

    if league_name and league_name in LEAGUE_LEVEL_MAP:
        # Pioneer League was MiLB Rookie ball before 2021 reorganization
        if league_name == 'Pioneer League':
            date_str = metadata.get('date_yyyymmdd', '') or metadata.get('date', '')
            if date_str and str(date_str)[:4] < '2021':
                return ('Rookie', league_name)
        return (LEAGUE_LEVEL_MAP[league_name], league_name)

    # Fall back to sport_level code from stadium data
    sport_level = metadata.get('sport_level', '')
    if isinstance(sport_level, dict):
        sport_level = sport_level.get('home', '') or sport_level.get('away', '')
    if sport_level and isinstance(sport_level, str) and sport_level in SPORT_LEVEL_MAP:
        return (SPORT_LEVEL_MAP[sport_level], league_name or '')

    # Try to resolve from MILB_STADIUM_DATA via team name
    from ..utils.milb_stadiums import MILB_TEAM_LEAGUES
    if team_name and team_name in MILB_TEAM_LEAGUES:
        league = MILB_TEAM_LEAGUES[team_name]
        level = LEAGUE_LEVEL_MAP.get(league, '')
        if level:
            return (level, league)

    # Default fallback
    return ('', league_name or '')
