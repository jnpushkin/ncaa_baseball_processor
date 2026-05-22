"""
Partner League parsers for independent baseball leagues.

Supports:
- Pioneer League (pioneerleague.com XML format)
- Atlantic League (Pointstreak HTML format)
- American Association (Pointstreak HTML format)
- Frontier League (Pointstreak HTML format)
"""

import json
import re
import sys
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# Add parent dir for shared utils
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from utils.http import create_retry_session

_session = create_retry_session()

# Lazy import for partner team data
# These will be imported on first use to avoid path issues
_partner_stadiums_module = None
_partner_roster_module = None

def _get_partner_stadiums_module():
    """Lazy import of partner_stadiums module."""
    global _partner_stadiums_module
    if _partner_stadiums_module is None:
        import sys
        parent_dir = Path(__file__).resolve().parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        try:
            from baseball_processor.utils import partner_stadiums
            _partner_stadiums_module = partner_stadiums
        except ImportError:
            # Create a mock module with fallback functions
            class MockModule:
                @staticmethod
                def get_partner_team_id(team_name: str) -> Optional[str]:
                    return None
                @staticmethod
                def get_partner_logo(team_name: str) -> Optional[str]:
                    return None
                @staticmethod
                def get_partner_team_data(team_name: str) -> Optional[Dict]:
                    return None
            _partner_stadiums_module = MockModule()
    return _partner_stadiums_module

def get_partner_team_data(team_name: str) -> Optional[Dict]:
    """Get partner team data (logo, stadium, coordinates, etc.)."""
    return _get_partner_stadiums_module().get_partner_team_data(team_name)

def get_partner_team_id(team_name: str) -> Optional[str]:
    """Get partner team ID."""
    return _get_partner_stadiums_module().get_partner_team_id(team_name)

def get_partner_logo(team_name: str) -> Optional[str]:
    """Get partner team logo URL."""
    return _get_partner_stadiums_module().get_partner_logo(team_name)


def _get_partner_roster_module():
    """Lazy import of partner_roster_integration module."""
    global _partner_roster_module
    if _partner_roster_module is None:
        import sys
        parent_dir = Path(__file__).resolve().parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        try:
            import partner_roster_integration
            _partner_roster_module = partner_roster_integration
        except ImportError:
            # Create a mock module with fallback functions
            class MockModule:
                @staticmethod
                def lookup_partner_player(team_name: str, year: int, player_name: str) -> Optional[str]:
                    return None
                @staticmethod
                def fetch_partner_roster(team_name: str, year: int, use_cache: bool = True) -> Optional[Dict]:
                    return None
            _partner_roster_module = MockModule()
    return _partner_roster_module


