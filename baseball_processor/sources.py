"""Source loading and cache handling for processor runs."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.constants import (
    CACHE_DIR,
    CONFERENCES,
    MILB_CACHE_DIR,
    MILB_GAME_IDS_FILE,
    NCAA_API_CACHE_DIR,
    NCAA_API_GAME_IDS_FILE,
    PARTNER_ARTIFACT_DIR,
    PARTNER_CACHE_DIR,
    PARTNER_GAME_IDS_FILE,
    PDF_DIR,
    TEAM_ALIASES,
)
from .utils.helpers import parse_innings_pitched, safe_int


@dataclass
class SourceGames:
    """Loaded game groups for one processor run."""

    ncaa_games: List[Dict[str, Any]]
    ncaa_api_games: List[Dict[str, Any]]
    milb_games: List[Dict[str, Any]]
    partner_games: List[Dict[str, Any]]

    @property
    def all_ncaa(self) -> List[Dict[str, Any]]:
        return self.ncaa_games + self.ncaa_api_games

    @property
    def pro_minor_games(self) -> List[Dict[str, Any]]:
        return self.milb_games + self.partner_games

    @property
    def all_games(self) -> List[Dict[str, Any]]:
        return self.all_ncaa + self.pro_minor_games

    @property
    def processing_ncaa(self) -> List[Dict[str, Any]]:
        return merge_duplicate_ncaa_games(self.all_ncaa)

    @property
    def processing_games(self) -> List[Dict[str, Any]]:
        return self.processing_ncaa + self.pro_minor_games

    def summary_parts(self) -> List[str]:
        parts = []
        if self.ncaa_games:
            parts.append(f"{len(self.ncaa_games)} NCAA (PDF)")
        if self.ncaa_api_games:
            parts.append(f"{len(self.ncaa_api_games)} NCAA (API)")
        if self.milb_games:
            parts.append(f"{len(self.milb_games)} MiLB")
        if self.partner_games:
            parts.append(f"{len(self.partner_games)} Partner")
        return parts


def _load_json_files(cache_dir: Path, pattern: str, label: str) -> List[Dict[str, Any]]:
    games = []
    if not cache_dir.exists():
        return games

    cache_files = list(cache_dir.glob(pattern))
    if cache_files:
        print(f"Loading {len(cache_files)} {label} games from cache...")

    for cache_file in cache_files:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                games.append(json.load(f))
        except Exception as e:
            print(f"  Error loading {cache_file.name}: {e}")
    return games


def _load_single_json_file(cache_file: Path, label: str) -> Optional[Dict[str, Any]]:
    """Load one cached game file, returning None on a cache miss."""
    if not cache_file.exists():
        print(f"Cache miss for {label}: {cache_file}")
        return None
    print(f"Loading {label} from cache: {cache_file.name}")
    with open(cache_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _print_game_summary(game_data: Dict[str, Any], league: str = "") -> None:
    meta = game_data["metadata"]
    prefix = f"[{league}] " if league else ""
    print(f"  {prefix}{meta['away_team']} @ {meta['home_team']}")
    print(f"  Score: {meta['away_team_score']} - {meta['home_team_score']}")


def _date_key(game_data: Dict[str, Any]) -> str:
    meta = game_data.get("metadata", {}) or {}
    if meta.get("date_yyyymmdd"):
        return str(meta["date_yyyymmdd"])
    date = str(meta.get("date", "") or "")
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return ""


def _source_label(game_data: Dict[str, Any]) -> str:
    meta = game_data.get("metadata", {}) or {}
    source = str(meta.get("source") or game_data.get("source") or "").lower()
    if source == "sidearm_html":
        return "ncaa"
    if source:
        return source
    if game_data.get("format") == "milb_api":
        return "milb"
    return "ncaa"


_KNOWN_TEAM_SLUGS: tuple[str, ...] = ()
_TEAM_SLUG_ALIASES = {
    "fdu": "fairleighdickinson",
    "loyolamarymount": "lmu",
    "cal": "california",
    "uconn": "connecticut",
}


def _compact_team_slug(value: Any) -> str:
    team = re.sub(r"\s*\(CA\)\s*$", "", str(value or "").strip(), flags=re.IGNORECASE)
    team = team.replace("&", "and")
    return "".join(c for c in team.lower() if c.isalnum())


def _expand_state_suffix(slug: str) -> str:
    if slug.endswith("st") and not slug.endswith("state"):
        return f"{slug[:-2]}state"
    return slug


def _canonical_team_slug(slug: str) -> str:
    return _TEAM_SLUG_ALIASES.get(slug, slug)


def _known_team_slugs() -> tuple[str, ...]:
    global _KNOWN_TEAM_SLUGS
    if _KNOWN_TEAM_SLUGS:
        return _KNOWN_TEAM_SLUGS

    team_names = set(TEAM_ALIASES) | set(TEAM_ALIASES.values())
    for teams in CONFERENCES.values():
        team_names.update(teams)

    slugs = {
        _canonical_team_slug(_expand_state_suffix(_compact_team_slug(team)))
        for team in team_names
        if team
    }
    _KNOWN_TEAM_SLUGS = tuple(sorted(slugs, key=len, reverse=True))
    return _KNOWN_TEAM_SLUGS


def _team_slug(value: Any) -> str:
    slug = _canonical_team_slug(_expand_state_suffix(_compact_team_slug(value)))
    if not slug:
        return ""
    for alias_slug, known_slug in _TEAM_SLUG_ALIASES.items():
        if alias_slug == "cal":
            continue
        if slug == alias_slug or slug.startswith(alias_slug):
            return known_slug
    for known_slug in _known_team_slugs():
        if slug == known_slug or slug.startswith(known_slug):
            return known_slug
    return slug


def _source_score(meta: Dict[str, Any], side: str) -> Any:
    for field in (f"{side}_team_score", f"{side}_score"):
        if meta.get(field) not in (None, ""):
            return meta.get(field)
    return None


def _score_key(game_data: Dict[str, Any]) -> Optional[tuple[int, int]]:
    meta = game_data.get("metadata", {}) or {}
    away_score = _source_score(meta, "away")
    home_score = _source_score(meta, "home")
    if away_score is None or home_score is None:
        return None
    return (safe_int(away_score), safe_int(home_score))


def _scores_compatible_for_merge(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    """Return True when scores agree or one source lacks enough score data."""
    left_score = _score_key(left)
    right_score = _score_key(right)
    if left_score is None or right_score is None:
        return True
    return left_score == right_score


def _duplicate_game_key(game_data: Dict[str, Any]) -> Optional[tuple]:
    meta = game_data.get("metadata", {}) or {}
    if _source_label(game_data) not in {"ncaa", "ncaa_api"}:
        return None
    date_key = _date_key(game_data)
    away = _team_slug(meta.get("away_team"))
    home = _team_slug(meta.get("home_team"))
    if not date_key or not away or not home:
        return None
    return (date_key, away, home)


def _adjacent_duplicate_key(game_data: Dict[str, Any]) -> Optional[tuple]:
    meta = game_data.get("metadata", {}) or {}
    if _source_label(game_data) not in {"ncaa", "ncaa_api"}:
        return None
    away = _team_slug(meta.get("away_team"))
    home = _team_slug(meta.get("home_team"))
    if not away or not home:
        return None
    score = _score_key(game_data)
    if score is None:
        return None
    away_score, home_score = score
    return (away, home, away_score, home_score)


def _date_diff_days(left: Dict[str, Any], right: Dict[str, Any]) -> Optional[int]:
    left_key = _date_key(left)
    right_key = _date_key(right)
    if not left_key or not right_key:
        return None
    try:
        left_date = datetime.strptime(left_key, "%Y%m%d")
        right_date = datetime.strptime(right_key, "%Y%m%d")
    except ValueError:
        return None
    return abs((left_date - right_date).days)


def _row_identity_key(row: Dict[str, Any]) -> str:
    number = str(row.get("number") or "").strip()
    if number:
        return f"number:{number}"
    name = str(row.get("full_name") or row.get("name") or "").strip().lower()
    return f"name:{name}"


def _row_last_name_key(row: Dict[str, Any]) -> str:
    name = str(row.get("full_name") or row.get("name") or "").strip().lower()
    if not name:
        return ""
    if "," in name:
        last = name.split(",", 1)[0]
    else:
        last = name.split()[-1]
    return re.sub(r"[^a-z]", "", last)


def _is_placeholder_name(value: Any) -> bool:
    return str(value or "").strip().lower() in {"", "unknown", "none", "null", "n/a", "-", "--"}


def _has_full_player_name(row: Dict[str, Any]) -> bool:
    name = str(row.get("full_name") or row.get("name") or "").strip()
    if _is_placeholder_name(name):
        return False

    parts = name.split()
    if len(parts) < 2:
        return False

    first_token = re.sub(r"[^A-Za-z.]", "", parts[0])
    first_letters = re.sub(r"[^A-Za-z]", "", first_token)
    if len(first_letters) <= 1:
        return False
    if first_token.endswith("."):
        return False
    if parts[0][:1].islower():
        return False

    return True


_SECTION_STAT_FIELDS = {
    "batting": (
        ("AB", ("AB", "ab", "at_bats")),
        ("R", ("R", "r", "runs")),
        ("H", ("H", "h", "hits")),
        ("RBI", ("RBI", "rbi")),
        ("BB", ("BB", "bb", "walks")),
        ("K", ("SO", "so", "k", "strikeouts")),
        ("2B", ("2B", "2b", "doubles")),
        ("3B", ("3B", "3b", "triples")),
        ("HR", ("HR", "hr", "home_runs")),
        ("SB", ("SB", "sb", "stolen_bases")),
    ),
    "pitching": (
        ("IP", ("IP", "ip", "innings_pitched")),
        ("H", ("H", "h", "hits")),
        ("R", ("R", "r", "runs")),
        ("ER", ("ER", "er", "earned_runs")),
        ("BB", ("BB", "bb", "walks")),
        ("K", ("SO", "so", "k", "strikeouts")),
        ("BF", ("batters_faced", "bf")),
    ),
}


def _has_source_batting_signal(row: Dict[str, Any]) -> bool:
    if str(row.get("position") or "").strip():
        return True
    for _field, aliases in _SECTION_STAT_FIELDS["batting"]:
        if (_compare_stat_value(_field, _first_stat_value(row, aliases)) or 0) > 0:
            return True
    return False


def _has_impossible_batting_strikeout(row: Dict[str, Any]) -> bool:
    stat_fields = dict(_SECTION_STAT_FIELDS["batting"])
    at_bats_raw = _first_stat_value(row, stat_fields["AB"])
    if at_bats_raw is None:
        return False
    at_bats = _compare_stat_value("AB", at_bats_raw) or 0
    strikeouts = _compare_stat_value("K", _first_stat_value(row, stat_fields["K"])) or 0
    return at_bats == 0 and strikeouts > 0


def _source_quality_rows(section: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if "batting" not in section:
        return rows
    return [
        row
        for row in rows
        if _has_source_batting_signal(row) and not _has_impossible_batting_strikeout(row)
    ]


def _first_stat_value(row: Dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _compare_stat_value(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field == "IP":
        return round(parse_innings_pitched(str(value).strip()), 3)
    return safe_int(value)


def _row_display_name(row: Dict[str, Any]) -> str:
    return str(row.get("full_name") or row.get("name") or "").strip() or "Unknown"


def _matched_row_pairs(
    primary_rows: List[Dict[str, Any]],
    api_rows: List[Dict[str, Any]],
) -> tuple[list[tuple[Dict[str, Any], Dict[str, Any], str]], list[Dict[str, Any]], list[Dict[str, Any]]]:
    primary_by_key: Dict[str, int] = {}
    for index, row in enumerate(primary_rows):
        key = _row_identity_key(row)
        if key not in {"number:", "name:"}:
            primary_by_key[key] = index

    primary_by_last: Dict[str, int] = {}
    primary_last_counts: Dict[str, int] = {}
    for index, row in enumerate(primary_rows):
        last = _row_last_name_key(row)
        if not last:
            continue
        primary_last_counts[last] = primary_last_counts.get(last, 0) + 1
        primary_by_last[last] = index

    pairs: list[tuple[Dict[str, Any], Dict[str, Any], str]] = []
    api_only: list[Dict[str, Any]] = []
    matched_primary_indexes: set[int] = set()

    for api_row in api_rows:
        row_key = _row_identity_key(api_row)
        primary_index = primary_by_key.get(row_key)
        match_method = "number" if primary_index is not None and row_key.startswith("number:") else "name"
        if primary_index is None:
            last = _row_last_name_key(api_row)
            if last and primary_last_counts.get(last) == 1:
                primary_index = primary_by_last[last]
                match_method = "unique_last_name"
        if primary_index is None:
            api_only.append(api_row)
            continue
        matched_primary_indexes.add(primary_index)
        pairs.append((primary_rows[primary_index], api_row, match_method))

    primary_only = [
        row
        for index, row in enumerate(primary_rows)
        if index not in matched_primary_indexes
    ]
    return pairs, primary_only, api_only


def _source_stat_disagreements(
    section: str,
    primary_rows: List[Dict[str, Any]],
    api_rows: List[Dict[str, Any]],
) -> tuple[Dict[str, int], list[Dict[str, Any]]]:
    category = "pitching" if "pitching" in section else "batting"
    raw_api_rows = api_rows
    primary_rows = _source_quality_rows(section, primary_rows)
    api_rows = _source_quality_rows(section, api_rows)
    pairs, primary_only, api_only = _matched_row_pairs(primary_rows, api_rows)
    coverage = {
        "pdf_rows": len(primary_rows),
        "api_rows": len(api_rows),
        "matched_rows": len(pairs),
        "pdf_only_rows": len(primary_only),
        "api_only_rows": len(api_only),
    }
    issues: list[Dict[str, Any]] = []
    unavailable_fields = _secondary_unavailable_fields(category, section, primary_rows, raw_api_rows)
    for field, primary_positive_rows in unavailable_fields.items():
        issues.append({
            "code": "secondary_stat_field_unavailable",
            "severity": "info",
            "section": section,
            "category": category,
            "field": field,
            "primary_source": "ncaa_pdf",
            "secondary_source": "ncaa_api",
            "primary_positive_rows": primary_positive_rows,
            "secondary_rows": len(api_rows),
        })

    for primary_row, api_row, match_method in pairs:
        player = _row_display_name(api_row if _has_full_player_name(api_row) else primary_row)
        for field, aliases in _SECTION_STAT_FIELDS[category]:
            if field in unavailable_fields:
                continue
            primary_raw = _first_stat_value(primary_row, aliases)
            api_raw = _first_stat_value(api_row, aliases)
            primary_value = _compare_stat_value(field, primary_raw)
            api_value = _compare_stat_value(field, api_raw)
            if primary_value is None or api_value is None or primary_value == api_value:
                continue
            issues.append({
                "code": "source_stat_disagreement",
                "severity": "warning",
                "section": section,
                "category": category,
                "player": player,
                "field": field,
                "primary_source": "ncaa_pdf",
                "secondary_source": "ncaa_api",
                "primary_value": primary_value,
                "secondary_value": api_value,
                "match_method": match_method,
            })

    for row in api_only:
        if _is_placeholder_name(row.get("full_name") or row.get("name")):
            continue
        issues.append({
            "code": "api_only_player_row",
            "severity": "info",
            "section": section,
            "category": category,
            "player": _row_display_name(row),
            "primary_source": "ncaa_pdf",
            "secondary_source": "ncaa_api",
        })

    return coverage, issues


def _secondary_unavailable_fields(
    category: str,
    section: str,
    primary_rows: List[Dict[str, Any]],
    api_rows: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Identify known NCAA API fields that are absent but defaulted to zero."""
    if not api_rows:
        return {}
    candidate_fields = {"K"} if category == "batting" else {"BB", "K"}
    unavailable: Dict[str, int] = {}
    stat_fields = dict(_SECTION_STAT_FIELDS[category])

    for field in candidate_fields:
        aliases = stat_fields[field]
        api_stat_rows = [
            row
            for row in api_rows
            if not _is_placeholder_name(row.get("full_name") or row.get("name"))
            and not ("batting" in section and _has_impossible_batting_strikeout(row))
        ]
        api_values = [
            _compare_stat_value(field, _first_stat_value(row, aliases))
            for row in api_stat_rows
        ]
        if any(value not in (None, 0) for value in api_values):
            continue

        primary_positive_rows = sum(
            1
            for row in primary_rows
            if (_compare_stat_value(field, _first_stat_value(row, aliases)) or 0) > 0
        )
        if primary_positive_rows:
            unavailable[field] = primary_positive_rows

    return unavailable


