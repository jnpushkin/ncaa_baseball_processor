"""
Game notes extraction from NCAA baseball box score PDFs.
"""

import re


def extract_game_notes(text: str) -> dict:
    """Extract additional game statistics from the notes section.

    Parses both format A (e.g., "HR - Player (count)") and format B (e.g., "HR: Player (count)")
    """
    notes = {
        "errors": [],        # E - Player
        "double_plays": {},  # DP - Team count
        "doubles": [],       # 2B - Player (season)
        "triples": [],       # 3B - Player (season)
        "home_runs": [],     # HR - Player count (season)
        "stolen_bases": [],  # SB - Player
        "caught_stealing": [], # CS - Player
        "hit_by_pitch": [],  # HBP - Player (season)
        "intentional_walks": [], # IBB - Player
        "strikeouts_looking": [], # KL - Player
        "grounded_into_dp": [], # GDP - Player
        "wild_pitches": [],  # WP - Player
        "passed_balls": [],  # PB - Player
        "hit_batters": [],   # HB - Pitcher
        "balks": [],         # BK - Pitcher
        "win": None,         # Win - Player (record)
        "loss": None,        # Loss - Player (record)
        "save": None,        # Save - Player (count) or None
    }

    # Extract errors: E - Player1 ; Player2 ; or E: Player
    errors_match = re.search(r'E\s*[-:]\s*([^;]+(?:;\s*[^;]+)*?)(?:;?\s*DP|;?\s*$|\n)', text)
    if errors_match:
        errors_str = errors_match.group(1)
        notes["errors"] = [e.strip() for e in errors_str.split(';') if e.strip() and 'DP' not in e]

    # Extract double plays: DP - Team1 X or DP: X
    dp_match = re.search(r'DP\s*[-:]\s*(\d+|[^.]+?)(?:\.|$|\n)', text)
    if dp_match:
        dp_str = dp_match.group(1).strip()
        if dp_str.isdigit():
            notes["double_plays"]["count"] = int(dp_str)
        else:
            for dp in dp_str.split(';'):
                parts = dp.strip().rsplit(' ', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    notes["double_plays"][parts[0].strip()] = int(parts[1])

    # Extract doubles: 2B - Player (season) ; or 2B: Player (count)
    # Common stat prefixes to filter out
    stat_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E|3B|HR)\b'
    doubles_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E|3B|HR)\b'

    # Use findall to capture ALL 2B entries
    # Format A: "2B - Player (count)" at start of line
    # Format B: "2B - Player (count)" mid-line, terminated by ; or next stat
    # Note: "2B: Umpire Name" in umpire line doesn't have parentheses - skip those
    doubles_matches = re.findall(r'(?:^|;\s*)2B\s*[-:]\s*([^;]+?)(?=\s*;|\s*$|\s*(?:3B|HR|SB|CS|SH|SF|WP|PB|KL|HBP|GDP|LOB|DP|BK|IBB|E)\s*[-:])', text, re.MULTILINE)
    for doubles_line in doubles_matches:
        for item in doubles_line.split(';'):
            item = item.strip()
            # Skip items that are clearly not doubles
            if item and not re.match(doubles_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    # Skip if player name looks like a stat prefix
                    if not re.match(doubles_prefixes, player_name, re.IGNORECASE):
                        notes["doubles"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })
                # Don't add items without parentheses - they might be umpire names

    # Extract triples: 3B - Player count (season) ;
    # Use findall to capture ALL 3B entries (Format A at line start, Format B mid-line)
    # Note: "3B: Umpire Name" in umpire line doesn't have parentheses - skip those
    triples_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E|2B|HR)\b'
    triples_matches = re.findall(r'(?:^|;\s*)3B\s*[-:]\s*([^;]+?)(?=\s*;|\s*$|\s*(?:2B|HR|SB|CS|SH|SF|WP|PB|KL|HBP|GDP|LOB|DP|BK|IBB|E)\s*[-:])', text, re.MULTILINE)
    for triples_line in triples_matches:
        for item in triples_line.split(';'):
            item = item.strip()
            if item and not re.match(triples_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    if not re.match(triples_prefixes, player_name, re.IGNORECASE):
                        notes["triples"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })
                # Don't add items without parentheses - they might be umpire names

    # Extract home runs: HR - Player count (season) ; or HR: Player (count)
    # Use findall to capture ALL HR entries (Format A at line start, Format B mid-line)
    hr_matches = re.findall(r'(?:^|;\s*)HR\s*[-:]\s*([^;]+?)(?=\s*;|\s*$|\s*(?:2B|3B|SB|CS|SH|SF|WP|PB|KL|HBP|GDP|LOB|DP|BK|IBB|E)\s*[-:])', text, re.MULTILINE)
    for hr_line in hr_matches:
        for item in hr_line.split(';'):
            item = item.strip()
            # Skip items that are clearly not home runs (SH, SF, HBP, CS, SB, etc.)
            # Use word boundary \b to catch formats like "HBP - Player" or "SF Player"
            stat_prefixes = r'^(SH|SF|SFA|HBP|CS|SB|GDP|LOB|DP|WP|PB|BK|IBB|E)\b'
            if item and not re.match(stat_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    # Skip if player name looks like a stat prefix
                    if not re.match(stat_prefixes, player_name, re.IGNORECASE):
                        notes["home_runs"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })

    # Extract stolen bases: SB - Player count (season) ;
    # Use findall to capture ALL SB entries (Format A at line start, Format B mid-line)
    sb_prefixes = r'^(CS|GDP|LOB|DP|WP|PB|BK|IBB|E)\b'
    sb_matches = re.findall(r'(?:^|;\s*)SB\s*[-:]\s*([^;]+?)(?=\s*;|\s*$|\s*(?:2B|3B|HR|CS|SH|SF|WP|PB|KL|HBP|GDP|LOB|DP|BK|IBB|E)\s*[-:])', text, re.MULTILINE)
    for sb_line in sb_matches:
        for item in sb_line.split(';'):
            item = item.strip()
            if item and 'CS' not in item and not re.match(sb_prefixes, item, re.IGNORECASE):
                match = re.match(r'([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)', item)
                if match:
                    player_name = match.group(1).strip()
                    if not re.match(sb_prefixes, player_name, re.IGNORECASE):
                        notes["stolen_bases"].append({
                            "player": player_name,
                            "game_count": int(match.group(2)) if match.group(2) else 1,
                            "season_total": int(match.group(3))
                        })
                elif item and not re.match(sb_prefixes, item, re.IGNORECASE):
                    notes["stolen_bases"].append({"player": item, "game_count": 1, "season_total": None})

    # Extract caught stealing: CS - Player (count) ; (single line only)
    cs_match = re.search(r'^CS\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if cs_match:
        for item in cs_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                notes["caught_stealing"].append(item)

    # Extract hit by pitch (batters): HBP - Player (count) ; or HBP: Player (count)
    # Note: Format B also has "HBP:" for pitchers who hit batters
    hbp_match = re.search(r'^HBP\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if hbp_match:
        for item in hbp_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                notes["hit_by_pitch"].append(item)

    # Extract grounded into double play: GDP - Player ;
    gdp_match = re.search(r'^GDP\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if gdp_match:
        for item in gdp_match.group(1).split(';'):
            item = item.strip()
            if item and 'LOB' not in item:
                notes["grounded_into_dp"].append(item)

    # Extract win/loss/save - both "Win - Player (record)" and "Win: Player (record)"
    win_match = re.search(r'Win\s*[-:]\s*([^(]+)\s*\((\d+-\d+)\)', text)
    if win_match:
        notes["win"] = {"player": win_match.group(1).strip(), "record": win_match.group(2)}

    loss_match = re.search(r'Loss\s*[-:]\s*([^(]+)\s*\((\d+-\d+)\)', text)
    if loss_match:
        notes["loss"] = {"player": loss_match.group(1).strip(), "record": loss_match.group(2)}

    # Check for "Save - None" FIRST before trying to parse a save with count
    # Otherwise the greedy regex can match across lines (e.g., "Save - None.\nWP - Pitcher (3)")
    if re.search(r'Save\s*[-:]\s*None', text, re.IGNORECASE):
        notes["save"] = None
    else:
        # Only match save on a single line to avoid capturing WP/HBP data
        save_match = re.search(r'Save\s*[-:]\s*([^(\n]+)\s*\((\d+)\)', text)
        if save_match:
            notes["save"] = {"player": save_match.group(1).strip(), "count": int(save_match.group(2))}

    # Extract wild pitches: WP - Pitcher (count)
    # Format B has multiple stats on one line, so use lookahead to stop at next stat prefix
    # This ensures we don't capture HB data that follows WP on the same line
    wp_match = re.search(r'(?:^|;\s*)WP\s*[-:]\s*([^;]+?)(?=\s*;?\s*(?:HB|PB|SFA|SH|SF|BK)\s*[-:]|\s*;?\s*$)', text, re.MULTILINE)
    if wp_match:
        for item in wp_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                # Only accept if it has a count in parentheses (avoids stray names)
                if re.search(r'\(\d+\)', item):
                    notes["wild_pitches"].append(item)

    # Extract passed balls: PB - Player ; (single line only)
    pb_match = re.search(r'^PB\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if pb_match:
        for item in pb_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                notes["passed_balls"].append(item)

    # Extract sacrifice hits: SH - Player (count) (single line only)
    sh_match = re.search(r'^SH\s*[-:]\s*(.+?)$', text, re.MULTILINE)
    if sh_match:
        notes["sacrifice_hits"] = []
        for item in sh_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                notes["sacrifice_hits"].append(item)

    # Extract hit batters (pitchers who hit batters): HB - Pitcher count (season)
    # Format B has this inline: "HB - Turkington,A 3 (6) ; Dessart,S (1)"
    # Multiple pitchers may be listed, separated by semicolons, until next stat prefix
    hb_match = re.search(r'(?:^|;\s*)HB\s*[-:]\s*(.+?)(?=\s*;?\s*(?:WP|PB|SFA|SH|SF|BK)\s*[-:]|\s*;?\s*$)', text, re.MULTILINE)
    if hb_match:
        for item in hb_match.group(1).split(';'):
            item = item.strip()
            if item and item.lower() != 'none':
                # Only accept if it has a count in parentheses
                if re.search(r'\(\d+\)', item):
                    notes["hit_batters"].append(item)

    return notes