def enrich_players_with_bref_ids(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich player data in a parsed game with Baseball Reference IDs and full names.

    Looks up bref_ids and full names from team rosters for crossover tracking.

    Args:
        game_data: Parsed game data dict (will be modified in place)

    Returns:
        Modified game data with player_id fields and full names populated
    """
    roster_module = _get_partner_roster_module()
    metadata = game_data.get('metadata', {})
    box_score = game_data.get('box_score', {})

    # Get year from date
    date_str = metadata.get('date_yyyymmdd', '')
    if len(date_str) >= 4:
        year = int(date_str[:4])
    else:
        year = 2024  # Default

    def enrich_player(player, team_name, fallback_team_name=None):
        """Look up bref_id and full name for a player, trying fallback team if needed."""
        if player.get('player_id') and player.get('bref_id'):
            return
        result = roster_module.lookup_partner_player_full(team_name, year, player.get('name', ''))
        if not result and fallback_team_name:
            result = roster_module.lookup_partner_player_full(fallback_team_name, year, player.get('name', ''))
        if result:
            if result.get('bref_id'):
                player['player_id'] = result['bref_id']
                player['bref_id'] = result['bref_id']
            if result.get('full_name'):
                player['name'] = result['full_name']

    # Process away team (try opponent as fallback for misassigned players)
    away_team = metadata.get('away_team', '')
    home_team = metadata.get('home_team', '')
    if away_team:
        for player in box_score.get('away_batting', []):
            enrich_player(player, away_team, home_team)
        for player in box_score.get('away_pitching', []):
            enrich_player(player, away_team, home_team)

    # Process home team
    if home_team:
        for player in box_score.get('home_batting', []):
            enrich_player(player, home_team, away_team)
        for player in box_score.get('home_pitching', []):
            enrich_player(player, home_team, away_team)

    return game_data


def prefetch_rosters_for_game(game_data: Dict[str, Any]) -> None:
    """
    Pre-fetch rosters for both teams in a game.

    Call this before enrich_players_with_bref_ids() to cache rosters.

    Args:
        game_data: Parsed game data dict
    """
    roster_module = _get_partner_roster_module()
    metadata = game_data.get('metadata', {})

    # Get year from date
    date_str = metadata.get('date_yyyymmdd', '')
    if len(date_str) >= 4:
        year = int(date_str[:4])
    else:
        year = 2024

    # Fetch rosters for both teams
    away_team = metadata.get('away_team', '')
    home_team = metadata.get('home_team', '')

    if away_team:
        roster_module.fetch_partner_roster(away_team, year, use_cache=True)
    if home_team:
        roster_module.fetch_partner_roster(home_team, year, use_cache=True)


# League configurations
PARTNER_LEAGUES = {
    'pioneer': {
        'name': 'Pioneer League',
        'base_url': 'https://www.pioneerleague.com/sports/bsb/{year}/boxscores/',
        'format': 'xml',
    },
    'atlantic': {
        'name': 'Atlantic League',
        'base_url': 'https://baseball.pointstreak.com/boxscore.html?gameid=',
        'format': 'pointstreak',
        'league_id': 174,
    },
    'american_association': {
        'name': 'American Association',
        'base_url': 'https://baseball.pointstreak.com/boxscore.html?gameid=',
        'format': 'pointstreak',
        'league_id': 193,
    },
    'frontier': {
        'name': 'Frontier League',
        'base_url': 'https://baseball.pointstreak.com/boxscore.html?gameid=',
        'format': 'pointstreak',
        'league_id': 196,
    },
}


def _default_partner_artifact_dir() -> Path:
    """Return the default location for partner source artifacts."""
    return Path(__file__).resolve().parent.parent / 'partner' / 'artifacts'


def _relative_artifact_path(path: Path) -> str:
    """Store artifact paths relative to the project root when possible."""
    project_root = Path(__file__).resolve().parent.parent
    try:
        return str(path.resolve().relative_to(project_root))
    except ValueError:
        return str(path)


def pioneer_boxscore_urls(game_code: str, year: Optional[int] = None) -> Dict[str, str]:
    """Build the Pioneer boxscore, print, and coach-view URLs for a game."""
    season = year or (int(game_code[:4]) if len(game_code) >= 4 and game_code[:4].isdigit() else 2024)
    base = f"https://www.pioneerleague.com/sports/bsb/{season}/boxscores/{game_code}.xml"
    return {
        'boxscore': base,
        'print': f"{base}?dec=printer-decorator",
        'coach_view': f"{base}?tmpl=bsxml-monospace-template",
    }


def pioneer_artifact_paths(
    game_code: str,
    year: Optional[int] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """Return local artifact paths for a Pioneer game."""
    season = year or (int(game_code[:4]) if len(game_code) >= 4 and game_code[:4].isdigit() else 2024)
    root = Path(output_dir) if output_dir else _default_partner_artifact_dir()
    game_dir = root / 'pioneer' / str(season)
    return {
        'boxscore_html': game_dir / f'{game_code}.boxscore.html',
        'print_html': game_dir / f'{game_code}.print.html',
        'coach_view_html': game_dir / f'{game_code}.coach.html',
        'print_pdf': game_dir / f'{game_code}.print.pdf',
    }


def _pioneer_source_artifact_metadata(
    game_code: str,
    year: Optional[int],
    artifact_paths: Optional[Dict[str, Path]] = None,
    downloaded_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build cache metadata for Pioneer source URLs and local artifacts."""
    urls = pioneer_boxscore_urls(game_code, year)
    metadata: Dict[str, Any] = {
        'source_urls': urls,
    }
    if artifact_paths:
        metadata['source_artifacts'] = {
            'downloaded_at': downloaded_at or datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'files': {
                key: _relative_artifact_path(path)
                for key, path in artifact_paths.items()
                if path.exists()
            },
            'urls': urls,
            'note': 'Pioneer does not expose an official PDF link here; print_pdf is generated from the rendered print view.',
        }
    return metadata


def attach_pioneer_source_metadata(
    game_data: Dict[str, Any],
    game_code: str,
    year: Optional[int] = None,
    artifact_paths: Optional[Dict[str, Path]] = None,
) -> Dict[str, Any]:
    """Attach Pioneer source URL/artifact metadata to a parsed or cached game."""
    metadata = game_data.setdefault('metadata', {})
    source_metadata = _pioneer_source_artifact_metadata(game_code, year, artifact_paths)
    metadata['source_urls'] = source_metadata['source_urls']
    if 'source_artifacts' in source_metadata:
        metadata['source_artifacts'] = source_metadata['source_artifacts']
    return game_data


def download_pioneer_boxscore_artifacts(
    game_code: str,
    year: Optional[int] = None,
    output_dir: Optional[Path] = None,
    overwrite: bool = False,
    include_pdf: bool = True,
    include_html: bool = True,
    timeout_ms: int = 45000,
) -> Dict[str, Any]:
    """
    Save local source artifacts for a Pioneer boxscore.

    Pioneer exposes rendered HTML/print views, not a direct official PDF. This
    function preserves the rendered boxscore HTML, print HTML, coach-view HTML,
    and a generated PDF of the print view.
    """
    if not include_pdf and not include_html:
        raise ValueError("At least one of include_pdf or include_html must be true")

    season = year or (int(game_code[:4]) if len(game_code) >= 4 and game_code[:4].isdigit() else 2024)
    urls = pioneer_boxscore_urls(game_code, season)
    paths = pioneer_artifact_paths(game_code, season, output_dir)
    requested = set()
    if include_html:
        requested.update({'boxscore_html', 'print_html', 'coach_view_html'})
    if include_pdf:
        requested.add('print_pdf')

    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    needed = {key for key in requested if overwrite or not paths[key].exists()}
    downloaded: List[str] = []
    skipped_existing = sorted(requested - needed)

    if needed:
        from playwright.sync_api import sync_playwright

        view_targets = [
            ('boxscore', urls['boxscore'], {'boxscore_html'}),
            ('print', urls['print'], {'print_html', 'print_pdf'}),
            ('coach_view', urls['coach_view'], {'coach_view_html'}),
        ]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                for _view_name, url, keys in view_targets:
                    if not (keys & needed):
                        continue
                    page.goto(url, wait_until='networkidle', timeout=timeout_ms)
                    if 'boxscore_html' in keys and 'boxscore_html' in needed:
                        paths['boxscore_html'].write_text(page.content(), encoding='utf-8')
                        downloaded.append('boxscore_html')
                    if 'print_html' in keys and 'print_html' in needed:
                        paths['print_html'].write_text(page.content(), encoding='utf-8')
                        downloaded.append('print_html')
                    if 'print_pdf' in keys and 'print_pdf' in needed:
                        page.emulate_media(media='print')
                        page.pdf(
                            path=str(paths['print_pdf']),
                            format='Letter',
                            print_background=True,
                            margin={
                                'top': '0.4in',
                                'right': '0.4in',
                                'bottom': '0.4in',
                                'left': '0.4in',
                            },
                        )
                        downloaded.append('print_pdf')
                    if 'coach_view_html' in keys and 'coach_view_html' in needed:
                        paths['coach_view_html'].write_text(page.content(), encoding='utf-8')
                        downloaded.append('coach_view_html')
            finally:
                browser.close()

    return {
        'game_code': game_code,
        'year': season,
        'source_urls': urls,
        'artifacts': {
            key: _relative_artifact_path(path)
            for key, path in paths.items()
            if key in requested and path.exists()
        },
        'downloaded': downloaded,
        'skipped_existing': skipped_existing,
        'generated_pdf': include_pdf,
    }


def list_pioneer_games_for_date(date_str: str) -> List[Dict[str, str]]:
    """
    Scrape pioneerleague.com schedule and return all games on the given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of dicts with keys: game_code, away_team, home_team, date_yyyymmdd
    """
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    year = dt.year
    yyyymmdd = dt.strftime('%Y%m%d')

    url = f'https://www.pioneerleague.com/sports/bsb/{year}/schedule'
    resp = _session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    resp.raise_for_status()
    html = resp.text

    games = []
    seen = set()
    pattern = re.compile(r'href="[^"]*boxscores/(' + yyyymmdd + r'_[a-z0-9]+)\.xml[^"]*"')
    for m in pattern.finditer(html):
        code = m.group(1)
        if code in seen:
            continue
        seen.add(code)
        before = html[max(0, m.start() - 5000):m.start()]
        alts = re.findall(r'alt="([^"]+?) team logo"', before)
        away = alts[-2] if len(alts) >= 2 else '?'
        home = alts[-1] if len(alts) >= 1 else '?'
        games.append({
            'game_code': code,
            'away_team': away,
            'home_team': home,
            'date_yyyymmdd': yyyymmdd,
        })
    return games


def fetch_pioneer_boxscore(game_code: str, year: int = 2024) -> Dict[str, Any]:
    """
    Fetch and parse a Pioneer League box score using Playwright.

    The Pioneer League website serves HTML with JavaScript-rendered content,
    so we use Playwright to render the page and extract the stats tables.

    Args:
        game_code: Game code (e.g., "20240828_fhp1" from the URL)
        year: Season year

    Returns:
        Parsed game data dict
    """
    from playwright.sync_api import sync_playwright

    url = f"https://www.pioneerleague.com/sports/bsb/{year}/boxscores/{game_code}.xml"
    print(f"Fetching Pioneer League game: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until='networkidle', timeout=30000)
        html_content = page.content()
        browser.close()

    game_data = parse_pioneer_html(html_content, game_code)
    attach_pioneer_source_metadata(game_data, game_code, year)
    return game_data


def _safe_int_text(value: Any, default: int = 0) -> int:
    """Parse an integer from a table cell or scalar value."""
    try:
        return int(str(value or '').strip())
    except (TypeError, ValueError):
        return default


def _pioneer_cell_text(cells: List[Any], index: int, default: str = '') -> str:
    if index < 0 or index >= len(cells):
        return default
    return cells[index].get_text(strip=True)


def _pioneer_header_index(table) -> Dict[str, int]:
    rows = table.find_all('tr') if table else []
    if not rows:
        return {}
    headers = rows[0].find_all(['th', 'td'])
    return {
        cell.get_text(strip=True).lower(): index
        for index, cell in enumerate(headers)
        if cell.get_text(strip=True)
    }


def _pioneer_index_for(headers: Dict[str, int], label: str, fallback: int) -> int:
    return headers.get(label.lower(), fallback)


def _split_pioneer_note_items(text: str) -> List[str]:
    text = re.sub(r'\s+', ' ', text or '').strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r'\s*,\s*', text) if item.strip()]