def _metadata_value(meta: Dict[str, Any], *fields: str) -> Any:
    for field in fields:
        if meta.get(field) not in (None, ""):
            return meta.get(field)
    return None


def _build_source_merge_quality(pdf_game: Dict[str, Any], api_game: Dict[str, Any]) -> Dict[str, Any]:
    pdf_meta = pdf_game.get("metadata", {}) or {}
    api_meta = api_game.get("metadata", {}) or {}
    pdf_box = pdf_game.get("box_score", {}) or {}
    api_box = api_game.get("box_score", {}) or {}
    issues: list[Dict[str, Any]] = []
    sections: Dict[str, Dict[str, int]] = {}

    for side in ("away", "home"):
        pdf_score = _metadata_value(pdf_meta, f"{side}_team_score", f"{side}_score")
        api_score = _metadata_value(api_meta, f"{side}_team_score", f"{side}_score")
        if pdf_score is not None and api_score is not None and safe_int(pdf_score) != safe_int(api_score):
            issues.append({
                "code": "source_score_disagreement",
                "severity": "warning",
                "field": f"{side}_score",
                "primary_source": "ncaa_pdf",
                "secondary_source": "ncaa_api",
                "primary_value": safe_int(pdf_score),
                "secondary_value": safe_int(api_score),
            })

    if _date_key(pdf_game) and _date_key(api_game) and _date_key(pdf_game) != _date_key(api_game):
        issues.append({
            "code": "source_date_disagreement",
            "severity": "info",
            "field": "date",
            "primary_source": "ncaa_pdf",
            "secondary_source": "ncaa_api",
            "primary_value": _date_key(pdf_game),
            "secondary_value": _date_key(api_game),
            "date_diff_days": _date_diff_days(pdf_game, api_game),
        })

    for section in ("away_batting", "home_batting", "away_pitching", "home_pitching"):
        coverage, section_issues = _source_stat_disagreements(
            section,
            pdf_box.get(section, []) or [],
            api_box.get(section, []) or [],
        )
        sections[section] = coverage
        issues.extend(section_issues)

    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    info_count = sum(1 for issue in issues if issue.get("severity") == "info")
    return {
        "sources": ["ncaa_pdf", "ncaa_api"],
        "primary_source": "ncaa_pdf",
        "secondary_source": "ncaa_api",
        "stats_source": "ncaa_pdf",
        "identity_source": "ncaa_api",
        "api_game_id": api_meta.get("game_id") or api_meta.get("game_pk"),
        "confidence": "review" if warning_count else "high",
        "warning_count": warning_count,
        "info_count": info_count,
        "issue_count": len(issues),
        "sections": sections,
        "issues": issues,
    }


