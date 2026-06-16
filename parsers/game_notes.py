"""
Game notes extraction from NCAA baseball box score PDFs.
"""

import re

# Stat labels that can appear in the box-score notes section. Used to find the
# end of one stat's player list (the next label) and to filter stray prefixes.
_STAT_LABELS = (
    "2B", "3B", "HR", "SB", "CS", "SH", "SF", "SFA", "WP", "PB", "KL",
    "HBP", "GDP", "LOB", "DP", "BK", "IBB", "E",
)


def _extract_stat_entries(text: str, label: str) -> list:
    """Extract all "<label>: Player (count)" entries for a counting stat.

    Handles three layouts seen in NCAA box scores:
      * Format A — one stat per line ("2B - Player (5)")
      * Format B — several stats on one line ("2B: P1 (1) 3B: P2 (1)")
      * Two-column box scores where pdfplumber merges the home/away note
        columns, so a label can appear mid-line after the other column's
        "(count) " (e.g. "SB: Lebron (1) 2B: Robbins (1); Mendoza (1)").

    The label is matched wherever it is not preceded by an alphanumeric (so it
    is a real prefix, not part of a name), and its player list is captured up to
    the next stat label or end of line, then split on ';'. Items without a
    "(count)" (e.g. base-umpire names in the umpires line) are skipped.
    """
    others = "|".join(l for l in _STAT_LABELS if l != label)
    pattern = (
        r"(?<![A-Za-z0-9])" + label + r"\s*[-:]\s*"
        r"(.+?)(?=(?<![A-Za-z0-9])(?:" + others + r")\s*[-:]|$)"
    )
    any_label = r"^(?:" + "|".join(_STAT_LABELS) + r")\b"
    entries = []
    for segment in re.findall(pattern, text, re.MULTILINE):
        for item in segment.split(";"):
            item = item.strip()
            if not item or re.match(any_label, item, re.IGNORECASE):
                continue
            match = re.match(r"([^(]+?)(?:\s*(\d+))?\s*\((\d+)\)", item)
            if not match:
                continue
            player_name = match.group(1).strip()
            if player_name and not re.match(any_label, player_name, re.IGNORECASE):
                entries.append({
                    "player": player_name,
                    "game_count": int(match.group(2)) if match.group(2) else 1,
                    "season_total": int(match.group(3)),
                })
    return entries


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

    # Extract doubles, triples, home runs, and stolen bases. Each handles
    # Format A (one stat per line), Format B (several stats per line), and
    # two-column box scores where a label appears mid-line. Items without a
    # "(count)" (e.g. base-umpire names) are skipped.
    notes["doubles"] = _extract_stat_entries(text, "2B")
    notes["triples"] = _extract_stat_entries(text, "3B")
    notes["home_runs"] = _extract_stat_entries(text, "HR")
    notes["stolen_bases"] = _extract_stat_entries(text, "SB")

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