def _parse_pioneer_counted_item(item: str) -> tuple[str, int]:
    item = re.sub(r'\s+', ' ', item or '').strip()
    count_match = re.search(r'\((\d+)\)\s*$', item)
    count = int(count_match.group(1)) if count_match else 1
    name = re.sub(r'\s*\(\d+\)\s*$', '', item).strip()
    return name, count


def _pioneer_note_name_key(name: str) -> str:
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name or '')
    return re.sub(r'[^a-z0-9]+', ' ', name.lower()).strip()


def _merge_game_notes(target: Dict[str, List[str]], source: Dict[str, List[str]]) -> None:
    for key, values in source.items():
        if values:
            target.setdefault(key, []).extend(values)


def parse_pioneer_batting_summary(stats_box) -> Dict[str, List[str]]:
    """Parse XBH/SB notes from a Pioneer batting stats summary block."""
    summary = stats_box.select_one('.stats-summary') if stats_box else None
    if not summary:
        return {}

    label_to_key = {
        '2B': 'doubles',
        '3B': 'triples',
        'HR': 'home_runs',
        'SB': 'stolen_bases',
    }
    notes: Dict[str, List[str]] = {}
    for row in summary.find_all('div', recursive=False):
        label_elem = row.find('strong')
        value_elem = row.find('span')
        if not label_elem or not value_elem:
            continue
        label = label_elem.get_text(strip=True).rstrip(':').upper()
        key = label_to_key.get(label)
        if not key:
            continue
        items = _split_pioneer_note_items(value_elem.get_text(' ', strip=True))
        if items:
            notes.setdefault(key, []).extend(items)
    return notes


def apply_pioneer_batting_summary(batters: List[Dict[str, Any]], notes: Dict[str, List[str]]) -> None:
    """Merge Pioneer summary-derived XBH/SB counts into parsed batter rows."""
    if not batters or not notes:
        return

    by_name = {_pioneer_note_name_key(row.get('name', '')): row for row in batters}
    by_last_name: Dict[str, List[Dict[str, Any]]] = {}
    for row in batters:
        key = _pioneer_note_name_key(row.get('name', ''))
        if not key:
            continue
        last = key.split()[-1]
        by_last_name.setdefault(last, []).append(row)

    note_to_row_stat = {
        'doubles': 'doubles',
        'triples': 'triples',
        'home_runs': 'hr',
        'stolen_bases': 'sb',
    }
    for note_key, row_stat in note_to_row_stat.items():
        for item in notes.get(note_key, []):
            name, count = _parse_pioneer_counted_item(item)
            key = _pioneer_note_name_key(name)
            row = by_name.get(key)
            if not row and key:
                last_matches = by_last_name.get(key.split()[-1], [])
                if len(last_matches) == 1:
                    row = last_matches[0]
            if row:
                row[row_stat] = max(_safe_int_text(row.get(row_stat)), count)


def _pioneer_stats_boxes_by_table_header(soup: BeautifulSoup, header: str) -> List[Any]:
    boxes = soup.select('#boxscore-tabpanel .stats-box.half') or soup.select('.stats-box.half')
    matches = []
    for box in boxes:
        table = box.find('table')
        headers = _pioneer_header_index(table)
        if headers and header.lower() in headers and headers.get(header.lower()) == 0:
            matches.append(box)
    return matches


