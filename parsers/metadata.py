"""
Metadata extraction from NCAA baseball box score PDFs.
"""

import re


# Map team names to their home cities/venues
TEAM_HOME_CITIES = {
    'virginia': ['charlottesville', 'davenport'],
    'california': ['berkeley'],
    'stanford': ['stanford', 'palo alto', 'sunken diamond'],
    'san francisco': ['san francisco', 'benedetti'],
    'ucla': ['los angeles', 'jackie robinson'],
    'usc': ['los angeles', 'dedeaux'],
    'arizona': ['tucson', 'hi corbett'],
    'arizona state': ['tempe', 'phoenix municipal'],
    'florida': ['gainesville'],
    'lsu': ['baton rouge', 'alex box'],
    'texas': ['austin', 'disch-falk'],
    'vanderbilt': ['nashville', 'hawkins'],
    'tennessee': ['knoxville', 'lindsey nelson'],
    'nc state': ['raleigh', 'doak'],
    'north carolina': ['chapel hill', 'boshamer'],
    'wake forest': ['winston-salem'],
    'clemson': ['clemson'],
    'georgia': ['athens', 'foley'],
    'arkansas': ['fayetteville', 'baum'],
    'ole miss': ['oxford', 'swayze'],
    'mississippi state': ['starkville', 'dudy noble'],
    'oregon state': ['corvallis', 'goss'],
}


