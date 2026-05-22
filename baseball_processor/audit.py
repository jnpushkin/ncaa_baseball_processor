"""Data-integrity audits for cached inputs and generated website output."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .normalization import normalize_game
from .sources import _team_slug
from .utils.constants import BASE_DIR, CACHE_DIR, MILB_CACHE_DIR, NCAA_API_CACHE_DIR, PARTNER_CACHE_DIR
from .utils.helpers import (
    is_placeholder_player_name,
    is_single_initial_player_name,
    normalize_player_name,
    safe_int,
)


CacheEntry = Tuple[str, Path, Dict[str, Any]]


SOURCE_CACHE_GROUPS = [
    ("ncaa", CACHE_DIR, "*.json"),
    ("ncaa_api", NCAA_API_CACHE_DIR, "ncaa_api_*.json"),
    ("milb", MILB_CACHE_DIR, "milb_*.json"),
    ("partner", PARTNER_CACHE_DIR, "*.json"),
]


def _load_cache_entries() -> List[CacheEntry]:
    entries: List[CacheEntry] = []
    for source_group, cache_dir, pattern in SOURCE_CACHE_GROUPS:
        if not cache_dir.exists():
            continue
        for path in sorted(cache_dir.glob(pattern)):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    entries.append((source_group, path, json.load(f)))
            except Exception as exc:
                entries.append((source_group, path, {"__load_error__": str(exc)}))
    return entries


def _row_count(normalized_game: Dict[str, Any], section: str) -> int:
    rows_by_side = normalized_game.get(section, {}) or {}
    return sum(len(rows_by_side.get(side, []) or []) for side in ("away", "home"))


def audit_cached_games() -> tuple[dict[str, Any], list[str]]:
    """Audit cached raw games for normalizable metadata and stat-row retention."""
    issues: list[str] = []
    entries = _load_cache_entries()
    source_counts = Counter(entry[0] for entry in entries)
    normalized_ids: list[str] = []
    batting_rows = 0
    pitching_rows = 0

    expected_source_by_group = {
        "ncaa": {"ncaa"},
        "ncaa_api": {"ncaa_api"},
        "milb": {"milb"},
        "partner": {"partner"},
    }

    for source_group, path, game in entries:
        if "__load_error__" in game:
            issues.append(f"{path}: failed to load JSON ({game['__load_error__']})")
            continue

        try:
            normalized = normalize_game(game)
        except Exception as exc:
            issues.append(f"{path}: failed to normalize ({exc})")
            continue

        game_id = normalized.get("game_id")
        source = normalized.get("source")
        basic = normalized.get("basic_info", {}) or {}
        if not game_id:
            issues.append(f"{path}: missing normalized game_id")
        else:
            normalized_ids.append(str(game_id))
        if source not in expected_source_by_group[source_group]:
            issues.append(f"{path}: expected source {source_group!r}, got {source!r}")
        if not basic.get("date_yyyymmdd"):
            issues.append(f"{path}: missing normalized date_yyyymmdd")
        if not basic.get("away_team") or not basic.get("home_team"):
            issues.append(f"{path}: missing normalized teams")

        game_batting_rows = _row_count(normalized, "batting")
        game_pitching_rows = _row_count(normalized, "pitching")
        batting_rows += game_batting_rows
        pitching_rows += game_pitching_rows
        if game_batting_rows == 0 and game_pitching_rows == 0:
            issues.append(f"{path}: no normalized batting or pitching rows")

    id_counts = Counter(normalized_ids)
    duplicate_ids = sorted(game_id for game_id, count in id_counts.items() if count > 1)
    if duplicate_ids:
        issues.append(f"duplicate normalized game_id values: {', '.join(duplicate_ids[:10])}")

    summary = {
        "cache_files": len(entries),
        "source_counts": dict(source_counts),
        "normalized_games": len(normalized_ids),
        "unique_game_ids": len(id_counts),
        "batting_rows": batting_rows,
        "pitching_rows": pitching_rows,
    }
    return summary, issues


def _load_generated_site(web_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    site_path = web_dir / "src" / "data" / "site-data.json"
    if not site_path.exists():
        return None, [f"generated site data not found at {site_path}; skipping generated-output audit"]
    with open(site_path, "r", encoding="utf-8") as f:
        return json.load(f), []


def _detail_rows(detail: Dict[str, Any], key: str) -> Iterable[Dict[str, Any]]:
    box_score = detail.get("box_score", {}) or {}
    rows = box_score.get(key, []) or []
    return rows if isinstance(rows, list) else []


def _person_key(name: Any) -> str:
    normalized = normalize_player_name(str(name or ""))
    return re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()


def _rate_string(value: float) -> str:
    if value >= 1:
        return f"{value:.3f}"
    return f"{value:.3f}".lstrip("0") if value > 0 else ".000"


def _detail_batting_stat_issues(path: Path, detail: Dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("away_batting", "home_batting"):
        for index, row in enumerate(_detail_rows(detail, key)):
            player = row.get("name") or row.get("full_name") or f"{key}[{index}]"
            ab = safe_int(row.get("ab"))
            h = safe_int(row.get("h"))
            doubles = safe_int(row.get("doubles"))
            triples = safe_int(row.get("triples"))
            hr = safe_int(row.get("hr"))
            xbh = doubles + triples + hr
            if h > ab:
                issues.append(f"{path.name}:{key}[{index}] {player}: hits ({h}) exceed at-bats ({ab})")
            if xbh > h:
                issues.append(f"{path.name}:{key}[{index}] {player}: XBH ({xbh}) exceed hits ({h})")
            for stat in ("ab", "r", "h", "rbi", "bb", "k", "doubles", "triples", "hr", "sb"):
                if safe_int(row.get(stat)) < 0:
                    issues.append(f"{path.name}:{key}[{index}] {player}: negative {stat} value {row.get(stat)!r}")
    return issues


def _detail_pitching_stat_issues(path: Path, detail: Dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("away_pitching", "home_pitching"):
        for index, row in enumerate(_detail_rows(detail, key)):
            player = row.get("name") or row.get("full_name") or f"{key}[{index}]"
            r = safe_int(row.get("r"))
            er = safe_int(row.get("er"))
            if er > r:
                issues.append(f"{path.name}:{key}[{index}] {player}: earned runs ({er}) exceed runs ({r})")
            for stat in ("h", "r", "er", "bb", "k", "hr"):
                if safe_int(row.get(stat)) < 0:
                    issues.append(f"{path.name}:{key}[{index}] {player}: negative {stat} value {row.get(stat)!r}")
    return issues


def _find_detail_batter(detail: Dict[str, Any], player: Any) -> Dict[str, Any] | None:
    target = _person_key(player)
    if not target:
        return None
    for key in ("away_batting", "home_batting"):
        for row in _detail_rows(detail, key):
            if _person_key(row.get("name")) == target or _person_key(row.get("full_name")) == target:
                return row
    return None


def _milestone_detail_consistency_issues(
    site_data: Dict[str, Any],
    detail_payloads: Dict[str, Dict[str, Any]],
) -> list[str]:
    issues: list[str] = []
    milestone_specs = {
        "threeHrGames": {"HR": "hr", "H": "h", "RBI": "rbi"},
        "multiHrGames": {"HR": "hr", "H": "h", "RBI": "rbi"},
        "hrGames": {"HR": "hr", "H": "h", "RBI": "rbi"},
        "sixRbiGames": {"RBI": "rbi", "H": "h", "HR": "hr"},
        "fiveRbiGames": {"RBI": "rbi", "H": "h", "HR": "hr"},
        "fourRbiGames": {"RBI": "rbi", "H": "h", "HR": "hr"},
        "threeRbiGames": {"RBI": "rbi", "H": "h", "HR": "hr"},
        "hitForExtraBases": {"HR": "hr", "2B": "doubles", "3B": "triples"},
        "threeTotalBasesGames": {"HR": "hr", "H": "h", "RBI": "rbi"},
    }
    milestones = site_data.get("milestones", {}) or {}
    for milestone_key, stat_map in milestone_specs.items():
        rows = milestones.get(milestone_key, []) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            game_id = str(row.get("GameID") or "")
            player = row.get("Player")
            if not game_id or game_id not in detail_payloads:
                continue
            detail_row = _find_detail_batter(detail_payloads[game_id], player)
            if not detail_row:
                issues.append(f"{milestone_key}:{game_id}: could not find detail batting row for {player!r}")
                continue
            for milestone_stat, detail_stat in stat_map.items():
                if milestone_stat not in row:
                    continue
                milestone_value = safe_int(row.get(milestone_stat))
                detail_value = safe_int(detail_row.get(detail_stat))
                if milestone_value != detail_value:
                    issues.append(
                        f"{milestone_key}:{game_id}:{player}: {milestone_stat}={milestone_value} "
                        f"but detail {detail_stat}={detail_value}"
                    )
    return issues


def _unified_batter_rate_issues(site_data: Dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(site_data.get("unifiedBatters", []) or []):
        if not isinstance(row, dict):
            continue
        name = row.get("name") or f"unifiedBatters[{index}]"
        ab = safe_int(row.get("ab"))
        h = safe_int(row.get("h"))
        doubles = safe_int(row.get("doubles"))
        triples = safe_int(row.get("triples"))
        hr = safe_int(row.get("hr"))
        if ab > 0:
            expected_avg = _rate_string(h / ab)
            if row.get("avg") != expected_avg:
                issues.append(f"unifiedBatters[{index}] {name}: avg {row.get('avg')!r} should be {expected_avg}")
            singles = max(0, h - doubles - triples - hr)
            total_bases = singles + (2 * doubles) + (3 * triples) + (4 * hr)
            expected_slg = _rate_string(total_bases / ab)
            if row.get("slg") != expected_slg:
                issues.append(f"unifiedBatters[{index}] {name}: slg {row.get('slg')!r} should be {expected_slg}")
    return issues


def _missing_player_link_issues(site_data: Dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("unifiedBatters", "unifiedPitchers"):
        missing = [
            row
            for row in site_data.get(key, []) or []
            if isinstance(row, dict)
            and str(row.get("level") or "").upper() == "NCAA"
            and not row.get("bref_id")
            and not is_placeholder_player_name(row.get("name"))
        ]
        if missing:
            examples = [
                f"{row.get('name')} ({row.get('team')})"
                for row in missing[:8]
            ]
            issues.append(f"{key}: {len(missing)} NCAA player row(s) missing B-Ref/Chadwick link: {', '.join(examples)}")
    return issues


def _duplicate_player_game_issues(site_data: Dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("batterGames", "pitcherGames"):
        seen: Dict[tuple[str, str, str, str, str], int] = {}
        examples: list[str] = []
        for row in site_data.get(key, []) or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("level") or "").upper() != "NCAA":
                continue
            game_id = str(row.get("game_id") or "")
            name = str(row.get("Name") or row.get("name") or "").strip()
            team = str(row.get("team") or "").strip()
            identity = str(row.get("bref_id") or _person_key(name))
            if not game_id or not name or not team:
                continue
            row_key = (key, game_id, team, identity, name)
            seen[row_key] = seen.get(row_key, 0) + 1
            if seen[row_key] == 2 and len(examples) < 5:
                examples.append(f"{name} ({team}, {game_id})")
        duplicate_count = sum(count - 1 for count in seen.values() if count > 1)
        if duplicate_count:
            issues.append(f"{key}: {duplicate_count} duplicate NCAA player-game row(s): {', '.join(examples)}")
    return issues


def _golden_game_issues(site_data: Dict[str, Any], detail_payloads: Dict[str, Dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    game_id = "partner_pioneer_league_20260520_6ela"
    detail = detail_payloads.get(game_id)
    three_hr_rows = [
        row
        for row in (site_data.get("milestones", {}) or {}).get("threeHrGames", []) or []
        if isinstance(row, dict) and row.get("GameID") == game_id and row.get("Player") == "T.J. McKenzie"
    ]
    batter_rows = [
        row
        for row in site_data.get("unifiedBatters", []) or []
        if isinstance(row, dict) and row.get("name") == "T.J. McKenzie" and row.get("team") == "Oakland Ballers"
    ]

    if not detail and not three_hr_rows and not batter_rows:
        return issues
    if not three_hr_rows:
        issues.append("golden game McKenzie 2026-05-20: missing threeHrGames row")
    elif safe_int(three_hr_rows[0].get("HR")) != 3:
        issues.append(f"golden game McKenzie 2026-05-20: milestone HR is {three_hr_rows[0].get('HR')!r}, expected 3")

    if not detail:
        issues.append(f"golden game McKenzie 2026-05-20: missing detail file {game_id}.json")
    else:
        detail_row = _find_detail_batter(detail, "T.J. McKenzie")
        if not detail_row:
            issues.append("golden game McKenzie 2026-05-20: missing detail batting row")
        elif safe_int(detail_row.get("hr")) != 3:
            issues.append(f"golden game McKenzie 2026-05-20: detail hr is {detail_row.get('hr')!r}, expected 3")

    if not batter_rows:
        issues.append("golden game McKenzie 2026-05-20: missing unifiedBatters row")
    else:
        batter = batter_rows[0]
        expected = {"hr": 3, "rbi": 6, "slg": "4.000"}
        for key, value in expected.items():
            if batter.get(key) != value:
                issues.append(f"golden game McKenzie 2026-05-20: unified {key} is {batter.get(key)!r}, expected {value!r}")
    return issues


def _unified_game_log_issues(site_data: Dict[str, Any]) -> list[str]:
    issues: list[str] = []
    rows = site_data.get("unifiedGameLog", []) or []
    if not isinstance(rows, list):
        return ["unifiedGameLog is not a list"]

    blank_venues = [
        row
        for row in rows
        if isinstance(row, dict)
        and "venue" in row
        and not str(row.get("venue") or "").strip()
    ]
    if blank_venues:
        examples = [
            f"{row.get('date')} {row.get('away_team')} @ {row.get('home_team')} ({row.get('game_id')})"
            for row in blank_venues[:5]
        ]
        issues.append(f"{len(blank_venues)} unifiedGameLog row(s) missing venue: {', '.join(examples)}")

    grouped: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        date_key = str(row.get("date_sort") or "").strip()
        away = _team_slug(row.get("away_team"))
        home = _team_slug(row.get("home_team"))
        if not date_key or not away or not home:
            continue
        key = (
            date_key,
            away,
            home,
            safe_int(row.get("away_score")),
            safe_int(row.get("home_score")),
            str(row.get("level") or ""),
        )
        grouped.setdefault(key, []).append(row)

    duplicate_groups = [rows for rows in grouped.values() if len(rows) > 1]
    if duplicate_groups:
        examples = []
        for group in duplicate_groups[:5]:
            first = group[0]
            examples.append(
                f"{first.get('date')} {first.get('away_team')} @ {first.get('home_team')} "
                f"{first.get('away_score')}-{first.get('home_score')}"
            )
        issues.append(f"{len(duplicate_groups)} duplicate unifiedGameLog game key(s): {', '.join(examples)}")

    return issues


def audit_generated_website(
    web_dir: Path | None = None,
    *,
    expected_cache_games: int | None = None,
    expected_game_ids: set[str] | None = None,
    strict_cache_count: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Audit generated website data without requiring a specific architecture."""
    web_dir = web_dir or (BASE_DIR / "web")
    warnings: list[str] = []
    issues: list[str] = []
    site_data, load_warnings = _load_generated_site(web_dir)
    warnings.extend(load_warnings)
    if site_data is None:
        return {"generated": False}, issues, warnings

    games_dir = web_dir / "public" / "games"
    detail_files = sorted(games_dir.glob("*.json")) if games_dir.exists() else []
    unified_games = site_data.get("unifiedGameLog", []) or []
    linked_games = [game for game in unified_games if game.get("game_id")]
    linked_ids = [str(game["game_id"]) for game in linked_games]

    duplicate_linked_ids = sorted(game_id for game_id, count in Counter(linked_ids).items() if count > 1)
    if duplicate_linked_ids:
        issues.append(f"duplicate unifiedGameLog game_id values: {', '.join(duplicate_linked_ids[:10])}")

    detail_by_id = {path.stem: path for path in detail_files}
    missing_details = [game_id for game_id in linked_ids if game_id not in detail_by_id]
    if missing_details:
        issues.append(f"{len(missing_details)} linked game(s) missing detail JSON: {', '.join(missing_details[:10])}")

    if len(detail_files) != len(linked_ids):
        issues.append(f"detail file count {len(detail_files)} does not match linked game count {len(linked_ids)}")

    if strict_cache_count and expected_cache_games is not None:
        if len(linked_ids) != expected_cache_games:
            issues.append(f"linked game count {len(linked_ids)} does not match cached game count {expected_cache_games}")
        if len(detail_files) != expected_cache_games:
            issues.append(f"detail file count {len(detail_files)} does not match cached game count {expected_cache_games}")
    if strict_cache_count and expected_game_ids is not None:
        linked_id_set = set(linked_ids)
        detail_id_set = set(detail_by_id)
        missing_linked_ids = sorted(expected_game_ids - linked_id_set)
        extra_linked_ids = sorted(linked_id_set - expected_game_ids)
        missing_detail_ids = sorted(expected_game_ids - detail_id_set)
        extra_detail_ids = sorted(detail_id_set - expected_game_ids)
        if missing_linked_ids:
            issues.append(f"{len(missing_linked_ids)} expected cached game id(s) missing from unifiedGameLog: {', '.join(missing_linked_ids[:10])}")
        if extra_linked_ids:
            issues.append(f"{len(extra_linked_ids)} generated unifiedGameLog id(s) not found in cache audit: {', '.join(extra_linked_ids[:10])}")
        if missing_detail_ids:
            issues.append(f"{len(missing_detail_ids)} expected cached game id(s) missing detail JSON: {', '.join(missing_detail_ids[:10])}")
        if extra_detail_ids:
            issues.append(f"{len(extra_detail_ids)} generated detail id(s) not found in cache audit: {', '.join(extra_detail_ids[:10])}")

    data_quality_summary = (site_data.get("dataQuality") or {}).get("summary", {}) or {}
    source_merge_warnings = safe_int(data_quality_summary.get("sourceMergeWarnings"))
    if source_merge_warnings:
        review_games = safe_int(data_quality_summary.get("sourceMergeReviewGames"))
        warnings.append(
            f"source merge quality reported {source_merge_warnings} warning(s) "
            f"across {review_games} game(s)"
        )
    unmerged_source_candidates = safe_int(data_quality_summary.get("unmergedSourceCandidates"))
    if unmerged_source_candidates:
        warnings.append(
            f"source merge quality kept {unmerged_source_candidates} same-date/team candidate(s) unmerged"
        )

    required_batter_keys = {"ab", "r", "h", "rbi", "bb", "k"}
    required_pitcher_keys = {"ip", "h", "r", "er", "bb", "k", "np"}

    placeholder_tables: list[str] = []
    for key in ("unifiedBatters", "unifiedPitchers", "batterGames", "pitcherGames"):
        rows = site_data.get(key, []) or []
        if not isinstance(rows, list):
            continue
        count = sum(
            1
            for row in rows
            if isinstance(row, dict)
            and is_placeholder_player_name(row.get("name") or row.get("Name") or row.get("Player"))
        )
        if count:
            placeholder_tables.append(f"{key}={count}")
    if placeholder_tables:
        issues.append(f"placeholder player rows leaked into generated player tables: {', '.join(placeholder_tables)}")

    single_initial_tables: list[str] = []
    for key in ("unifiedBatters", "unifiedPitchers", "batterGames", "pitcherGames"):
        rows = site_data.get(key, []) or []
        if not isinstance(rows, list):
            continue
        count = sum(
            1
            for row in rows
            if isinstance(row, dict)
            and is_single_initial_player_name(row.get("name") or row.get("Name") or row.get("Player"))
        )
        if count:
            single_initial_tables.append(f"{key}={count}")
    if single_initial_tables:
        issues.append(
            "single-initial player names leaked into generated player tables: "
            + ", ".join(single_initial_tables)
        )

    placeholder_milestones = 0
    single_initial_milestones = 0
    for rows in (site_data.get("milestones", {}) or {}).values():
        if isinstance(rows, list):
            placeholder_milestones += sum(
                1
                for row in rows
                if isinstance(row, dict)
                and is_placeholder_player_name(row.get("Player") or row.get("name"))
            )
            single_initial_milestones += sum(
                1
                for row in rows
                if isinstance(row, dict)
                and is_single_initial_player_name(row.get("Player") or row.get("name"))
            )
    if placeholder_milestones:
        issues.append(f"{placeholder_milestones} placeholder player row(s) leaked into generated milestones")
    if single_initial_milestones:
        issues.append(f"{single_initial_milestones} single-initial player row(s) leaked into generated milestones")

    issues.extend(_unified_game_log_issues(site_data))

    detail_payloads: Dict[str, Dict[str, Any]] = {}
    for path in detail_files:
        try:
            detail = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"{path}: failed to load detail JSON ({exc})")
            continue
        detail_payloads[path.stem] = detail

        for key in ("away_batting", "home_batting"):
            for index, row in enumerate(_detail_rows(detail, key)):
                if is_placeholder_player_name(row.get("name") or row.get("full_name")):
                    issues.append(f"{path.name}:{key}[{index}] has placeholder player name")
                    break
                if (
                    is_single_initial_player_name(row.get("name"))
                    or is_single_initial_player_name(row.get("full_name"))
                ):
                    issues.append(f"{path.name}:{key}[{index}] has single-initial player name")
                    break
                missing = required_batter_keys - set(row)
                if missing:
                    issues.append(f"{path.name}:{key}[{index}] missing keys {sorted(missing)}")
                    break
        for key in ("away_pitching", "home_pitching"):
            for index, row in enumerate(_detail_rows(detail, key)):
                if is_placeholder_player_name(row.get("name") or row.get("full_name")):
                    issues.append(f"{path.name}:{key}[{index}] has placeholder player name")
                    break
                if (
                    is_single_initial_player_name(row.get("name"))
                    or is_single_initial_player_name(row.get("full_name"))
                ):
                    issues.append(f"{path.name}:{key}[{index}] has single-initial player name")
                    break
                missing = required_pitcher_keys - set(row)
                if missing:
                    issues.append(f"{path.name}:{key}[{index}] missing keys {sorted(missing)}")
                    break
        issues.extend(_detail_batting_stat_issues(path, detail))
        issues.extend(_detail_pitching_stat_issues(path, detail))

    stat_issues = (
        _milestone_detail_consistency_issues(site_data, detail_payloads)
        + _unified_batter_rate_issues(site_data)
        + _golden_game_issues(site_data, detail_payloads)
        + _missing_player_link_issues(site_data)
        + _duplicate_player_game_issues(site_data)
    )
    issues.extend(stat_issues)

    summary = {
        "generated": True,
        "unified_games": len(unified_games),
        "linked_games": len(linked_ids),
        "detail_files": len(detail_files),
        "missing_detail_files": len(missing_details),
        "stat_accuracy_errors": len(stat_issues),
        "source_merge_warnings": source_merge_warnings,
        "unmerged_source_candidates": unmerged_source_candidates,
    }
    return summary, issues, warnings


def run_integrity_audit(*, strict_generated_from_cache: bool = False) -> tuple[dict[str, Any], list[str], list[str]]:
    """Run all local data-preservation checks."""
    cache_summary, cache_issues = audit_cached_games()
    expected_game_ids = None
    if strict_generated_from_cache:
        from .website.generator import _build_raw_game_index

        raw_games = [
            game
            for _source_group, _path, game in _load_cache_entries()
            if "__load_error__" not in game
        ]
        index = _build_raw_game_index(raw_games)
        expected_game_ids = {record[0] for bucket in index.values() for record in bucket}
    site_summary, site_issues, warnings = audit_generated_website(
        expected_cache_games=cache_summary["normalized_games"],
        expected_game_ids=expected_game_ids,
        strict_cache_count=strict_generated_from_cache,
    )
    summary = {
        "cache": cache_summary,
        "website": site_summary,
    }
    return summary, cache_issues + site_issues, warnings