def parse_pioneer_html(html_content: str, game_code: str = '') -> Dict[str, Any]:
    """
    Parse Pioneer League HTML box score (rendered via Playwright).

    Table structure:
    - Table 0: Line Score
    - Table 1: Away team batting
    - Table 2: Home team batting
    - Table 3: Away team pitching
    - Table 4: Home team pitching

    Args:
        html_content: Rendered HTML content
        game_code: Original game code for reference

    Returns:
        Game data dict in standard format
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract teams from og:title meta tag
    # Format: "Idaho Falls Chukars vs. Oakland Ballers - Box Score - 8/28/2024"
    away_team = ''
    home_team = ''
    date_str = ''
    date_yyyymmdd = ''

    og_title = soup.find('meta', property='og:title')
    if og_title:
        title_content = og_title.get('content', '')
        match = re.match(r'(.+?)\s+vs\.?\s+(.+?)\s+-\s+Box Score\s+-\s+(\d+/\d+/\d+)', title_content)
        if match:
            away_team = match.group(1).strip()
            home_team = match.group(2).strip()
            date_str = match.group(3).strip()
            try:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                date_yyyymmdd = date_obj.strftime('%Y%m%d')
            except ValueError:
                pass

    # Get date from game code if not found
    if not date_yyyymmdd and game_code and len(game_code) >= 8:
        date_yyyymmdd = game_code[:8]
        try:
            date_obj = datetime.strptime(date_yyyymmdd, '%Y%m%d')
            date_str = date_obj.strftime('%m/%d/%Y')
        except ValueError:
            pass

    # Find tables
    tables = soup.find_all('table')

    # Parse line score (Table 0) for final score
    # Format: Final, 1, 2, 3, 4, 5, 6, 7, 8, 9, R, H, E
    # R (runs) is typically at index 10 (or 3rd from last)
    away_score = 0
    home_score = 0
    if len(tables) > 0:
        line_score = tables[0]
        rows = line_score.find_all('tr')

        # Find the R column index from header row
        r_col_idx = -3  # Default: 3rd from last
        if rows:
            header_cells = rows[0].find_all(['th', 'td'])
            for i, cell in enumerate(header_cells):
                if cell.get_text(strip=True) == 'R':
                    r_col_idx = i
                    break

        # Parse team rows (rows 1 and 2)
        for row in rows[1:3]:
            cells = row.find_all(['th', 'td'])
            if len(cells) > abs(r_col_idx):
                team_cell = cells[0].get_text(strip=True)
                runs_text = cells[r_col_idx].get_text(strip=True)
                try:
                    runs = int(runs_text)
                except ValueError:
                    runs = 0

                # First data row is away team, second is home team
                if away_score == 0 and away_team and away_team in team_cell:
                    away_score = runs
                elif home_score == 0 and home_team and home_team in team_cell:
                    home_score = runs
                elif away_score == 0:
                    away_score = runs
                else:
                    home_score = runs

    batting_boxes = _pioneer_stats_boxes_by_table_header(soup, 'Hitters')
    pitching_boxes = _pioneer_stats_boxes_by_table_header(soup, 'Pitchers')

    # Parse batting tables and merge summary-only XBH/SB data.
    away_batters = []
    home_batters = []
    game_notes: Dict[str, List[str]] = {}
    if len(batting_boxes) > 0:
        away_batters = parse_pioneer_html_batting(batting_boxes[0].find('table'))
        away_notes = parse_pioneer_batting_summary(batting_boxes[0])
        apply_pioneer_batting_summary(away_batters, away_notes)
        _merge_game_notes(game_notes, away_notes)
    elif len(tables) > 1:
        away_batters = parse_pioneer_html_batting(tables[1])

    if len(batting_boxes) > 1:
        home_batters = parse_pioneer_html_batting(batting_boxes[1].find('table'))
        home_notes = parse_pioneer_batting_summary(batting_boxes[1])
        apply_pioneer_batting_summary(home_batters, home_notes)
        _merge_game_notes(game_notes, home_notes)
    elif len(tables) > 2:
        home_batters = parse_pioneer_html_batting(tables[2])

    # Parse pitching tables (Tables 3 and 4)
    away_pitchers = []
    home_pitchers = []
    if len(pitching_boxes) > 0:
        away_pitchers = parse_pioneer_html_pitching(pitching_boxes[0].find('table'))
    elif len(tables) > 3:
        away_pitchers = parse_pioneer_html_pitching(tables[3])

    if len(pitching_boxes) > 1:
        home_pitchers = parse_pioneer_html_pitching(pitching_boxes[1].find('table'))
    elif len(tables) > 4:
        home_pitchers = parse_pioneer_html_pitching(tables[4])

    # Look up team IDs and logos from partner team data
    away_team_data = get_partner_team_data(away_team) or {}
    home_team_data = get_partner_team_data(home_team) or {}

    return {
        'metadata': {
            'date': date_str,
            'date_yyyymmdd': date_yyyymmdd,
            'away_team': away_team,
            'away_team_short': '',
            'away_team_id': away_team_data.get('id'),
            'away_team_logo': away_team_data.get('logo'),
            'home_team': home_team,
            'home_team_short': '',
            'home_team_id': home_team_data.get('id'),
            'home_team_logo': home_team_data.get('logo'),
            'away_team_score': away_score,
            'home_team_score': home_score,
            'venue': home_team_data.get('stadium', ''),
            'parent_orgs': {'away': '', 'home': ''},
            'league': {'away': 'Pioneer League', 'home': 'Pioneer League'},
            'sport_level': {'away': 'Partner', 'home': 'Partner'},
            'source': 'partner',
            'game_code': game_code,
        },
        'box_score': {
            'away_batting': away_batters,
            'home_batting': home_batters,
            'away_pitching': away_pitchers,
            'home_pitching': home_pitchers,
        },
        'game_notes': game_notes,
        'format': 'pioneer_html',
    }


def parse_pioneer_html_batting(table) -> List[Dict[str, Any]]:
    """Parse a Pioneer League HTML batting table."""
    batters = []

    rows = table.find_all('tr')
    headers = _pioneer_header_index(table)
    for row in rows[1:]:  # Skip header row
        cells = row.find_all(['th', 'td'])
        if len(cells) < 8:
            continue

        # First cell has position + name (e.g., "ssAnthony Mata")
        first_cell = cells[0].get_text(strip=True)
        if not first_cell or first_cell.lower() in ['totals', 'total', 'hitters']:
            continue

        # Extract position (lowercase letters/numbers at start like "ss", "2b", "lf") and name
        # Position can be: ss, 2b, 3b, 1b, c, lf, cf, rf, dh, p, pr, ph
        pos_match = re.match(r'^([a-z0-9]{1,4})\s*([A-Z].*)$', first_cell)
        if pos_match:
            position = pos_match.group(1).upper()
            name = pos_match.group(2).strip()
        else:
            position = ''
            name = first_cell

        # Columns: Name, AB, R, H, RBI, BB, SO, LOB, AVG (varies)
        try:
            batters.append({
                'name': name,
                'player_id': None,
                'position': position,
                'ab': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'AB', 1))),
                'r': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'R', 2))),
                'h': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'H', 3))),
                'rbi': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'RBI', 4))),
                'bb': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'BB', 5))),
                'k': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'SO', 6))),
                'lob': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'LOB', 7))),
                'doubles': 0,
                'triples': 0,
                'hr': 0,
                'sb': 0,
            })
        except (ValueError, IndexError):
            continue

    return batters


def parse_pioneer_html_pitching(table) -> List[Dict[str, Any]]:
    """Parse a Pioneer League HTML pitching table."""
    pitchers = []

    rows = table.find_all('tr')
    headers = _pioneer_header_index(table)
    for row in rows[1:]:  # Skip header row
        cells = row.find_all(['th', 'td'])
        if len(cells) < 7:
            continue

        name = cells[0].get_text(strip=True)
        if not name or name.lower() in ['totals', 'total', 'pitchers']:
            continue

        # Remove win/loss notation like "(L, 0-1)" or "(W, 1-0)"
        win = '(W' in name
        loss = '(L' in name
        save = '(S' in name
        name = re.sub(r'\([WLS][^)]*\)', '', name).strip()

        # Columns: Name, IP, H, R, ER, BB, SO, HR (varies)
        try:
            pitchers.append({
                'name': name,
                'player_id': None,
                'ip': _pioneer_cell_text(cells, _pioneer_index_for(headers, 'IP', 1), '0') or '0',
                'h': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'H', 2))),
                'r': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'R', 3))),
                'er': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'ER', 4))),
                'bb': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'BB', 5))),
                'k': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'SO', 6))),
                'hr': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'HR', 7))),
                'wp': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'WP', 8))),
                'bf': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'BF', 9))),
                'np': _safe_int_text(_pioneer_cell_text(cells, _pioneer_index_for(headers, 'NP', 11))),
                'win': win,
                'loss': loss,
                'save': save,
            })
        except (ValueError, IndexError):
            continue

    return pitchers


def parse_pioneer_xml(xml_content: str, game_code: str = '') -> Dict[str, Any]:
    """
    Parse Pioneer League XML box score format (legacy, kept for reference).

    Args:
        xml_content: Raw XML content
        game_code: Original game code for reference

    Returns:
        Game data dict in standard format
    """
    root = ET.fromstring(xml_content)

    # Extract game metadata
    venue_elem = root.find('.//venue')
    venue = venue_elem.text if venue_elem is not None else ''

    # Get date from game code or XML
    date_str = ''
    date_yyyymmdd = ''
    if game_code and len(game_code) >= 8:
        date_yyyymmdd = game_code[:8]
        try:
            date_obj = datetime.strptime(date_yyyymmdd, '%Y%m%d')
            date_str = date_obj.strftime('%m/%d/%Y')
        except ValueError:
            pass

    # Find teams
    teams = root.findall('.//team')
    away_team_data = None
    home_team_data = None

    for team in teams:
        vh = team.get('vh', '')
        if vh == 'V':
            away_team_data = team
        elif vh == 'H':
            home_team_data = team

    if not away_team_data or not home_team_data:
        raise ValueError("Could not find both teams in XML")

    away_team = away_team_data.get('name', '')
    home_team = home_team_data.get('name', '')

    # Get linescore for final score
    away_linescore = away_team_data.find('.//linescore')
    home_linescore = home_team_data.find('.//linescore')

    away_score = int(away_linescore.get('runs', 0)) if away_linescore is not None else 0
    home_score = int(home_linescore.get('runs', 0)) if home_linescore is not None else 0

    # Parse batting stats
    away_batters = parse_pioneer_batting(away_team_data)
    home_batters = parse_pioneer_batting(home_team_data)

    # Parse pitching stats
    away_pitchers = parse_pioneer_pitching(away_team_data)
    home_pitchers = parse_pioneer_pitching(home_team_data)

    return {
        'metadata': {
            'date': date_str,
            'date_yyyymmdd': date_yyyymmdd,
            'away_team': away_team,
            'away_team_short': away_team_data.get('code', ''),
            'away_team_id': (get_partner_team_data(away_team) or {}).get('id'),
            'away_team_logo': (get_partner_team_data(away_team) or {}).get('logo'),
            'home_team': home_team,
            'home_team_short': home_team_data.get('code', ''),
            'home_team_id': (get_partner_team_data(home_team) or {}).get('id'),
            'home_team_logo': (get_partner_team_data(home_team) or {}).get('logo'),
            'away_team_score': away_score,
            'home_team_score': home_score,
            'venue': venue,
            'parent_orgs': {'away': '', 'home': ''},
            'league': {'away': 'Pioneer League', 'home': 'Pioneer League'},
            'sport_level': {'away': 'Partner', 'home': 'Partner'},
            'source': 'partner',
            'game_code': game_code,
        },
        'box_score': {
            'away_batting': away_batters,
            'home_batting': home_batters,
            'away_pitching': away_pitchers,
            'home_pitching': home_pitchers,
        },
        'game_notes': {},
        'format': 'pioneer_xml',
    }


def parse_pioneer_batting(team_elem) -> List[Dict[str, Any]]:
    """Parse batting stats from Pioneer League XML team element."""
    batters = []

    for player in team_elem.findall('.//batter'):
        name = player.get('name', '')
        if not name:
            continue

        batters.append({
            'name': name,
            'player_id': player.get('uni', ''),
            'position': player.get('pos', ''),
            'ab': int(player.get('ab', 0)),
            'r': int(player.get('r', 0)),
            'h': int(player.get('h', 0)),
            'rbi': int(player.get('rbi', 0)),
            'bb': int(player.get('bb', 0)),
            'k': int(player.get('so', 0)),
            'doubles': int(player.get('d', 0)),
            'triples': int(player.get('t', 0)),
            'hr': int(player.get('hr', 0)),
            'sb': int(player.get('sb', 0)),
        })

    return batters


def parse_pioneer_pitching(team_elem) -> List[Dict[str, Any]]:
    """Parse pitching stats from Pioneer League XML team element."""
    pitchers = []

    for player in team_elem.findall('.//pitcher'):
        name = player.get('name', '')
        if not name:
            continue

        # Parse IP (may be in format "5.1" for 5 1/3)
        ip_str = player.get('ip', '0')

        pitchers.append({
            'name': name,
            'player_id': player.get('uni', ''),
            'ip': ip_str,
            'h': int(player.get('h', 0)),
            'r': int(player.get('r', 0)),
            'er': int(player.get('er', 0)),
            'bb': int(player.get('bb', 0)),
            'k': int(player.get('so', 0)),
            'hr': int(player.get('hr', 0)),
            'np': int(player.get('np', 0)),
            'win': player.get('win') == '1',
            'loss': player.get('loss') == '1',
            'save': player.get('save') == '1',
        })

    return pitchers


def fetch_pointstreak_boxscore(game_id: int, league: str = 'atlantic') -> Dict[str, Any]:
    """
    Fetch and parse a Pointstreak box score (Atlantic League, American Association, etc).

    Args:
        game_id: Pointstreak game ID
        league: League identifier ('atlantic', 'american_association', 'frontier')

    Returns:
        Parsed game data dict
    """
    url = f"https://baseball.pointstreak.com/boxscore.html?gameid={game_id}"
    print(f"Fetching {league} game: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    response = _session.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return parse_pointstreak_html(response.text, game_id, league)


def parse_pointstreak_html(html_content: str, game_id: int, league: str = 'atlantic') -> Dict[str, Any]:
    """
    Parse Pointstreak HTML box score format.

    Args:
        html_content: Raw HTML content
        game_id: Pointstreak game ID
        league: League identifier

    Returns:
        Game data dict in standard format
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    league_info = PARTNER_LEAGUES.get(league, PARTNER_LEAGUES['atlantic'])
    league_name = league_info['name']

    # Extract team names from title
    # Format: "Home vs. Away - League - boxscore" (Pointstreak uses Home first)
    away_team = ''
    home_team = ''
    title_elem = soup.find('title')
    if title_elem:
        title_text = title_elem.text
        match = re.match(r'(.+?)\s+vs\.?\s+(.+?)\s+-', title_text)
        if match:
            home_team = match.group(1).strip()  # First team is HOME
            away_team = match.group(2).strip()  # Second team is AWAY

    # Find date - look in the page text
    date_str = ''
    date_yyyymmdd = ''
    page_text = soup.get_text()
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', page_text)
    if date_match:
        date_str = date_match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            date_yyyymmdd = date_obj.strftime('%Y%m%d')
        except ValueError:
            pass

    # Find venue - look for "Location:" field first (most reliable)
    venue = ''
    # Try to find Location field (e.g., "Location: SIUH Community Park")
    location_match = re.search(r'Location[:\s]+([^\n]+)', page_text, re.I)
    if location_match:
        venue = location_match.group(1).strip()
    else:
        # Fallback: look for specific venue patterns
        venue_match = re.search(r'(?:played at|at)\s+([A-Z][^,\n]+(?:Stadium|Park|Ballpark|Complex)[^,\n]*)', page_text)
        if venue_match:
            parsed_venue = venue_match.group(1).strip()
            # Exclude false positives like "Left Field", "Center Field", "Right Field"
            if not re.match(r'^(Left|Center|Right)\s+Field', parsed_venue, re.I):
                venue = parsed_venue

    # Parse scores from nova-boxscore__record spans
    # Layout: Home team (left/first) | Away team (right/second)
    away_score = 0
    home_score = 0
    score_spans = soup.find_all('span', class_='nova-boxscore__record')
    if len(score_spans) >= 2:
        try:
            home_score = int(score_spans[0].text.strip())  # Home team is first on page
            away_score = int(score_spans[1].text.strip())  # Away team is second
        except ValueError:
            pass

    # Parse stats tables - first 4 nova-stats-table with team name headers
    # Tables 0,1 = batting (away, home), Tables 2,3 = pitching (away, home)
    stats_tables = soup.find_all('table', class_='nova-stats-table')

    away_batters = []
    home_batters = []
    away_pitchers = []
    home_pitchers = []

    # Identify stats tables (have team name headers, 9-10 columns of stats)
    # Table order: AWAY batting, HOME batting, AWAY pitching, HOME pitching
    table_idx = 0
    for table in stats_tables:
        rows = table.find_all('tr')
        # Skip tables with only 2 cells per row (play-by-play tables)
        if rows and len(rows) > 2:
            data_row = rows[2] if len(rows) > 2 else rows[1]
            cells = data_row.find_all('td')
            if len(cells) >= 8:  # Stats tables have 8+ columns
                if table_idx == 0:
                    away_batters = parse_pointstreak_stats_table(table, 'batting')
                elif table_idx == 1:
                    home_batters = parse_pointstreak_stats_table(table, 'batting')
                elif table_idx == 2:
                    away_pitchers = parse_pointstreak_stats_table(table, 'pitching')
                elif table_idx == 3:
                    home_pitchers = parse_pointstreak_stats_table(table, 'pitching')
                table_idx += 1
                if table_idx >= 4:
                    break

    # Look up team IDs and logos from partner team data
    away_team_lookup = get_partner_team_data(away_team) or {}
    home_team_lookup = get_partner_team_data(home_team) or {}

    return {
        'metadata': {
            'date': date_str,
            'date_yyyymmdd': date_yyyymmdd,
            'away_team': away_team,
            'away_team_short': '',
            'away_team_id': away_team_lookup.get('id'),
            'away_team_logo': away_team_lookup.get('logo'),
            'home_team': home_team,
            'home_team_short': '',
            'home_team_id': home_team_lookup.get('id'),
            'home_team_logo': home_team_lookup.get('logo'),
            'away_team_score': away_score,
            'home_team_score': home_score,
            'venue': venue or home_team_lookup.get('stadium', ''),  # Prefer parsed venue from Location field
            'parent_orgs': {'away': '', 'home': ''},
            'league': {'away': league_name, 'home': league_name},
            'sport_level': {'away': 'Partner', 'home': 'Partner'},
            'source': 'partner',
            'game_id': game_id,
        },
        'box_score': {
            'away_batting': away_batters,
            'home_batting': home_batters,
            'away_pitching': away_pitchers,
            'home_pitching': home_pitchers,
        },
        'game_notes': {},
        'format': 'pointstreak',
    }