def extract_game_metadata(text: str) -> dict:
    """Extract game metadata from PDF text (Format A)."""
    metadata = {
        "date": None,
        "venue": None,
        "stadium": None,
        "city": None,
        "away_team": None,
        "away_team_rank": None,
        "away_team_record": None,
        "away_team_score": None,
        "home_team": None,
        "home_team_rank": None,
        "home_team_record": None,
        "home_team_score": None,
        "attendance": None,
        "duration": None,
        "start_time": None,
        "weather": None,
        "umpires": {}
    }

    # Extract date (format: February 20, 2018 or 2/20/2018)
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
    if date_match:
        metadata["date"] = date_match.group(1)
    else:
        date_match = re.search(r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})', text)
        if date_match:
            metadata["date"] = date_match.group(1)

    # Extract venue/stadium and city
    # Format: "at Davenport Field (Charlottesville, Va.)"
    venue_match = re.search(r'at\s+([A-Za-z\s]+(?:Field|Stadium|Park|Center|Arena|Coliseum|Complex))\s*\(([^)]+)\)', text)
    if venue_match:
        metadata["stadium"] = venue_match.group(1).strip()
        metadata["city"] = venue_match.group(2).strip()
        metadata["venue"] = f"{metadata['stadium']} ({metadata['city']})"
    else:
        # Fallback: try simpler pattern
        venue_match = re.search(r'at\s+([^(]+)\s*\(([^)]+)\)', text)
        if venue_match:
            metadata["stadium"] = venue_match.group(1).strip()
            metadata["city"] = venue_match.group(2).strip()
            metadata["venue"] = f"{metadata['stadium']} ({metadata['city']})"

    # Extract teams and scores - look for box score header format
    # "VMI 9 (2-2)" or "#18 Virginia 4 (2-2)" on same line
    # Also handles "VMI 9 (2-2) Virginia 4 (2-2)" format
    box_header = re.search(r'(#\d+\s+)?([A-Za-z]+)\s+(\d+)\s+\((\d+-\d+)\)\s+(#\d+\s+)?([A-Za-z]+)\s+(\d+)\s+\((\d+-\d+)\)', text)
    if box_header:
        # Away team (first)
        metadata["away_team_rank"] = box_header.group(1).strip() if box_header.group(1) else None
        metadata["away_team"] = box_header.group(2).strip()
        metadata["away_team_score"] = int(box_header.group(3))
        metadata["away_team_record"] = box_header.group(4)

        # Home team (second)
        metadata["home_team_rank"] = box_header.group(5).strip() if box_header.group(5) else None
        metadata["home_team"] = box_header.group(6).strip()
        metadata["home_team_score"] = int(box_header.group(7))
        metadata["home_team_record"] = box_header.group(8)
    else:
        # Fallback: look for separate patterns
        team_pattern = r'(#\d+\s+)?([A-Za-z\s\.]+?)\s+(\d+)\s+\((\d+-\d+)\)'
        teams = re.findall(team_pattern, text[:1000])

        if len(teams) >= 2:
            metadata["away_team_rank"] = teams[0][0].strip() if teams[0][0] else None
            metadata["away_team"] = teams[0][1].strip()
            metadata["away_team_score"] = int(teams[0][2])
            metadata["away_team_record"] = teams[0][3]

            metadata["home_team_rank"] = teams[1][0].strip() if teams[1][0] else None
            metadata["home_team"] = teams[1][1].strip()
            metadata["home_team_score"] = int(teams[1][2])
            metadata["home_team_record"] = teams[1][3]

    # Also look for title format: "VMI at Virginia" to confirm home/away
    matchup = re.search(r'^([A-Za-z]+)\s+at\s+(#?\d*\s*[A-Za-z]+)', text, re.MULTILINE)
    if matchup:
        away_name = matchup.group(1).strip()
        home_match = matchup.group(2).strip()
        # Check if home team has a rank
        home_rank_match = re.match(r'(#\d+)\s+(.+)', home_match)
        if home_rank_match:
            if not metadata["home_team_rank"]:
                metadata["home_team_rank"] = home_rank_match.group(1)

    # Look for rankings in page 1 format: "#18 Virginia" on its own line
    # Check for away team rank
    if not metadata["away_team_rank"] and metadata["away_team"]:
        away_rank = re.search(rf'(#\d+)\s+{re.escape(metadata["away_team"])}', text)
        if away_rank:
            metadata["away_team_rank"] = away_rank.group(1)

    # Check for home team rank
    if not metadata["home_team_rank"] and metadata["home_team"]:
        home_rank = re.search(rf'(#\d+)\s+{re.escape(metadata["home_team"])}', text)
        if home_rank:
            metadata["home_team_rank"] = home_rank.group(1)

    # Extract attendance
    attendance_match = re.search(r'Attendance:\s*([\d,]+)', text)
    if attendance_match:
        metadata["attendance"] = int(attendance_match.group(1).replace(',', ''))

    # Extract duration
    duration_match = re.search(r'Duration:\s*([\d:]+)', text)
    if duration_match:
        metadata["duration"] = duration_match.group(1)

    # Extract start time
    start_match = re.search(r'Start:\s*(\d{1,2}:\d{2}\s*[AP]M)', text)
    if start_match:
        metadata["start_time"] = start_match.group(1)

    # Extract weather
    weather_match = re.search(r'Weather:\s*(.+?)(?:\n|$)', text)
    if weather_match:
        metadata["weather"] = weather_match.group(1).strip()

    # Extract umpires
    umpires_match = re.search(r'Umpires\s*-\s*HP:\s*([^;]+);\s*1B:\s*([^;]+);\s*2B:\s*([^;]+);\s*3B:\s*([^.\n]+)', text)
    if umpires_match:
        metadata["umpires"] = {
            "home_plate": umpires_match.group(1).strip(),
            "first_base": umpires_match.group(2).strip(),
            "second_base": umpires_match.group(3).strip(),
            "third_base": umpires_match.group(4).strip()
        }

    # Venue-based home/away validation
    # If venue/city contains one team's name but not the other, that team should be home
    metadata["_teams_swapped"] = False
    venue = metadata.get("venue", "") or ""
    city = metadata.get("city", "") or ""
    venue_city = (venue + " " + city).lower()
    away_team = (metadata.get("away_team") or "").lower()
    home_team = (metadata.get("home_team") or "").lower()

    if away_team and home_team and venue_city:
        # Check if venue suggests teams should be swapped
        away_home_cities = TEAM_HOME_CITIES.get(away_team, [away_team])
        home_home_cities = TEAM_HOME_CITIES.get(home_team, [home_team])

        away_in_venue = any(city_name in venue_city for city_name in away_home_cities)
        home_in_venue = any(city_name in venue_city for city_name in home_home_cities)

        # Also check if team name is directly in venue
        if not away_in_venue:
            away_in_venue = away_team in venue_city
        if not home_in_venue:
            home_in_venue = home_team in venue_city

        if away_in_venue and not home_in_venue:
            # Away team's venue - they should be home, swap!
            metadata["_teams_swapped"] = True

    return metadata


