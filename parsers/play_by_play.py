"""
Play-by-play parsing for NCAA baseball box scores.
"""

import re


def parse_innings_from_text(text: str) -> list:
    """Extract runs per inning from score line."""
    # Pattern: team name followed by numbers
    pattern = r'^\s*(?:VMI|Virginia|[A-Za-z\s\.#\d]+)\s+([\d\s]+)\s+\d+\s+\d+\s+\d+\s+\d+\s*$'
    innings = []
    for line in text.split('\n'):
        # Look for lines with score by innings data
        parts = line.strip().split()
        if len(parts) >= 13:  # At least 9 innings + R H E LOB
            try:
                # Try to extract 9 inning scores
                innings = [int(parts[i]) for i in range(1, 10) if parts[i].isdigit()]
                if len(innings) == 9:
                    return innings
            except (ValueError, IndexError):
                continue
    return innings


def parse_format_b_play_by_play(text: str) -> dict:
    """Parse play-by-play from format B PDFs."""
    innings = {}
    current_inning = None
    current_half = None

    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Detect team batting indicator - "Team - Top/Bottom of Xth"
        half_match = re.search(r'([A-Za-z\s]+)\s*-\s*(Top|Bottom)\s+of\s+(\d+)', stripped, re.IGNORECASE)
        if half_match:
            current_inning = int(half_match.group(3))
            current_half = "top" if half_match.group(2).lower() == "top" else "bottom"
            if current_inning not in innings:
                innings[current_inning] = {"top": [], "bottom": []}
            continue

        # Skip summary lines
        if stripped.startswith('Runs:') or stripped.startswith('No play'):
            continue

        # Parse play events
        if current_inning and current_half and stripped:
            # Extract pitch count if present
            pitch_match = re.search(r'\((\d-\d\s*[BKFSX]*)\)', stripped)
            pitch_count = pitch_match.group(1) if pitch_match else None

            # Check for RBI
            rbi_match = re.search(r'(\d+)\s*RBI', stripped)
            rbi = int(rbi_match.group(1)) if rbi_match else 0
            if ', RBI' in stripped and not rbi_match:
                rbi = 1

            # Skip if this looks like just a score line (just numbers)
            if re.match(r'^\d+\s+\d+\s*$', stripped):
                continue

            event = {
                "description": stripped,
                "pitch_count": pitch_count,
                "rbi": rbi
            }

            innings[current_inning][current_half].append(event)

    return innings


def parse_play_by_play(text: str) -> dict:
    """Parse play-by-play text into structured data."""
    innings = {}
    current_inning = None
    current_half = None
    in_scoring_summary = False

    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()

        # Detect and skip "Scoring Innings" summary section
        if 'Scoring Innings' in stripped:
            in_scoring_summary = True
            continue

        # Skip content in scoring summary section
        if in_scoring_summary:
            # Check if we've reached actual play-by-play again (new page)
            if re.match(r'^(\d+)(?:st|nd|rd|th)\s+Inning', stripped):
                in_scoring_summary = False
            else:
                continue

        # Detect inning headers
        inning_match = re.match(r'^(\d+)(?:st|nd|rd|th)\s+Inning', stripped)
        if inning_match:
            current_inning = int(inning_match.group(1))
            if current_inning not in innings:
                innings[current_inning] = {"top": [], "bottom": []}
            continue

        # Detect half-inning - format 1: "Top of 1st batting"
        if 'Top of' in stripped and 'batting' in stripped.lower():
            half_match = re.search(r'Top of (\d+)', stripped)
            if half_match:
                current_inning = int(half_match.group(1))
                if current_inning not in innings:
                    innings[current_inning] = {"top": [], "bottom": []}
            current_half = "top"
            continue
        elif 'Bottom of' in stripped and 'batting' in stripped.lower():
            half_match = re.search(r'Bottom of (\d+)', stripped)
            if half_match:
                current_inning = int(half_match.group(1))
                if current_inning not in innings:
                    innings[current_inning] = {"top": [], "bottom": []}
            current_half = "bottom"
            continue

        # Detect half-inning - format 2: "RU 1st -" or "VA 1st -" (team abbreviation + inning)
        # First occurrence of team is away (top), alternating after that
        team_inning_match = re.match(r'^([A-Z]{2,3})\s+(\d+)(?:st|nd|rd|th)\s*-', stripped)
        if team_inning_match:
            inning_num = int(team_inning_match.group(2))
            if inning_num not in innings:
                innings[inning_num] = {"top": [], "bottom": []}
            # Alternate between top and bottom based on whether we've seen this inning before
            if current_inning != inning_num:
                current_inning = inning_num
                current_half = "top"
            else:
                current_half = "bottom"
            # Don't continue - parse the rest of the line as events
            remaining = stripped[team_inning_match.end():].strip()
            if remaining and remaining != 'No play.':
                for event_text in remaining.split('.;'):
                    event_text = event_text.strip()
                    if event_text and not re.match(r'^\d+\s+R,', event_text):
                        pitch_match = re.search(r'\((\d-\d\s*[BKFS]*)\)', event_text)
                        pitch_count = pitch_match.group(1) if pitch_match else None
                        rbi_match = re.search(r'(\d+)\s*RBI', event_text)
                        rbi = int(rbi_match.group(1)) if rbi_match else 0
                        if ', RBI' in event_text and not rbi_match:
                            rbi = 1
                        innings[current_inning][current_half].append({
                            "description": event_text.rstrip('.'),
                            "pitch_count": pitch_count,
                            "rbi": rbi
                        })
            continue

        # Skip summary lines and headers
        if not stripped or 'This Inning' in stripped or stripped.startswith('Score by'):
            continue
        if re.match(r'^[A-Z]+\s+\d+\s+\d+\s+\d+\s+\d+', stripped):  # Score line
            continue
        if 'starters:' in stripped.lower():
            continue
        # Skip inning summary lines like "6 R, 4 H, 1 E, 1 LOB."
        if re.match(r'^\d+\s+R,\s+\d+\s+H,\s+\d+\s+E,\s+\d+\s+LOB', stripped):
            continue
        # Skip page headers
        if 'Play By Play' in stripped or 'at Davenport Field' in stripped:
            continue

        # Parse play events
        if current_inning and current_half and stripped:
            # Skip if line looks like inning summary "R H E L" or team starter list
            if re.match(r'^\d+/[a-z]+/', stripped):  # Starter format: 4/ss/Eaton
                continue

            # Extract pitch count if present
            pitch_match = re.search(r'\((\d-\d\s*[BKFS]*)\)', stripped)
            pitch_count = pitch_match.group(1) if pitch_match else None

            # Check for RBI
            rbi_match = re.search(r'(\d+)\s*RBI', stripped)
            rbi = int(rbi_match.group(1)) if rbi_match else 0
            if ', RBI' in stripped and not rbi_match:
                rbi = 1

            event = {
                "description": stripped,
                "pitch_count": pitch_count,
                "rbi": rbi
            }

            innings[current_inning][current_half].append(event)

    return innings