def parse_pointstreak_stats_table(table, stat_type: str = 'batting') -> List[Dict[str, Any]]:
    """
    Parse a Pointstreak nova-stats-table for batting or pitching.

    Table format:
    - Row 0: Team name header
    - Row 1: Column headers
    - Row 2+: Player stats
    - Last row: Totals (skip)

    Batting columns: Jersey#, Name, Pos, AB, R, H, RBI, BB, K, AVG
    Pitching columns: Jersey#, Name, IP, H, R, ER, BB, K, ERA
    """
    players = []

    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 8:
            continue

        # First cell is jersey number
        jersey = cells[0].text.strip()
        if not jersey or not jersey.isdigit():
            continue

        # Second cell is player name (format: "LastName, F")
        name = cells[1].text.strip()
        if not name or name.lower() in ['totals', 'total']:
            continue

        if stat_type == 'batting':
            # Batting: Jersey#, Name, Pos, AB, R, H, RBI, BB, K, AVG
            try:
                players.append({
                    'name': name,
                    'player_id': None,
                    'position': cells[2].text.strip() if len(cells) > 2 else '',
                    'ab': int(cells[3].text.strip() or 0) if len(cells) > 3 else 0,
                    'r': int(cells[4].text.strip() or 0) if len(cells) > 4 else 0,
                    'h': int(cells[5].text.strip() or 0) if len(cells) > 5 else 0,
                    'rbi': int(cells[6].text.strip() or 0) if len(cells) > 6 else 0,
                    'bb': int(cells[7].text.strip() or 0) if len(cells) > 7 else 0,
                    'k': int(cells[8].text.strip() or 0) if len(cells) > 8 else 0,
                    'doubles': 0,
                    'triples': 0,
                    'hr': 0,
                    'sb': 0,
                })
            except (ValueError, IndexError):
                continue
        else:
            # Pitching: Jersey#, Name, IP, H, R, ER, BB, K, ERA
            try:
                players.append({
                    'name': name,
                    'player_id': None,
                    'ip': cells[2].text.strip() if len(cells) > 2 else '0',
                    'h': int(cells[3].text.strip() or 0) if len(cells) > 3 else 0,
                    'r': int(cells[4].text.strip() or 0) if len(cells) > 4 else 0,
                    'er': int(cells[5].text.strip() or 0) if len(cells) > 5 else 0,
                    'bb': int(cells[6].text.strip() or 0) if len(cells) > 6 else 0,
                    'k': int(cells[7].text.strip() or 0) if len(cells) > 7 else 0,
                    'hr': 0,
                    'np': 0,
                    'win': False,
                    'loss': False,
                    'save': False,
                })
            except (ValueError, IndexError):
                continue

    return players


