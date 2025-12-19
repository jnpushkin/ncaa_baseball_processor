#!/usr/bin/env python3
"""
Baseball Reference College Roster Scraper

Scrapes college baseball team rosters from Baseball Reference to get
player full names and bref IDs for linking statistics.
"""

import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, quote


BASE_URL = "https://www.baseball-reference.com"
SEARCH_URL = f"{BASE_URL}/search/search.fcgi"
TEAM_URL = f"{BASE_URL}/register/team.cgi"

# Rate limiting - be respectful
REQUEST_DELAY = 3.0  # seconds between requests

# Create a cloudscraper session to handle Cloudflare
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'darwin',
        'desktop': True
    }
)


@dataclass
class Player:
    """Player information from roster."""
    name: str
    bref_id: str
    first_name: str
    last_name: str
    position: Optional[str] = None
    number: Optional[str] = None
    year: Optional[str] = None


@dataclass
class TeamRoster:
    """Complete team roster."""
    team_name: str
    team_id: str
    year: Optional[str] = None
    conference: Optional[str] = None
    players: list = None

    def __post_init__(self):
        if self.players is None:
            self.players = []


def search_team(team_name: str, year: Optional[int] = None) -> list[dict]:
    """
    Search for a college team on Baseball Reference.

    Args:
        team_name: Name of the team (e.g., "Oregon State Beavers", "Virginia Cavaliers")
        year: Optional year to filter results

    Returns:
        List of matching teams with their IDs and info
    """
    print(f"Searching for team: {team_name}")

    params = {"search": team_name}

    try:
        response = scraper.get(SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error searching for team: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    teams = []

    # Look for search results in the "Foreign, Amateur, & Minor League Teams" section
    # or direct team links
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/register/team.cgi?id=' in href:
            # Extract team ID
            match = re.search(r'id=([a-f0-9]+)', href)
            if match:
                team_id = match.group(1)
                # Get text and clean up whitespace/newlines
                team_text = ' '.join(link.get_text().split())

                # Extract year from the text (format: "Team Name (YYYY-YYYY)")
                year_match = re.search(r'\((\d{4}(?:-\d{4})?)\)', team_text)
                team_year = year_match.group(1) if year_match else None

                # Clean up team name (remove year part)
                team_name_clean = re.sub(r'\s*\(\d{4}(?:-\d{4})?\)\s*', '', team_text).strip()

                # Extract conference if present in parent text
                parent_text = link.parent.get_text() if link.parent else ""
                conf_match = re.search(r'(?:NCAA Division I|Pac-12|ACC|SEC|Big 12|Big Ten|Big East)[^,)]*', parent_text)
                conference = conf_match.group(0) if conf_match else None

                team_info = {
                    "name": team_name_clean,
                    "id": team_id,
                    "year": team_year,
                    "conference": conference,
                    "url": urljoin(BASE_URL, href)
                }

                # Filter by year if specified
                if year:
                    if team_year and str(year) in team_year:
                        teams.append(team_info)
                else:
                    teams.append(team_info)

    # Remove duplicates based on team ID
    seen_ids = set()
    unique_teams = []
    for team in teams:
        if team["id"] not in seen_ids:
            seen_ids.add(team["id"])
            unique_teams.append(team)

    print(f"Found {len(unique_teams)} matching team(s)")
    return unique_teams


def fetch_roster(team_id: str) -> Optional[TeamRoster]:
    """
    Fetch the roster for a team given its Baseball Reference team ID.

    Args:
        team_id: The Baseball Reference team ID (e.g., "c1295e0d")

    Returns:
        TeamRoster object with all players, or None if fetch failed
    """
    url = f"{TEAM_URL}?id={team_id}"
    print(f"Fetching roster from: {url}")

    try:
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching roster: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract team name from page title
    title = soup.find('title')
    team_name = title.get_text().strip() if title else "Unknown Team"
    # Clean up title (remove " Statistics | Baseball-Reference.com")
    team_name = re.sub(r'\s*Statistics\s*\|\s*Baseball-Reference\.com', '', team_name).strip()

    # Try to extract year from title or h1
    year_match = re.search(r'(\d{4})', team_name)
    year = year_match.group(1) if year_match else None

    roster = TeamRoster(
        team_name=team_name,
        team_id=team_id,
        year=year
    )

    # Find player tables (batting and pitching)
    players_seen = set()  # Track by bref_id to avoid duplicates

    # Look for all tables that might contain player data
    tables = soup.find_all('table')

    # Also look for commented-out tables (Baseball Reference hides some data in comments)
    html = response.text
    comments = re.findall(r'<!--(.*?)-->', html, re.DOTALL)
    for comment in comments:
        if 'team_pitching' in comment.lower() or '/register/player.fcgi' in comment:
            comment_soup = BeautifulSoup(comment, 'html.parser')
            comment_tables = comment_soup.find_all('table')
            tables.extend(comment_tables)

    for table in tables:
        # Look for player links in the table
        for link in table.find_all('a', href=True):
            href = link['href']
            if '/register/player.fcgi?id=' in href:
                # Extract player ID
                match = re.search(r'id=([a-z0-9-]+)', href)
                if match:
                    bref_id = match.group(1)

                    if bref_id in players_seen:
                        continue
                    players_seen.add(bref_id)

                    player_name = link.get_text(strip=True)

                    # Parse name into first/last
                    first_name, last_name = parse_name(player_name)

                    # Try to get position from the row
                    row = link.find_parent('tr')
                    position = None
                    if row:
                        # Position is often in a specific column
                        cells = row.find_all(['td', 'th'])
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if cell_text in ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'OF', 'IF', 'UT']:
                                position = cell_text
                                break

                    player = Player(
                        name=player_name,
                        bref_id=bref_id,
                        first_name=first_name,
                        last_name=last_name,
                        position=position,
                        year=year
                    )
                    roster.players.append(player)

    print(f"Found {len(roster.players)} players")
    return roster


