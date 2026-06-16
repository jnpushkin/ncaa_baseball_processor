"""Tests for MiLB metadata freshness helpers."""

from baseball_processor.utils.milb_metadata_audit import (
    compare_milb_metadata,
    metadata_audit_issue_lines,
)
from baseball_processor.utils.milb_metadata import (
    build_active_affiliated_registry,
    build_mlb_draft_league_registry,
    static_active_affiliated_teams,
    static_mlb_draft_league_teams,
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


def test_static_mlb_draft_league_metadata_uses_six_official_clubs():
    static = static_mlb_draft_league_teams()
    by_team = {team["team"]: team for team in static.values()}

    assert set(by_team) == {
        "Aberdeen IronBirds",
        "Mahoning Valley Scrappers",
        "State College Spikes",
        "Trenton Thunder",
        "West Virginia Black Bears",
        "Williamsport Crosscutters",
    }
    assert "Canada" not in by_team
    assert "Mexico" not in by_team
    assert by_team["Mahoning Valley Scrappers"]["league"] == "MLB Draft League"
    assert by_team["Mahoning Valley Scrappers"]["venue"] == "7 17 Credit Union Field at Eastwood"
    assert by_team["Mahoning Valley Scrappers"]["lat"] == 41.21861
    assert by_team["Mahoning Valley Scrappers"]["lng"] == -80.755


def test_mlb_draft_league_registry_filters_to_official_club_overrides():
    registry = build_mlb_draft_league_registry({
        545: {
            "team_id": 545,
            "team": "Mahoning Valley Scrappers",
            "level": "Independent",
            "level_code": "IND",
            "league": "MLB Draft League",
            "venue": "7 17 Credit Union Field at Eastwood",
            "sport_id": 22,
        }
    }, season=2026, official_club_names=("Mahoning Valley Scrappers",))

    team = registry["teams"][0]

    assert registry["season"] == 2026
    assert registry["official_club_names"] == ["Mahoning Valley Scrappers"]
    assert team["team"] == "Mahoning Valley Scrappers"
    assert team["team_id"] == 545
    assert team["level"] == "Independent"
    assert team["league"] == "MLB Draft League"
    assert team["city"] == "Niles, OH"
    assert team["lat"] == 41.21861
    assert team["lng"] == -80.755
    assert team["logo"] == "https://www.mlbstatic.com/team-logos/545.svg"