def parse_pointstreak_batting_table(table) -> List[Dict[str, Any]]:
    """Parse a Pointstreak batting stats table."""
    batters = []

    rows = table.find_all('tr')
    headers = []

    for row in rows:
        cells = row.find_all(['th', 'td'])

        # Check if this is a header row
        if row.find('th'):
            headers = [c.text.strip().lower() for c in cells]
            continue

        if not headers or len(cells) < 2:
            continue

        # Create stat dict from row
        stats = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                stats[headers[i]] = cell.text.strip()

        # Extract player name
        name = stats.get('player', stats.get('name', stats.get('', '')))
        if not name or name.lower() in ['totals', 'total']:
            continue

        batters.append({
            'name': name,
            'player_id': None,
            'position': stats.get('pos', ''),
            'ab': int(stats.get('ab', 0) or 0),
            'r': int(stats.get('r', 0) or 0),
            'h': int(stats.get('h', 0) or 0),
            'rbi': int(stats.get('rbi', 0) or 0),
            'bb': int(stats.get('bb', 0) or 0),
            'k': int(stats.get('so', stats.get('k', 0)) or 0),
            'doubles': int(stats.get('2b', 0) or 0),
            'triples': int(stats.get('3b', 0) or 0),
            'hr': int(stats.get('hr', 0) or 0),
            'sb': int(stats.get('sb', 0) or 0),
        })

    return batters


