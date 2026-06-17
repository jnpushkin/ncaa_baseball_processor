"""Parser for StatCrew/Sidearm NCAA baseball HTML box scores."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


_POSITION_RE = re.compile(
    r"^(?P<name>.+?)\s+"
    r"(?P<position>(?:p|c|1b|2b|3b|ss|lf|cf|rf|dh|ph|pr)"
    r"(?:/(?:p|c|1b|2b|3b|ss|lf|cf|rf|dh|ph|pr))*)$",
    re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _safe_int(value: Any) -> int:
    try:
        return int(_clean_text(value))
    except (TypeError, ValueError):
        return 0


def _safe_int_or_none(value: Any) -> Optional[int]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _display_name(value: str) -> str:
    text = _clean_text(value)
    text = re.sub(r"(?:\s+-?\d+)+$", "", text).strip()
    match = re.match(r"^(?P<last>[^,]+),\s+(?P<first>.+)$", text)
    if match:
        return _clean_text(f"{match.group('first')} {match.group('last')}")
    return text


def _split_player_position(value: str) -> tuple[str, str]:
    text = _clean_text(value)
    match = _POSITION_RE.match(text)
    if not match:
        return text, ""
    return _clean_text(match.group("name")), match.group("position").lower()


def _strip_leading_position(player_cell: str, position: str) -> str:
    text = _clean_text(player_cell)
    pos = _clean_text(position)
    if pos:
        text = re.sub(rf"^{re.escape(pos)}\s+", "", text, flags=re.IGNORECASE).strip()
    return text


def _split_sidearm_player_position(player_cell: str, position_cell: str = "") -> tuple[str, str]:
    position = _clean_text(position_cell).lower()
    text = _strip_leading_position(player_cell, position)
    if not position:
        text, position = _split_player_position(text)
    return _display_name(text), position


def _table_rows(table: Any) -> List[List[str]]:
    rows: List[List[str]] = []
    for tr in table.find_all("tr"):
        cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    return rows


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _clean_text(value).lower())


def _header_map(row: List[str]) -> Dict[str, int]:
    headers: Dict[str, int] = {}
    aliases = {
        "position": "pos",
        "runsbattedin": "rbi",
        "strikeouts": "so",
        "strikeoutslooking": "kl",
        "leftonbase": "lob",
        "atbats": "ab",
        "runsscored": "r",
        "hits": "h",
        "walks": "bb",
    }
    for index, cell in enumerate(row):
        key = aliases.get(_header_key(cell), _header_key(cell))
        if key and key not in headers:
            headers[key] = index
    if "player" not in headers and headers.get("ip") == 1:
        headers["player"] = 0
    return headers


def _row_value(row: List[str], headers: Dict[str, int], *keys: str) -> str:
    for key in keys:
        index = headers.get(key)
        if index is not None and index < len(row):
            return row[index]
    return ""


def _is_batting_header(row: List[str]) -> bool:
    headers = _header_map(row)
    return all(key in headers for key in ("player", "ab", "r", "h", "rbi"))


def _is_pitching_header(row: List[str]) -> bool:
    headers = _header_map(row)
    return all(key in headers for key in ("player", "ip", "h", "r", "er", "bb", "so"))


def _parse_batting_section(rows: List[List[str]], header_index: int) -> tuple[List[Dict[str, Any]], int]:
    batters: List[Dict[str, Any]] = []
    headers = _header_map(rows[header_index])
    player_index = headers["player"]
    position_index = headers.get("pos")
    index = header_index + 1
    while index < len(rows):
        row = rows[index]
        if _is_batting_header(row) or _is_pitching_header(row):
            break
        if not row:
            index += 1
            continue
        player_cell = row[player_index] if player_index < len(row) else ""
        position_cell = row[position_index] if position_index is not None and position_index < len(row) else ""
        if not player_cell:
            index += 1
            continue
        if player_cell.lower().startswith("totals") or position_cell.lower().startswith("totals"):
            index += 1
            break

        name, position = _split_sidearm_player_position(player_cell, position_cell)
        if name:
            batters.append(
                {
                    "number": "",
                    "name": name,
                    "position": position,
                    "at_bats": _safe_int(_row_value(row, headers, "ab")),
                    "runs": _safe_int(_row_value(row, headers, "r")),
                    "hits": _safe_int(_row_value(row, headers, "h")),
                    "rbi": _safe_int(_row_value(row, headers, "rbi")),
                    "walks": _safe_int(_row_value(row, headers, "bb")),
                    "strikeouts": _safe_int(_row_value(row, headers, "so", "k")),
                    "put_outs": _safe_int(_row_value(row, headers, "po")),
                    "assists": _safe_int(_row_value(row, headers, "a")),
                    "left_on_base": _safe_int(_row_value(row, headers, "lob")),
                    "doubles": _safe_int(_row_value(row, headers, "2b")),
                    "triples": _safe_int(_row_value(row, headers, "3b")),
                    "home_runs": _safe_int(_row_value(row, headers, "hr")),
                    "stolen_bases": _safe_int(_row_value(row, headers, "sb")),
                    "caught_stealing": _safe_int(_row_value(row, headers, "cs")),
                    "hit_by_pitch": _safe_int(_row_value(row, headers, "hbp")),
                    "sac_bunts": _safe_int(_row_value(row, headers, "sh")),
                    "sac_flies": _safe_int(_row_value(row, headers, "sf")),
                }
            )
        index += 1

    return batters, index


def _parse_batting_sections_from_table(table: Any) -> List[List[Dict[str, Any]]]:
    rows = _table_rows(table)
    sections: List[List[Dict[str, Any]]] = []
    index = 0
    while index < len(rows):
        row = rows[index]
        if not _is_batting_header(row):
            index += 1
            continue
        batters, index = _parse_batting_section(rows, index)
        if batters:
            sections.append(batters)
    return sections


def _is_composite_table(table: Any) -> bool:
    caption = table.find("caption")
    return bool(caption and "composite stats" in _clean_text(caption.get_text(" ", strip=True)).lower())


def _parse_pitcher_name_decision(player_cell: str) -> tuple[str, str, bool, bool, bool]:
    text = _clean_text(player_cell)
    decision = ""
    win = loss = save = False
    match = re.search(r"\((?P<content>[^)]*)\)\s*$", text)
    if match:
        content = match.group("content")
        text = _clean_text(text[: match.start()])
        if re.search(r"\bW\b", content):
            decision = "W"
            win = True
        elif re.search(r"\bL\b", content):
            decision = "L"
            loss = True
        elif re.search(r"\bS\b", content):
            decision = "S"
            save = True
    else:
        match = re.search(r"\s+(?P<decision>[WLS]),\s*[\w.-]+$", text)
        if match:
            decision = match.group("decision")
            text = _clean_text(text[: match.start()])
            win = decision == "W"
            loss = decision == "L"
            save = decision == "S"
    return _display_name(text), decision, win, loss, save


def _parse_pitching_section(rows: List[List[str]], header_index: int) -> tuple[List[Dict[str, Any]], int]:
    pitchers: List[Dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    headers = _header_map(rows[header_index])
    player_index = headers["player"]
    index = header_index + 1
    while index < len(rows):
        row = rows[index]
        if _is_batting_header(row) or _is_pitching_header(row):
            break
        player_cell = row[player_index] if player_index < len(row) else ""
        if not player_cell:
            index += 1
            continue
        if player_cell.lower().startswith("totals"):
            index += 1
            break

        name, decision, win, loss, save = _parse_pitcher_name_decision(player_cell)
        if name:
            pitcher = {
                "number": "",
                "name": name,
                "innings_pitched": _clean_text(_row_value(row, headers, "ip")),
                "hits": _safe_int(_row_value(row, headers, "h")),
                "runs": _safe_int(_row_value(row, headers, "r")),
                "earned_runs": _safe_int(_row_value(row, headers, "er")),
                "walks": _safe_int(_row_value(row, headers, "bb")),
                "strikeouts": _safe_int(_row_value(row, headers, "so", "k")),
                "home_runs": _safe_int(_row_value(row, headers, "hr")),
                "batters_faced": _safe_int(_row_value(row, headers, "bf")),
                "at_bats": _safe_int(_row_value(row, headers, "ab")),
                "pitches": _safe_int(_row_value(row, headers, "np")),
                "hit_by_pitch": _safe_int(_row_value(row, headers, "hbp")),
                "decision": decision,
                "win": win,
                "loss": loss,
                "save": save,
            }
            identity = (
                pitcher["name"],
                pitcher["innings_pitched"],
                pitcher["hits"],
                pitcher["runs"],
                pitcher["earned_runs"],
                pitcher["walks"],
                pitcher["strikeouts"],
            )
            if identity not in seen:
                pitchers.append(pitcher)
                seen.add(identity)
        index += 1

    return pitchers, index


def _parse_pitching_sections_from_table(table: Any) -> List[List[Dict[str, Any]]]:
    rows = _table_rows(table)
    sections: List[List[Dict[str, Any]]] = []
    index = 0
    while index < len(rows):
        row = rows[index]
        if not _is_pitching_header(row):
            index += 1
            continue
        pitchers, index = _parse_pitching_section(rows, index)
        if pitchers:
            sections.append(pitchers)
    return sections


def _parse_team_score(header: str) -> tuple[str, int | None]:
    text = _clean_text(header)
    match = re.match(r"^(?P<team>.+?)\s+(?P<score>\d+)(?:\s+\(|$)", text)
    if not match:
        return text, None
    return _clean_text(match.group("team")), int(match.group("score"))


def _team_cell_name(cell: Any) -> str:
    full = cell.select_one(".hide-on-large-down")
    if full:
        return _clean_text(full.get_text(" ", strip=True))
    text = _clean_text(cell.get_text(" ", strip=True))
    text = re.sub(r"^Winner\s+", "", text, flags=re.IGNORECASE)
    match = re.match(r"^[A-Z]{2,5}\s+(.+)$", text)
    if match:
        return _clean_text(match.group(1))
    return text


def _parse_line_score_table(soup: BeautifulSoup) -> tuple[Dict[str, Any], Dict[str, Any]]:
    metadata: Dict[str, Any] = {}
    line_score: Dict[str, Any] = {}
    for table in soup.find_all("table"):
        caption = table.find("caption")
        if not caption or "team score by innings" not in _clean_text(caption.get_text(" ", strip=True)).lower():
            continue
        header = [_header_key(cell.get_text(" ", strip=True)) for cell in table.find_all("th")]
        r_index = header.index("r") if "r" in header else None
        h_index = header.index("h") if "h" in header else None
        e_index = header.index("e") if "e" in header else None
        body_rows = table.find_all("tbody")[0].find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]
        teams: List[Dict[str, Any]] = []
        for tr in body_rows:
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            values = [_clean_text(cell.get_text(" ", strip=True)) for cell in cells]
            teams.append(
                {
                    "team": _team_cell_name(cells[0]),
                    "innings": [_safe_int(value) for value in values[1:r_index]] if r_index else [],
                    "runs": _safe_int_or_none(values[r_index]) if r_index is not None and r_index < len(values) else None,
                    "hits": _safe_int_or_none(values[h_index]) if h_index is not None and h_index < len(values) else None,
                    "errors": _safe_int_or_none(values[e_index]) if e_index is not None and e_index < len(values) else None,
                }
            )
        if len(teams) >= 2:
            metadata["away_team"] = teams[0]["team"]
            metadata["home_team"] = teams[1]["team"]
            if teams[0]["runs"] is not None:
                metadata["away_team_score"] = teams[0]["runs"]
            if teams[1]["runs"] is not None:
                metadata["home_team_score"] = teams[1]["runs"]
            line_score = {
                "away_innings": teams[0]["innings"],
                "home_innings": teams[1]["innings"],
            }
            break
    return metadata, line_score


def _parse_game_details(soup: BeautifulSoup) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    container = soup.select_one(".game-details, .sidearm-boxscore-game-details, [class*=game-details]")
    if not container:
        return details
    parts = [_clean_text(part) for part in container.get_text("\n", strip=True).splitlines()]
    parts = [part for part in parts if part and part.lower() != "game details"]
    labels = {"date", "start", "time", "attendance", "site", "umpires"}
    index = 0
    while index < len(parts) - 1:
        label = parts[index].lower()
        if label in labels:
            details[label] = parts[index + 1]
            index += 2
        else:
            index += 1

    metadata: Dict[str, Any] = {}
    if details.get("date"):
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%b %d, %Y"):
            try:
                parsed_date = datetime.strptime(details["date"], fmt)
                metadata["date"] = f"{parsed_date.month}/{parsed_date.day}/{parsed_date.year}"
                metadata["date_yyyymmdd"] = parsed_date.strftime("%Y%m%d")
                break
            except ValueError:
                continue
    if details.get("start"):
        metadata["start_time"] = details["start"]
    if details.get("time"):
        metadata["duration"] = details["time"]
    if details.get("attendance"):
        metadata["attendance"] = _safe_int(details["attendance"].replace(",", ""))
    if details.get("site"):
        site = details["site"]
        match = re.match(r"(?P<city>[^()]+)\((?P<venue>[^)]+)\)", site)
        if match:
            metadata["city"] = _clean_text(match.group("city"))
            metadata["venue"] = _clean_text(match.group("venue"))
        else:
            metadata["venue"] = site
    if details.get("umpires"):
        umpire_labels = {
            "Home Plate": "home_plate",
            "First": "first_base",
            "Second Base": "second_base",
            "Third Base": "third_base",
        }
        umpires: Dict[str, str] = {}
        pattern = r"(Home Plate|First|Second Base|Third Base):\s*(.*?)(?=\s+(?:Home Plate|First|Second Base|Third Base|Left Field|Right Field):|$)"
        for label, value in re.findall(pattern, details["umpires"]):
            value = _clean_text(value)
            if value:
                umpires[umpire_labels[label]] = value
        if umpires:
            metadata["umpires"] = umpires
    return metadata


def _pitch_count_from_description(description: str) -> Optional[str]:
    match = re.search(r"\((\d+-\d+[^)]*)\)", description)
    return _clean_text(match.group(1)) if match else None


def _rbi_from_description(description: str) -> int:
    match = re.search(r"(\d+)\s*RBI", description, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 1 if re.search(r"\bRBI\b", description, flags=re.IGNORECASE) else 0


def _parse_sidearm_play_by_play(soup: BeautifulSoup) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    innings: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
    section = soup.select_one("section#play-by-play") or soup.select_one("#play-by-play")
    if not section:
        return innings

    tables = section.select("#inning-all table.play-by-play")
    if not tables:
        tables = section.select("table.play-by-play")

    for table in tables:
        caption = table.find("caption")
        header = _clean_text(caption.get_text(" ", strip=True) if caption else "")
        match = re.search(
            r"\b(?P<half>Top|Bottom)\s+of\s+(?P<inning>\d+)(?:st|nd|rd|th)?\b",
            header,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        inning = int(match.group("inning"))
        half = "top" if match.group("half").lower() == "top" else "bottom"
        bucket = innings.setdefault(inning, {"top": [], "bottom": []})[half]

        body_rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]
        for row in body_rows:
            cells = row.find_all("td", recursive=False)
            if not cells:
                continue
            description = _clean_text(cells[0].get_text(" ", strip=True))
            if not description:
                continue
            event: Dict[str, Any] = {
                "description": description,
                "pitch_count": _pitch_count_from_description(description),
                "rbi": _rbi_from_description(description),
            }
            if len(cells) >= 3:
                event["away_score"] = _safe_int(cells[1].get_text(" ", strip=True))
                event["home_score"] = _safe_int(cells[2].get_text(" ", strip=True))
            bucket.append(event)

    return innings


def _parse_metadata(soup: BeautifulSoup) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {"source": "sidearm_html"}
    line_metadata, _line_score = _parse_line_score_table(soup)
    metadata.update(line_metadata)
    metadata.update(_parse_game_details(soup))

    text = soup.get_text("\n")
    matchup = re.search(r"\n\s*(?P<away>.+?)\s+at\s+(?P<home>.+?)\s*\n", text)
    if matchup and "away_team" not in metadata:
        metadata["away_team"] = _clean_text(matchup.group("away"))
        metadata["home_team"] = _clean_text(matchup.group("home"))

    date_venue = re.search(
        r"(?P<date>[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\s+at\s+"
        r"(?P<city>[^(\n]+)\((?P<venue>[^)]+)\)",
        text,
    )
    if date_venue and "date_yyyymmdd" not in metadata:
        parsed_date = datetime.strptime(_clean_text(date_venue.group("date")), "%b %d, %Y")
        metadata["date"] = f"{parsed_date.month}/{parsed_date.day}/{parsed_date.year}"
        metadata["date_yyyymmdd"] = parsed_date.strftime("%Y%m%d")
        metadata["city"] = _clean_text(date_venue.group("city"))
        metadata["venue"] = _clean_text(date_venue.group("venue"))

    headers = [_clean_text(header.get_text(" ", strip=True)) for header in soup.find_all("h4")]
    if len(headers) >= 2:
        away_team, away_score = _parse_team_score(headers[0])
        home_team, home_score = _parse_team_score(headers[1])
        metadata.setdefault("away_team", away_team)
        metadata.setdefault("home_team", home_team)
        if away_score is not None:
            metadata.setdefault("away_team_score", away_score)
        if home_score is not None:
            metadata.setdefault("home_team_score", home_score)

    return metadata


def parse_statcrew_html(html_content: str) -> Dict[str, Any]:
    """Parse a StatCrew/Sidearm HTML box score into the raw game contract."""
    soup = BeautifulSoup(html_content, "html.parser")
    all_batting_sections: List[List[Dict[str, Any]]] = []
    composite_batting_sections: List[List[Dict[str, Any]]] = []
    pitching_sections: List[List[Dict[str, Any]]] = []
    for table in soup.find_all("table"):
        batting_sections = _parse_batting_sections_from_table(table)
        if _is_composite_table(table):
            composite_batting_sections.extend(batting_sections)
        else:
            all_batting_sections.extend(batting_sections)
        pitching_sections.extend(_parse_pitching_sections_from_table(table))

    batting_sections = composite_batting_sections if len(composite_batting_sections) >= 2 else all_batting_sections
    metadata, line_score = _parse_line_score_table(soup)
    metadata.update(_parse_metadata(soup))

    box_score = {
        "away_batting": batting_sections[0] if len(batting_sections) >= 1 else [],
        "home_batting": batting_sections[1] if len(batting_sections) >= 2 else [],
        "away_pitching": pitching_sections[0] if len(pitching_sections) >= 1 else [],
        "home_pitching": pitching_sections[1] if len(pitching_sections) >= 2 else [],
    }
    if line_score:
        box_score["line_score"] = line_score

    return {
        "metadata": metadata,
        "box_score": {
            **box_score,
        },
        "game_notes": {},
        "play_by_play": _parse_sidearm_play_by_play(soup),
        "format": "sidearm_html",
    }
