"""Current-season MiLB metadata built from MLB Stats API plus local map overrides."""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from .constants import DATA_DIR, MILB_API_BASE, SPORT_LEVEL_MAP
from .milb_stadiums import LOGO_OVERRIDES, iter_milb_stadium_entries


ACTIVE_AFFILIATED_SPORT_IDS = (11, 12, 13, 14)
LEVEL_CODE_BY_NAME = {value: key for key, value in SPORT_LEVEL_MAP.items()}


def default_milb_season() -> int:
    """Return the season to use for current affiliated-team metadata."""
    return date.today().year


def generated_metadata_path(season: int | None = None, data_dir: Path | None = None) -> Path:
    """Return the generated current-season metadata path."""
    metadata_season = season or default_milb_season()
    return (data_dir or DATA_DIR) / f"milb_active_teams_{metadata_season}.json"


def _fetch_json(url: str, timeout: int = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ncaa-baseball-processor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def fetch_active_affiliated_teams(season: int | None = None, timeout: int = 10) -> dict[int, dict[str, Any]]:
    """Fetch current affiliated MiLB teams from the MLB Stats API."""
    metadata_season = season or default_milb_season()
    teams: dict[int, dict[str, Any]] = {}
    for sport_id in ACTIVE_AFFILIATED_SPORT_IDS:
        url = f"{MILB_API_BASE}/teams?sportId={sport_id}&season={metadata_season}&activeStatus=Y"
        payload = _fetch_json(url, timeout=timeout)
        for team in payload.get("teams", []) or []:
            team_id = team.get("id")
            if team_id is None:
                continue
            teams[int(team_id)] = {
                "team_id": int(team_id),
                "team": team.get("name", ""),
                "level": (team.get("sport") or {}).get("name", ""),
                "level_code": (team.get("sport") or {}).get("abbreviation", ""),
                "league": (team.get("league") or {}).get("name", ""),
                "venue": (team.get("venue") or {}).get("name", ""),
                "sport_id": sport_id,
            }
    return teams


def _static_location_overrides() -> dict[int, dict[str, Any]]:
    overrides: dict[int, dict[str, Any]] = {}
    for entry in iter_milb_stadium_entries(include_historic=True):
        try:
            team_id = int(entry["team_id"])
        except (TypeError, ValueError):
            continue
        overrides[team_id] = {
            "venue_key": entry["venue_key"],
            "venue": entry["venue"],
            "lat": entry["lat"],
            "lng": entry["lng"],
            "level_code": entry["level_code"],
            "league": entry["league"],
        }
    return overrides


def _team_logo(team_id: int) -> str:
    return LOGO_OVERRIDES.get(team_id, f"https://www.mlbstatic.com/team-logos/{team_id}.svg")


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (str(entry.get("level") or ""), str(entry.get("league") or ""), str(entry.get("team") or ""))


def static_active_affiliated_teams() -> dict[int, dict[str, Any]]:
    """Return active affiliated teams from the local static stadium map."""
    teams: dict[int, dict[str, Any]] = {}
    for entry in iter_milb_stadium_entries(include_historic=False):
        try:
            team_id = int(entry["team_id"])
        except (TypeError, ValueError):
            continue
        level = SPORT_LEVEL_MAP.get(entry["level_code"], entry["level_code"])
        teams[team_id] = {
            "team_id": team_id,
            "team": entry["team"],
            "level": level,
            "level_code": entry["level_code"],
            "league": entry["league"],
            "venue": entry["venue"],
            "venue_key": entry["venue_key"],
            "lat": entry["lat"],
            "lng": entry["lng"],
            "logo": _team_logo(team_id),
            "source": "static",
            "historic": False,
        }
    return teams


def build_active_affiliated_registry(
    live_teams: dict[int, dict[str, Any]],
    season: int | None = None,
) -> dict[str, Any]:
    """Merge live Stats API team identity with local coordinate/logo overrides."""
    metadata_season = season or default_milb_season()
    overrides = _static_location_overrides()
    registry_teams: list[dict[str, Any]] = []
    for team_id in sorted(live_teams):
        team = live_teams[team_id]
        override = overrides.get(team_id, {})
        level = team.get("level") or ""
        level_code = team.get("level_code") or override.get("level_code") or LEVEL_CODE_BY_NAME.get(level, level)
        venue = team.get("venue") or override.get("venue") or ""
        registry_teams.append({
            "team_id": team_id,
            "team": team.get("team", ""),
            "level": level,
            "level_code": level_code,
            "league": team.get("league", ""),
            "venue": venue,
            "venue_key": override.get("venue_key") or venue,
            "lat": override.get("lat"),
            "lng": override.get("lng"),
            "logo": _team_logo(team_id),
            "sport_id": team.get("sport_id"),
            "source": "statsapi",
            "historic": False,
        })

    registry_teams.sort(key=_entry_sort_key)
    return {
        "season": metadata_season,
        "source": "MLB Stats API",
        "sport_ids": list(ACTIVE_AFFILIATED_SPORT_IDS),
        "teams": registry_teams,
    }


def write_active_affiliated_registry(
    registry: dict[str, Any],
    path: Path | None = None,
) -> Path:
    """Write a generated current-season affiliated-team registry."""
    output_path = path or generated_metadata_path(int(registry["season"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, sort_keys=True)
        f.write("\n")
    return output_path


def load_active_affiliated_registry(
    season: int | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Load generated current-season affiliated-team metadata, if present."""
    registry_path = path or generated_metadata_path(season)
    if not registry_path.exists():
        return None
    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f)


def active_affiliated_registry_teams(
    season: int | None = None,
    prefer_generated: bool = True,
) -> tuple[dict[int, dict[str, Any]], str]:
    """Return active affiliated teams and the backing source label."""
    if prefer_generated:
        registry = load_active_affiliated_registry(season)
        if registry:
            teams = {
                int(team["team_id"]): team
                for team in registry.get("teams", [])
                if team.get("team_id") is not None
            }
            return teams, "generated"
    return static_active_affiliated_teams(), "static"


def iter_current_affiliated_team_entries(
    season: int | None = None,
    prefer_generated: bool = True,
):
    """Yield current affiliated teams from generated metadata, falling back to static data."""
    teams, _source = active_affiliated_registry_teams(season, prefer_generated=prefer_generated)
    for team in sorted(teams.values(), key=_entry_sort_key):
        yield team


def missing_location_teams(teams: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return active teams without usable map coordinates."""
    return [
        team
        for team in sorted(teams.values(), key=_entry_sort_key)
        if team.get("lat") in (None, "") or team.get("lng") in (None, "")
    ]