def extract_format_b_metadata(text: str) -> dict:
    """Extract metadata from format B PDFs."""
    metadata = {
        "date": None,
        "venue": None,
        "stadium": None,
        "city": None,
        "away_team": None,
        "away_team_rank": None,
        "away_team_record": None,
        "away_team_score": None,
        "home_team": None,
        "home_team_rank": None,
        "home_team_record": None,
        "home_team_score": None,
        "attendance": None,
        "duration": None,
        "start_time": None,
        "weather": None,
        "umpires": {}
    }

    # Format variations:
    # 1. "# 15 UCLA (48-17) -vs- # 6 LSU (50-15)" - ranked teams with W-L record
    # 2. "Arizona (16-13, 9-5 PAC-12) -vs- California (16-12, 5-9 PAC-12)" - conference record
    # 3. "Arizona (0) -vs- Coastal Carolina (0)" - single number (tournament series)
    # 4. "LMU (22-20) -vs- Saint Mary's (21-19)" - team names with apostrophes
    # Pattern handles: optional ranking, team name (including apostrophes), parenthesized record
    matchup = re.search(
        r"(?:#\s*(\d+)\s+)?([A-Za-z\s']+?)\s*\(([^)]+)\)\s*-vs-\s*(?:#\s*(\d+)\s+)?([A-Za-z\s']+?)\s*\(([^)]+)\)",
        text
    )
    if matchup:
        # Away team
        metadata["away_team_rank"] = f"#{matchup.group(1)}" if matchup.group(1) else None
        metadata["away_team"] = matchup.group(2).strip()
        metadata["away_team_record"] = matchup.group(3)

        # Home team
        metadata["home_team_rank"] = f"#{matchup.group(4)}" if matchup.group(4) else None
        metadata["home_team"] = matchup.group(5).strip()
        metadata["home_team_record"] = matchup.group(6)

    # Extract date - format: 6/17/2023 or M/D/YYYY
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
    if date_match:
        metadata["date"] = date_match.group(1)

    # Extract venue - format: "at City, State (Stadium)"
    venue_match = re.search(r'at\s+([^(]+)\s*\(([^)]+)\)', text)
    if venue_match:
        metadata["city"] = venue_match.group(1).strip()
        metadata["stadium"] = venue_match.group(2).strip()
        metadata["venue"] = f"{metadata['stadium']} ({metadata['city']})"

    # Extract scores from line like "UCLA 5 LSU 9" (appears after score by innings)
    if metadata["away_team"] and metadata["home_team"]:
        # Pattern: "Team1 X Team2 Y" on its own line
        pattern = rf'^{re.escape(metadata["away_team"])}\s+(\d+)\s+{re.escape(metadata["home_team"])}\s+(\d+)\s*$'
        score_match = re.search(pattern, text, re.MULTILINE)
        if score_match:
            metadata["away_team_score"] = int(score_match.group(1))
            metadata["home_team_score"] = int(score_match.group(2))

    # Extract attendance
    attendance_match = re.search(r'Attendance[:\s]+(\d[\d,]*)', text, re.IGNORECASE)
    if attendance_match:
        metadata["attendance"] = int(attendance_match.group(1).replace(',', ''))

    # Extract duration
    duration_match = re.search(r'Time[:\s]+(\d+:\d+)', text, re.IGNORECASE)
    if duration_match:
        metadata["duration"] = duration_match.group(1)

    # Extract start time
    start_match = re.search(r'Start[:\s]+(\d{1,2}:\d{2}\s*(?:am|pm)?)', text, re.IGNORECASE)
    if start_match:
        metadata["start_time"] = start_match.group(1)

    # Extract weather
    weather_match = re.search(r'Weather[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
    if weather_match:
        metadata["weather"] = weather_match.group(1).strip()

    # Extract umpires
    umpires_match = re.search(r'Umpires?[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
    if umpires_match:
        metadata["umpires"]["list"] = umpires_match.group(1).strip()

    return metadata