def parse_pointstreak_pitching_table(table) -> List[Dict[str, Any]]:
    """Parse a Pointstreak pitching stats table."""
    pitchers = []

    rows = table.find_all('tr')
    headers = []

    for row in rows:
        cells = row.find_all(['th', 'td'])

        if row.find('th'):
            headers = [c.text.strip().lower() for c in cells]
            continue

        if not headers or len(cells) < 2:
            continue

        stats = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                stats[headers[i]] = cell.text.strip()

        name = stats.get('player', stats.get('name', stats.get('', '')))
        if not name or name.lower() in ['totals', 'total']:
            continue

        pitchers.append({
            'name': name,
            'player_id': None,
            'ip': stats.get('ip', '0'),
            'h': int(stats.get('h', 0) or 0),
            'r': int(stats.get('r', 0) or 0),
            'er': int(stats.get('er', 0) or 0),
            'bb': int(stats.get('bb', 0) or 0),
            'k': int(stats.get('so', stats.get('k', 0)) or 0),
            'hr': int(stats.get('hr', 0) or 0),
            'np': int(stats.get('np', stats.get('pitches', 0)) or 0),
            'win': 'W' in stats.get('dec', ''),
            'loss': 'L' in stats.get('dec', ''),
            'save': 'S' in stats.get('dec', ''),
        })

    return pitchers