def parse_name(full_name: str) -> tuple[str, str]:
    """
    Parse a full name into first and last name components.

    Args:
        full_name: Full player name (e.g., "Travis Bazzana", "Jake McCarthy")

    Returns:
        Tuple of (first_name, last_name)
    """
    parts = full_name.strip().split()

    if len(parts) == 0:
        return ("", "")
    elif len(parts) == 1:
        return ("", parts[0])
    else:
        # Handle suffixes like Jr., III, etc.
        suffixes = {'jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v'}

        # Check if last part is a suffix
        if parts[-1].lower() in suffixes and len(parts) > 2:
            last_name = f"{parts[-2]} {parts[-1]}"
            first_name = " ".join(parts[:-2])
        else:
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])

        return (first_name, last_name)


def generate_bref_id(first_name: str, last_name: str, sequence: int = 0) -> str:
    """
    Generate a Baseball Reference-style ID for a player.

    Format: [last6][seq3][first3]
    - last6: First 6 chars of last name, padded with dashes
    - seq3: 3-digit sequence number
    - first3: First 3 chars of first name, padded with dashes

    Args:
        first_name: Player's first name
        last_name: Player's last name
        sequence: Sequence number for disambiguation (default 0)

    Returns:
        Generated bref ID string
    """
    # Clean and lowercase names
    last_clean = re.sub(r'[^a-z]', '', last_name.lower())
    first_clean = re.sub(r'[^a-z]', '', first_name.lower())

    # Pad/truncate to required lengths
    last_part = (last_clean + '------')[:6]
    first_part = (first_clean + '---')[:3]
    seq_part = f"{sequence:03d}"

    return f"{last_part}{seq_part}{first_part}"


def scrape_team_roster(team_name: str, year: Optional[int] = None, output_dir: str = "rosters") -> Optional[str]:
    """
    Search for a team and scrape its roster.

    Args:
        team_name: Name of the team to search for
        year: Optional year to filter results
        output_dir: Directory to save roster JSON files

    Returns:
        Path to saved roster file, or None if failed
    """
    # Search for the team
    teams = search_team(team_name, year)

    if not teams:
        print(f"No teams found matching '{team_name}'")
        return None

    # If multiple results, use the first one (most recent)
    team = teams[0]
    print(f"Using team: {team['name']} (ID: {team['id']})")

    time.sleep(REQUEST_DELAY)  # Rate limiting

    # Fetch the roster
    roster = fetch_roster(team['id'])

    if not roster or not roster.players:
        print("Failed to fetch roster or no players found")
        return None

    # Save to JSON
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create filename from team name
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', roster.team_name).strip('_').lower()
    filename = output_path / f"{safe_name}.json"

    # Convert to dict for JSON serialization
    roster_dict = {
        "team_name": roster.team_name,
        "team_id": roster.team_id,
        "year": roster.year,
        "players": [asdict(p) for p in roster.players]
    }

    with open(filename, 'w') as f:
        json.dump(roster_dict, f, indent=2)

    print(f"Saved roster to: {filename}")
    return str(filename)


def scrape_multiple_teams(team_names: list[str], year: Optional[int] = None, output_dir: str = "rosters") -> list[str]:
    """
    Scrape rosters for multiple teams.

    Args:
        team_names: List of team names to scrape
        year: Optional year to filter results
        output_dir: Directory to save roster JSON files

    Returns:
        List of paths to saved roster files
    """
    saved_files = []

    for i, team_name in enumerate(team_names):
        print(f"\n[{i+1}/{len(team_names)}] Processing: {team_name}")

        result = scrape_team_roster(team_name, year, output_dir)
        if result:
            saved_files.append(result)

        # Rate limiting between teams
        if i < len(team_names) - 1:
            print(f"Waiting {REQUEST_DELAY} seconds before next request...")
            time.sleep(REQUEST_DELAY)

    print(f"\nCompleted. Saved {len(saved_files)} roster(s)")
    return saved_files


