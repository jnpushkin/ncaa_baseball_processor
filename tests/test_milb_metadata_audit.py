"""Tests for MiLB metadata freshness helpers."""

from baseball_processor.utils.milb_metadata_audit import (
    compare_milb_metadata,
    metadata_audit_issue_lines,
)
from baseball_processor.utils.milb_metadata import (
    build_active_affiliated_registry,
    static_active_affiliated_teams,
)


def test_static_active_metadata_reflects_2026_affiliation_changes():
    static = static_active_affiliated_teams()
    by_team = {team["team"]: team for team in static.values()}

    assert by_team["Frederick Keys"]["level"] == "High-A"
    assert by_team["Frederick Keys"]["league"] == "South Atlantic League"
    assert by_team["Hickory Crawdads"]["level"] == "Single-A"
    assert by_team["Hickory Crawdads"]["league"] == "Carolina League"
    assert "Aberdeen IronBirds" not in by_team


def test_compare_milb_metadata_reports_missing_stale_and_mismatch():
    static = {
        1: {"team_id": 1, "team": "Static Team", "level": "High-A", "league": "Old League", "venue": "Old Park"},
        2: {"team_id": 2, "team": "Stale Team", "level": "Single-A", "league": "Carolina League", "venue": "Stale Park"},
    }
    live = {
        1: {"team_id": 1, "team": "Static Team", "level": "High-A", "league": "New League", "venue": "New Park"},
        3: {"team_id": 3, "team": "Missing Team", "level": "Double-A", "league": "Eastern League", "venue": "Missing Park"},
    }

    report = compare_milb_metadata(static, live)
    lines = metadata_audit_issue_lines(report)

    assert report["missing"][0]["team"] == "Missing Team"
    assert report["stale"][0]["team"] == "Stale Team"
    assert report["mismatches"][0]["fields"]["league"] == {"static": "Old League", "live": "New League"}
    assert any("missing active team 3 Missing Team" in line for line in lines)
    assert any("stale static team 2 Stale Team" in line for line in lines)
    assert any("metadata mismatch 1" in line for line in lines)


def test_generated_registry_uses_live_identity_and_static_location_overrides():
    registry = build_active_affiliated_registry({
        493: {
            "team_id": 493,
            "team": "Frederick Keys",
            "level": "High-A",
            "level_code": "A+",
            "league": "South Atlantic League",
            "venue": "Nymeo Field",
            "sport_id": 13,
        }
    }, season=2026)

    team = registry["teams"][0]

    assert registry["season"] == 2026
    assert team["team"] == "Frederick Keys"
    assert team["team_id"] == 493
    assert team["league"] == "South Atlantic League"
    assert team["venue"] == "Nymeo Field"
    assert team["lat"] == 39.4016031
    assert team["lng"] == -77.4142135
    assert team["logo"] == "https://www.mlbstatic.com/team-logos/493.svg"