def _source_candidate_quality(
    pdf_game: Dict[str, Any],
    api_game: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    pdf_meta = pdf_game.get("metadata", {}) or {}
    api_meta = api_game.get("metadata", {}) or {}
    return {
        "sources": ["ncaa_pdf", "ncaa_api"],
        "confidence": "not_merged",
        "reason": reason,
        "pdf_score": _score_key(pdf_game),
        "api_score": _score_key(api_game),
        "pdf_date": _date_key(pdf_game),
        "api_date": _date_key(api_game),
        "pdf_away_team": pdf_meta.get("away_team"),
        "pdf_home_team": pdf_meta.get("home_team"),
        "api_game_id": api_meta.get("game_id") or api_meta.get("game_pk"),
    }


def _copy_inferred_venue(api_game: Dict[str, Any], pdf_game: Dict[str, Any]) -> Dict[str, Any]:
    """Copy venue metadata to an unmerged API game when the same matchup anchors it."""
    updated = deepcopy(api_game)
    api_meta = updated.setdefault("metadata", {})
    pdf_meta = pdf_game.get("metadata", {}) or {}
    for field in ("venue", "stadium", "city"):
        if not api_meta.get(field) and pdf_meta.get(field):
            api_meta[field] = pdf_meta[field]
            api_meta[f"{field}_source"] = "same_date_pdf_matchup"
    return updated


def _with_unmerged_source_candidate_quality(
    game: Dict[str, Any],
    pdf_game: Dict[str, Any],
    api_game: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    updated = deepcopy(game)
    updated.setdefault("data_quality", {})["source_candidate"] = _source_candidate_quality(
        pdf_game,
        api_game,
        reason,
    )
    return updated


def _merge_box_section(primary_rows: List[Dict[str, Any]], api_rows: List[Dict[str, Any]], section: str) -> List[Dict[str, Any]]:
    """Merge API identity/side repairs with richer PDF stat rows."""
    if not api_rows:
        return deepcopy(primary_rows)

    primary_by_key = {
        _row_identity_key(row): row
        for row in primary_rows
        if _row_identity_key(row) not in {"number:", "name:"}
    }
    primary_by_last = {}
    primary_last_counts: Dict[str, int] = {}
    for row in primary_rows:
        last = _row_last_name_key(row)
        if not last:
            continue
        primary_last_counts[last] = primary_last_counts.get(last, 0) + 1
        primary_by_last[last] = row

    merged_rows = []
    matched_keys = set()
    for api_row in api_rows:
        row_key = _row_identity_key(api_row)
        primary_row = primary_by_key.get(row_key)
        if not primary_row:
            last = _row_last_name_key(api_row)
            if last and primary_last_counts.get(last) == 1:
                primary_row = primary_by_last[last]
                row_key = _row_identity_key(primary_row)
        if primary_row:
            row = deepcopy(primary_row)
            matched_keys.add(row_key)
            if _has_full_player_name(api_row):
                row["name"] = api_row.get("name") or api_row.get("full_name")
                row["full_name"] = api_row.get("full_name") or api_row.get("name")
            for field in ("player_id", "register_id", "decision", "win", "loss", "save"):
                if api_row.get(field) not in (None, ""):
                    row[field] = api_row[field]
            for field in ("bref_id", "match_confidence", "position"):
                if not row.get(field) and api_row.get(field):
                    row[field] = api_row[field]
        else:
            if primary_rows and _is_placeholder_name(api_row.get("full_name") or api_row.get("name")):
                continue
            row = deepcopy(api_row)
        merged_rows.append(row)

    for primary_row in primary_rows:
        row_key = _row_identity_key(primary_row)
        if row_key in matched_keys:
            continue
        name = str(primary_row.get("full_name") or primary_row.get("name") or "").strip()
        is_weak_pitcher_row = (
            "pitching" in section
            and not primary_row.get("bref_id")
            and not primary_row.get("full_name")
            and len(name.split()) < 2
        )
        if not is_weak_pitcher_row:
            merged_rows.append(deepcopy(primary_row))
    return merged_rows


def _merge_ncaa_pdf_api_duplicate(pdf_game: Dict[str, Any], api_game: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the richer PDF shell, but use the cleaner NCAA API box score."""
    merged = deepcopy(pdf_game)
    merged_meta = merged.setdefault("metadata", {})
    api_meta = api_game.get("metadata", {}) or {}
    merged.setdefault("data_quality", {})["source_merge"] = _build_source_merge_quality(pdf_game, api_game)
    merged_meta["merged_sources"] = ["ncaa", "ncaa_api"]
    if api_meta.get("game_id"):
        merged_meta["ncaa_api_game_id"] = api_meta["game_id"]
    if _date_diff_days(pdf_game, api_game) == 1:
        # Suspended tournament games may use the start date in PDF box scores and
        # the resumption/final date in the NCAA API. Prefer the official API date
        # while keeping the PDF venue and richer shell data.
        for field in ("date", "date_yyyymmdd"):
            if api_meta.get(field):
                merged_meta[field] = api_meta[field]

    primary_box = merged.setdefault("box_score", {})
    api_box = api_game.get("box_score", {}) or {}
    for section in ("away_batting", "home_batting", "away_pitching", "home_pitching"):
        primary_box[section] = _merge_box_section(
            primary_box.get(section, []) or [],
            api_box.get(section, []) or [],
            section,
        )

    return merged


def _merge_exact_date_group(group: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    pdf_games = [game for game in group if _source_label(game) == "ncaa"]
    api_games = [game for game in group if _source_label(game) == "ncaa_api"]
    if not pdf_games or not api_games:
        return group, 0

    result: List[Dict[str, Any]] = []
    used_api_indexes: set[int] = set()
    merged_count = 0

    for pdf_game in pdf_games:
        api_match_index = None
        for index, api_game in enumerate(api_games):
            if index in used_api_indexes:
                continue
            if _scores_compatible_for_merge(pdf_game, api_game):
                api_match_index = index
                break

        if api_match_index is None:
            result.append(pdf_game)
            continue

        used_api_indexes.add(api_match_index)
        result.append(_merge_ncaa_pdf_api_duplicate(pdf_game, api_games[api_match_index]))
        merged_count += 1

    anchor_pdf = pdf_games[0]
    for index, api_game in enumerate(api_games):
        if index in used_api_indexes:
            continue
        api_with_venue = _copy_inferred_venue(api_game, anchor_pdf)
        api_with_quality = _with_unmerged_source_candidate_quality(
            api_with_venue,
            anchor_pdf,
            api_game,
            "score_mismatch",
        )
        result.append(api_with_quality)

    result.extend(
        game
        for game in group
        if _source_label(game) not in {"ncaa", "ncaa_api"}
    )
    return result, merged_count


def merge_duplicate_ncaa_games(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge NCAA PDF/API duplicates so stats are not double-counted.

    The raw source lists stay untouched. For processing, matching PDF/API games
    are represented once, using the PDF game shell and NCAA API player identities.
    A second pass catches suspended/postponed tournament games whose official API
    date differs from the PDF start date by one day, but only when final score
    also matches.
    """
    grouped: Dict[tuple, List[Dict[str, Any]]] = {}
    initial_passthrough: List[Dict[str, Any]] = []
    for game in games:
        key = _duplicate_game_key(game)
        if key is None:
            initial_passthrough.append(game)
        else:
            grouped.setdefault(key, []).append(game)

    merged_games: List[Dict[str, Any]] = []
    merged_count = 0
    for group in grouped.values():
        group_games, group_merged_count = _merge_exact_date_group(group)
        merged_games.extend(group_games)
        merged_count += group_merged_count

    adjacent_grouped: Dict[tuple, List[Dict[str, Any]]] = {}
    adjacent_passthrough: List[Dict[str, Any]] = []
    for game in merged_games + initial_passthrough:
        key = _adjacent_duplicate_key(game)
        if key is None:
            adjacent_passthrough.append(game)
        else:
            adjacent_grouped.setdefault(key, []).append(game)

    merged_games = []
    for group in adjacent_grouped.values():
        pdf_games = [game for game in group if _source_label(game) == "ncaa"]
        api_games = [game for game in group if _source_label(game) == "ncaa_api"]
        if (
            len(group) == 2
            and pdf_games
            and api_games
            and _date_diff_days(pdf_games[0], api_games[0]) == 1
        ):
            merged_games.append(_merge_ncaa_pdf_api_duplicate(pdf_games[0], api_games[0]))
            merged_count += 1
        else:
            merged_games.extend(group)

    if merged_count:
        print(f"Merged {merged_count} duplicate NCAA PDF/API game(s) for processing.")
    return merged_games + adjacent_passthrough


def _filter_games_by_date_range(
    games: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
) -> List[Dict[str, Any]]:
    start_key = start.strftime("%Y%m%d")
    end_key = end.strftime("%Y%m%d")
    return [game for game in games if start_key <= _date_key(game) <= end_key]


def process_pdf_file(
    file_path: str,
    matcher: Optional[Any] = None,
    use_cache: bool = True,
    index: Optional[int] = None,
    total: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Process a single NCAA PDF file with cache support."""
    from ncaab_parser import parse_ncaab_pdf
    from name_matcher import enrich_game_data

    filename = os.path.basename(file_path)
    filename_no_ext = os.path.splitext(filename)[0]
    safe_filename = re.sub(r"[^\w\-_]", "_", filename_no_ext)
    cache_path = CACHE_DIR / f"{safe_filename}.json"

    if index is not None and total is not None:
        print(f"[{index}/{total}] Processing: {filename}")
    else:
        print(f"Processing: {filename}")

    if use_cache and cache_path.exists():
        pdf_mtime = os.path.getmtime(file_path)
        cache_mtime = os.path.getmtime(cache_path)
        if pdf_mtime <= cache_mtime:
            print("  Using cached data")
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        print("  Cache outdated, re-parsing...")

    try:
        game_data = parse_ncaab_pdf(file_path)
        meta = game_data.get("metadata", {})
        print(f"  {meta.get('away_team', '?')} vs {meta.get('home_team', '?')}")
        print(f"  Score: {meta.get('away_team_score', '?')} - {meta.get('home_team_score', '?')}")

        if matcher:
            game_data = enrich_game_data(game_data, matcher)

        if use_cache:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(game_data, f, indent=2)
            print("  Cached")

        return game_data
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def process_pdf_games(input_path: str = None, use_cache: bool = True, roster_dir: str = None) -> List[Dict[str, Any]]:
    """Process NCAA PDFs from a file or directory."""
    from name_matcher import NameMatcher

    matcher = None
    if roster_dir and Path(roster_dir).exists():
        matcher = NameMatcher()
        count = matcher.load_rosters_from_dir(roster_dir)
        print(f"Loaded {count} rosters for player matching")

    games = []
    errors = []
    input_path = input_path or str(PDF_DIR)

    if os.path.isfile(input_path):
        if input_path.endswith(".pdf"):
            game = process_pdf_file(input_path, matcher, use_cache)
            if game:
                games.append(game)
            else:
                errors.append((os.path.basename(input_path), "Failed to parse"))
    elif os.path.isdir(input_path):
        pdf_files = list(Path(input_path).glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")
        for idx, pdf_file in enumerate(pdf_files, 1):
            game = process_pdf_file(str(pdf_file), matcher, use_cache, idx, len(pdf_files))
            if game:
                games.append(game)
            else:
                errors.append((pdf_file.name, "Failed to parse"))
    else:
        print(f"Invalid path: {input_path}")

    print(f"\nSuccessfully processed {len(games)} games")
    if errors:
        print(f"\nFailed to process {len(errors)}/{len(games) + len(errors)} PDFs:")
        for filename, error in errors:
            print(f"  - {filename}: {error}")
    return games


def load_ncaa_from_cache() -> List[Dict[str, Any]]:
    return _load_json_files(CACHE_DIR, "*.json", "NCAA")


def load_ncaa_api_from_cache() -> List[Dict[str, Any]]:
    return _load_json_files(NCAA_API_CACHE_DIR, "ncaa_api_*.json", "NCAA API")


def load_milb_from_cache() -> List[Dict[str, Any]]:
    return _load_json_files(MILB_CACHE_DIR, "milb_*.json", "MiLB")


def load_partner_from_cache() -> List[Dict[str, Any]]:
    return _load_json_files(PARTNER_CACHE_DIR, "*.json", "Partner League")


def load_source_games(args) -> SourceGames:
    """Load all requested source groups according to parsed CLI args."""
    from parsers.milb_api import process_all_milb_games, process_milb_game
    from parsers.ncaa_api import process_all_ncaa_api_games, process_ncaa_api_date_range, process_ncaa_api_game
    from parsers.partner_leagues import (
        list_pioneer_games_for_date,
        process_all_partner_games,
        process_partner_game,
    )

    ncaa_games: List[Dict[str, Any]] = []
    ncaa_api_games: List[Dict[str, Any]] = []
    milb_games: List[Dict[str, Any]] = []
    partner_games: List[Dict[str, Any]] = []

    explicit_ncaa_api = bool(
        args.ncaa_api_game
        or args.ncaa_api_date
        or args.ncaa_api_date_range
        or args.ncaa_api_only
    )
    explicit_milb = bool(args.milb_game or args.milb_only)
    explicit_partner = bool(args.partner_game or args.pioneer_by_date)
    explicit_mode = explicit_ncaa_api or explicit_milb or explicit_partner

    if args.ncaa_api_game:
        print(f"\nProcessing single NCAA API game: {args.ncaa_api_game}")
        NCAA_API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if args.from_cache_only:
            game_data = _load_single_json_file(
                NCAA_API_CACHE_DIR / f"ncaa_api_{args.ncaa_api_game}.json",
                "NCAA API game",
            )
        else:
            game_data = process_ncaa_api_game(args.ncaa_api_game, NCAA_API_CACHE_DIR)
        if game_data:
            ncaa_api_games.append(game_data)
            _print_game_summary(game_data)

    if args.ncaa_api_date or args.ncaa_api_date_range:
        NCAA_API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if args.ncaa_api_date:
            dt = datetime.strptime(args.ncaa_api_date, "%Y-%m-%d")
            if args.from_cache_only:
                print(f"\nLoading NCAA API cache entries for {args.ncaa_api_date}...")
                ncaa_api_games.extend(_filter_games_by_date_range(load_ncaa_api_from_cache(), dt, dt))
            else:
                print(f"\nFetching NCAA API games for {args.ncaa_api_date}...")
                ncaa_api_games.extend(process_ncaa_api_date_range(dt, dt, NCAA_API_CACHE_DIR))
        if args.ncaa_api_date_range:
            start = datetime.strptime(args.ncaa_api_date_range[0], "%Y-%m-%d")
            end = datetime.strptime(args.ncaa_api_date_range[1], "%Y-%m-%d")
            if args.from_cache_only:
                print(f"\nLoading NCAA API cache entries for {args.ncaa_api_date_range[0]} to {args.ncaa_api_date_range[1]}...")
                ncaa_api_games.extend(_filter_games_by_date_range(load_ncaa_api_from_cache(), start, end))
            else:
                print(f"\nFetching NCAA API games for {args.ncaa_api_date_range[0]} to {args.ncaa_api_date_range[1]}...")
                ncaa_api_games.extend(process_ncaa_api_date_range(start, end, NCAA_API_CACHE_DIR))

    if args.milb_game:
        print(f"\nProcessing single MiLB game: {args.milb_game}")
        MILB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if args.from_cache_only:
            game_data = _load_single_json_file(
                MILB_CACHE_DIR / f"milb_{args.milb_game}.json",
                "MiLB game",
            )
        else:
            game_data = process_milb_game(args.milb_game, MILB_CACHE_DIR)
        if game_data:
            milb_games.append(game_data)
            _print_game_summary(game_data)

    if args.pioneer_by_date:
        if args.from_cache_only:
            print("Cannot use --pioneer-by-date with --from-cache-only; schedule lookup requires network.")
            return SourceGames(ncaa_games, ncaa_api_games, milb_games, partner_games)
        try:
            games = list_pioneer_games_for_date(args.pioneer_by_date)
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return SourceGames(ncaa_games, ncaa_api_games, milb_games, partner_games)
        if not games:
            print(f"No Pioneer League games found on {args.pioneer_by_date}")
            return SourceGames(ncaa_games, ncaa_api_games, milb_games, partner_games)
        print(f"\nPioneer League games on {args.pioneer_by_date}:")
        for i, g in enumerate(games, 1):
            print(f"  {i}. {g['away_team']} @ {g['home_team']}  [{g['game_code']}]")
        try:
            choice = input(f"\nPick game (1-{len(games)}): ").strip()
            picked = games[int(choice) - 1]
        except (ValueError, IndexError, EOFError, KeyboardInterrupt):
            print("Cancelled.")
            return SourceGames(ncaa_games, ncaa_api_games, milb_games, partner_games)
        game_id_line = f"pioneer:{picked['game_code']}  # {picked['away_team']} @ {picked['home_team']}, {args.pioneer_by_date}"
        existing = PARTNER_GAME_IDS_FILE.read_text() if PARTNER_GAME_IDS_FILE.exists() else ""
        if picked["game_code"] not in existing:
            with open(PARTNER_GAME_IDS_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n{game_id_line}\n")
            print(f"Added to {PARTNER_GAME_IDS_FILE}")
        else:
            print(f"Already in {PARTNER_GAME_IDS_FILE}")
        args.partner_game = f"pioneer:{picked['game_code']}"

    if args.partner_game:
        if ":" not in args.partner_game:
            print("Error: --partner-game must be in format league:game_id")
            return SourceGames(ncaa_games, ncaa_api_games, milb_games, partner_games)
        league, game_id = args.partner_game.split(":", 1)
        print(f"\nProcessing single Partner League game: {league}:{game_id}")
        PARTNER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if args.from_cache_only:
            game_data = _load_single_json_file(
                PARTNER_CACHE_DIR / f"{league}_{game_id}.json",
                "Partner League game",
            )
        else:
            game_data = process_partner_game(
                game_id,
                league,
                PARTNER_CACHE_DIR,
                download_artifacts=getattr(args, "download_pioneer_pdfs", False),
                artifact_dir=Path(getattr(args, "pioneer_artifact_dir", PARTNER_ARTIFACT_DIR)),
            )
        if game_data:
            partner_games.append(game_data)
            meta = game_data["metadata"]
            league_name = meta.get("league", {}).get("home", league)
            _print_game_summary(game_data, league_name)

    if not explicit_mode:
        if args.from_db:
            from .db.database import Database
            db = Database()
            ncaa_games = db.get_all_games("ncaa")
            print(f"Loaded {len(ncaa_games)} NCAA games from database")
        elif args.from_cache_only:
            ncaa_games = load_ncaa_from_cache()
        else:
            roster_dir = args.roster_dir if Path(args.roster_dir).exists() else None
            ncaa_games = process_pdf_games(args.input_path, not args.no_cache, roster_dir)

    if (
        (not explicit_mode or args.ncaa_api_only)
        and not args.no_ncaa_api
        and not args.ncaa_api_game
        and not args.ncaa_api_date
        and not args.ncaa_api_date_range
    ):
        if args.from_db:
            from .db.database import Database
            db = Database()
            ncaa_api_games.extend(db.get_all_games("ncaa_api"))
            if ncaa_api_games:
                print(f"Loaded {len(ncaa_api_games)} NCAA API games from database")
        elif args.from_cache_only:
            ncaa_api_games.extend(load_ncaa_api_from_cache())
        else:
            if NCAA_API_GAME_IDS_FILE.exists():
                NCAA_API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                ncaa_api_games.extend(process_all_ncaa_api_games(NCAA_API_GAME_IDS_FILE, NCAA_API_CACHE_DIR))

    if (
        (not explicit_mode or args.milb_only)
        and not args.no_milb
        and not args.milb_game
        and (args.include_milb or args.milb_only)
    ):
        if args.from_db:
            from .db.database import Database
            db = Database()
            milb_games = db.get_all_games("milb")
            print(f"Loaded {len(milb_games)} MiLB games from database")
        elif args.from_cache_only:
            milb_games = load_milb_from_cache()
        elif MILB_GAME_IDS_FILE.exists():
            MILB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            milb_games = process_all_milb_games(MILB_GAME_IDS_FILE, MILB_CACHE_DIR)
        else:
            print("No MiLB game_ids.txt file found")

    if not explicit_mode and args.include_partner and not args.no_partner:
        if args.from_db:
            from .db.database import Database
            db = Database()
            partner_games = db.get_all_games("partner")
            print(f"Loaded {len(partner_games)} Partner games from database")
        elif args.from_cache_only:
            partner_games = load_partner_from_cache()
        elif PARTNER_GAME_IDS_FILE.exists():
            PARTNER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            partner_games = process_all_partner_games(
                PARTNER_GAME_IDS_FILE,
                PARTNER_CACHE_DIR,
                download_artifacts=getattr(args, "download_pioneer_pdfs", False),
                artifact_dir=Path(getattr(args, "pioneer_artifact_dir", PARTNER_ARTIFACT_DIR)),
            )
        else:
            print("No partner league game_ids.txt file found")

    return SourceGames(ncaa_games, ncaa_api_games, milb_games, partner_games)