def load_roster(roster_path: str) -> dict:
    """Load a roster JSON file."""
    with open(roster_path, 'r') as f:
        return json.load(f)


def lookup_player(roster: dict, name: str, number: Optional[str] = None) -> Optional[dict]:
    """
    Look up a player in a roster by name.

    Handles abbreviated names like "McCarthy, J." or "J. McCarthy"

    Args:
        roster: Roster dictionary with players list
        name: Player name to search for
        number: Optional jersey number for disambiguation

    Returns:
        Player dict if found, None otherwise
    """
    # Normalize the search name
    name_clean = name.strip()

    # Handle "Last, F." format
    if ',' in name_clean:
        parts = name_clean.split(',')
        last_name = parts[0].strip()
        first_initial = parts[1].strip().rstrip('.') if len(parts) > 1 else ""
    # Handle "F. Last" format
    elif '.' in name_clean.split()[0] if name_clean.split() else False:
        parts = name_clean.split()
        first_initial = parts[0].rstrip('.')
        last_name = ' '.join(parts[1:])
    else:
        # Full name format
        parts = name_clean.split()
        if len(parts) >= 2:
            first_initial = parts[0]
            last_name = parts[-1]
        else:
            last_name = name_clean
            first_initial = ""

    # Search through players
    for player in roster.get('players', []):
        player_last = player.get('last_name', '').lower()
        player_first = player.get('first_name', '').lower()

        # Check last name match
        if player_last != last_name.lower():
            continue

        # Check first name/initial match
        if first_initial:
            if not player_first.startswith(first_initial.lower()):
                continue

        # If we have a jersey number, use it to disambiguate
        if number and player.get('number'):
            if str(player.get('number')) != str(number):
                continue

        return player

    return None


def fetch_roster_by_id(team_id: str, output_dir: str = "rosters") -> Optional[str]:
    """
    Fetch roster directly using a known team ID.

    Args:
        team_id: Baseball Reference team ID
        output_dir: Directory to save roster JSON files

    Returns:
        Path to saved roster file, or None if failed
    """
    roster = fetch_roster(team_id)

    if not roster or not roster.players:
        print("Failed to fetch roster or no players found")
        return None

    # Save to JSON
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create filename from team name
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', roster.team_name).strip('_').lower()
    filename = output_path / f"{safe_name}.json"

    # Convert to dict for JSON serialization
    roster_dict = {
        "team_name": roster.team_name,
        "team_id": roster.team_id,
        "year": roster.year,
        "players": [asdict(p) for p in roster.players]
    }

    with open(filename, 'w') as f:
        json.dump(roster_dict, f, indent=2)

    print(f"Saved roster to: {filename}")
    return str(filename)


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Baseball Reference College Roster Scraper")
        print("\nUsage:")
        print("  python bref_roster_scraper.py <team_name> [year]")
        print("  python bref_roster_scraper.py --id <team_id>")
        print("  python bref_roster_scraper.py --file <teams_file> [year]")
        print("\nExamples:")
        print('  python bref_roster_scraper.py "Virginia Cavaliers"')
        print('  python bref_roster_scraper.py "Oregon State Beavers" 2024')
        print('  python bref_roster_scraper.py --id c1295e0d')
        print('  python bref_roster_scraper.py --file teams.txt 2024')
        print("\nThe teams.txt file should contain one team name per line.")
        print("\nKnown team IDs can be found by searching on baseball-reference.com")
        sys.exit(1)

    if sys.argv[1] == "--id":
        # Fetch by team ID directly
        if len(sys.argv) < 3:
            print("Error: Please specify a team ID")
            sys.exit(1)
        team_id = sys.argv[2]
        fetch_roster_by_id(team_id)

    elif sys.argv[1] == "--file":
        # Read team names from file
        if len(sys.argv) < 3:
            print("Error: Please specify a teams file")
            sys.exit(1)

        teams_file = sys.argv[2]
        year = int(sys.argv[3]) if len(sys.argv) > 3 else None

        with open(teams_file, 'r') as f:
            team_names = [line.strip() for line in f if line.strip()]

        scrape_multiple_teams(team_names, year)
    else:
        # Single team
        team_name = sys.argv[1]
        year = int(sys.argv[2]) if len(sys.argv) > 2 else None

        scrape_team_roster(team_name, year)
