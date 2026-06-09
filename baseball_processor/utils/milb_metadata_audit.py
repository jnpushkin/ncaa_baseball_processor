"""Freshness checks for generated/current MiLB team/stadium metadata."""

from __future__ import annotations

from typing import Any

from .milb_metadata import missing_location_teams


def _field_mismatches(static: dict[str, Any], live: dict[str, Any]) -> dict[str, dict[str, str]]:
    mismatches: dict[str, dict[str, str]] = {}
    for field in ("team", "level", "league", "venue"):
        static_value = str(static.get(field) or "")
        live_value = str(live.get(field) or "")
        if static_value != live_value:
            mismatches[field] = {"static": static_value, "live": live_value}
    return mismatches


def compare_milb_metadata(
    registry_teams: dict[int, dict[str, Any]],
    live_teams: dict[int, dict[str, Any]],
    registry_source: str = "registry",
) -> dict[str, Any]:
    """Compare generated/static affiliated-team metadata to live Stats API data."""
    registry_ids = set(registry_teams)
    live_ids = set(live_teams)

    missing = [live_teams[team_id] for team_id in sorted(live_ids - registry_ids)]
    stale = [registry_teams[team_id] for team_id in sorted(registry_ids - live_ids)]
    mismatches = []
    for team_id in sorted(registry_ids & live_ids):
        fields = _field_mismatches(registry_teams[team_id], live_teams[team_id])
        if fields:
            mismatches.append({
                "team_id": team_id,
                "static": registry_teams[team_id],
                "live": live_teams[team_id],
                "fields": fields,
            })

    return {
        "registry_source": registry_source,
        "registry_count": len(registry_teams),
        "live_count": len(live_teams),
        "missing": missing,
        "stale": stale,
        "mismatches": mismatches,
        "missing_locations": missing_location_teams(registry_teams),
    }


def metadata_audit_issue_lines(report: dict[str, Any]) -> list[str]:
    """Format a metadata comparison report as human-readable issue lines."""
    lines: list[str] = []
    for team in report.get("missing", []):
        lines.append(
            f"missing active team {team['team_id']} {team['team']} "
            f"({team['level']} / {team['league']} / {team['venue']})"
        )
    for team in report.get("stale", []):
        lines.append(
            f"stale static team {team['team_id']} {team['team']} "
            f"({team['level']} / {team['league']} / {team['venue']})"
        )
    for mismatch in report.get("mismatches", []):
        field_bits = []
        for field, values in mismatch["fields"].items():
            field_bits.append(f"{field}: {values['static']} -> {values['live']}")
        lines.append(f"metadata mismatch {mismatch['team_id']}: " + "; ".join(field_bits))
    for team in report.get("missing_locations", []):
        lines.append(
            f"missing coordinates for active team {team['team_id']} {team['team']} "
            f"({team['level']} / {team['league']} / {team['venue']})"
        )
    return lines


def has_metadata_issues(report: dict[str, Any]) -> bool:
    """Return True if the comparison report contains any freshness issue."""
    return any(report.get(key) for key in ("missing", "stale", "mismatches", "missing_locations"))


def summarize_metadata_audit(report: dict[str, Any]) -> str:
    """Return a one-line summary of an audit report."""
    return (
        f"{report.get('registry_count', 0)} registry active team(s), "
        f"{report.get('live_count', 0)} live active team(s), "
        f"{len(report.get('missing', []))} missing, "
        f"{len(report.get('stale', []))} stale, "
        f"{len(report.get('mismatches', []))} mismatched, "
        f"{len(report.get('missing_locations', []))} missing coordinates "
        f"({report.get('registry_source', 'registry')})"
    )