def process_partner_game(
    game_id: str,
    league: str,
    cache_dir: Optional[Path] = None,
    enrich_with_bref_ids: bool = True,
    download_artifacts: bool = False,
    artifact_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Process a partner league game with optional caching.

    Args:
        game_id: Game identifier (game code for Pioneer, numeric ID for Pointstreak)
        league: League identifier ('pioneer', 'atlantic', 'american_association', 'frontier')
        cache_dir: Optional cache directory
        enrich_with_bref_ids: Whether to look up bref_ids for players (requires network for uncached rosters)
        download_artifacts: Whether to save Pioneer rendered source HTML and generated print PDF artifacts
        artifact_dir: Optional artifact root directory

    Returns:
        Processed game data dict
    """
    # Check cache first
    if cache_dir:
        cache_file = cache_dir / f"{league}_{game_id}.json"
        if cache_file.exists():
            print(f"Loading from cache: {cache_file}")
            with open(cache_file, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
                # Enrich with bref_ids if requested and not already populated
                if enrich_with_bref_ids:
                    enrich_players_with_bref_ids(game_data)
                if league == 'pioneer':
                    year = int(game_id[:4]) if len(game_id) >= 4 and game_id[:4].isdigit() else 2024
                    if download_artifacts:
                        try:
                            artifact_result = download_pioneer_boxscore_artifacts(
                                game_id,
                                year=year,
                                output_dir=artifact_dir,
                            )
                            artifact_paths = {
                                key: Path(path)
                                for key, path in pioneer_artifact_paths(game_id, year, artifact_dir).items()
                                if key in artifact_result.get('artifacts', {})
                            }
                            attach_pioneer_source_metadata(game_data, game_id, year, artifact_paths)
                            with open(cache_file, 'w', encoding='utf-8') as out:
                                json.dump(game_data, out, indent=2)
                            print(f"Saved Pioneer source artifacts for {game_id}")
                        except Exception as e:
                            print(f"Warning: could not save Pioneer source artifacts for {game_id}: {e}")
                    else:
                        attach_pioneer_source_metadata(game_data, game_id, year)
                return game_data

    # Fetch based on league format
    if league == 'pioneer':
        # game_id is the game code (e.g., "20240828_fhp1")
        # Extract year from game code
        year = int(game_id[:4]) if len(game_id) >= 4 and game_id[:4].isdigit() else 2024
        game_data = fetch_pioneer_boxscore(game_id, year)
        if download_artifacts:
            try:
                artifact_result = download_pioneer_boxscore_artifacts(
                    game_id,
                    year=year,
                    output_dir=artifact_dir,
                )
                artifact_paths = {
                    key: Path(path)
                    for key, path in pioneer_artifact_paths(game_id, year, artifact_dir).items()
                    if key in artifact_result.get('artifacts', {})
                }
                attach_pioneer_source_metadata(game_data, game_id, year, artifact_paths)
                print(f"Saved Pioneer source artifacts for {game_id}")
            except Exception as e:
                print(f"Warning: could not save Pioneer source artifacts for {game_id}: {e}")
    else:
        # Pointstreak format
        game_data = fetch_pointstreak_boxscore(int(game_id), league)

    # Enrich with bref_ids if requested
    if enrich_with_bref_ids:
        enrich_players_with_bref_ids(game_data)

    # Save to cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{league}_{game_id}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2)
        print(f"Cached to {cache_file}")

    return game_data


def load_partner_game_ids(game_ids_file: Path) -> List[Dict[str, str]]:
    """
    Load partner league game IDs from a text file.

    File format (one per line):
        league:game_id  # optional comment

    Examples:
        pioneer:20240828_fhp1
        atlantic:612415  # Lancaster vs Staten Island
        american_association:580142

    Args:
        game_ids_file: Path to text file

    Returns:
        List of dicts with 'league' and 'game_id' keys
    """
    if not game_ids_file.exists():
        return []

    games = []
    with open(game_ids_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Strip inline comments
            if '#' in line:
                line = line.split('#')[0].strip()

            if ':' in line:
                league, game_id = line.split(':', 1)
                games.append({
                    'league': league.strip().lower(),
                    'game_id': game_id.strip()
                })
            else:
                print(f"Warning: Invalid format '{line}', expected 'league:game_id'")

    return games


def process_all_partner_games(
    game_ids_file: Path,
    cache_dir: Path,
    download_artifacts: bool = False,
    artifact_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Process all partner league games listed in the game IDs file.

    Args:
        game_ids_file: Path to text file with game IDs
        cache_dir: Cache directory
        download_artifacts: Whether to save Pioneer source artifacts while processing
        artifact_dir: Optional artifact root directory

    Returns:
        List of processed game data dicts
    """
    game_entries = load_partner_game_ids(game_ids_file)
    if not game_entries:
        print("No partner league game IDs found")
        return []

    print(f"Processing {len(game_entries)} partner league games...")
    games = []

    for entry in game_entries:
        league = entry['league']
        game_id = entry['game_id']

        try:
            game_data = process_partner_game(
                game_id,
                league,
                cache_dir,
                download_artifacts=download_artifacts,
                artifact_dir=artifact_dir,
            )
            games.append(game_data)

            meta = game_data['metadata']
            away = meta.get('away_team', 'Unknown')
            home = meta.get('home_team', 'Unknown')
            date = meta.get('date', 'Unknown date')
            league_name = meta.get('league', {}).get('home', league)
            print(f"  [{league_name}] {date}: {away} @ {home}")

        except Exception as e:
            print(f"  Error processing {league}:{game_id}: {e}")

    return games


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python partner_leagues.py <league> <game_id>")
        print("  Leagues: pioneer, atlantic, american_association, frontier")
        print("  Examples:")
        print("    python partner_leagues.py pioneer 20240828_fhp1")
        print("    python partner_leagues.py atlantic 612415")
        sys.exit(1)

    league = sys.argv[1]
    game_id = sys.argv[2]

    game_data = process_partner_game(game_id, league)

    meta = game_data['metadata']
    print(f"\nGame: {meta['away_team']} @ {meta['home_team']}")
    print(f"Date: {meta['date']}")
    print(f"Score: {meta['away_team_score']} - {meta['home_team_score']}")
    print(f"Venue: {meta['venue']}")
    print(f"League: {meta['league']}")

    print(f"\nAway batters: {len(game_data['box_score']['away_batting'])}")
    print(f"Home batters: {len(game_data['box_score']['home_batting'])}")
    print(f"Away pitchers: {len(game_data['box_score']['away_pitching'])}")
    print(f"Home pitchers: {len(game_data['box_score']['home_pitching'])}")
