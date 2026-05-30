"""Tests for website serializer helpers."""

import pandas as pd

from baseball_processor.website.parity import collect_website_data_parity_issues
from baseball_processor.normalization import normalize_game
from baseball_processor.website.generator import (
    _build_data_quality_report,
    _build_raw_game_index,
    _classify_and_id_raw_game,
    _serialize_detail_box_score,
    _serialize_data,
)
from baseball_processor.website.serializers import count_notable_milestones, scrub_json_value, serialize_milestones


def test_serialize_milestones_uses_frontend_keys():
    milestones = {
        "perfect_batting_games": pd.DataFrame([{"Player": "No Whiff", "H": 4}]),
        "three_total_bases_games": pd.DataFrame([{"Player": "Power Hitter", "TB": 10}]),
    }

    payload = serialize_milestones(milestones)

    assert payload["perfectBattingGames"][0]["Player"] == "No Whiff"
    assert payload["threeTotalBasesGames"][0]["TB"] == 10
    assert "perfect_batting_games" not in payload


def test_count_notable_milestones_handles_dataframes_and_lists():
    milestones = {
        "perfect_games": pd.DataFrame([{"Player": "Perfect Pete"}]),
        "multi_hr_games": [{"Player": "Slugger"}],
        "hr_games": [{"Player": "Common HR"}],
    }

    assert count_notable_milestones(milestones) == 2


def test_website_parity_detects_missing_milestone_payload():
    processed = {
        "milestones": {
            "perfect_games": pd.DataFrame([{"Player": "Perfect Pete"}]),
        }
    }
    json_data = {"milestones": {"perfectGames": []}}

    issues = collect_website_data_parity_issues(processed, json_data)

    assert any(issue["jsonKey"] == "perfectGames" for issue in issues)


def test_raw_game_index_uses_normalized_ncaa_api_source_and_id():
    raw_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "2026-04-18",
            "away_team": "Louisville",
            "home_team": "California",
            "away_team_score": 4,
            "home_team_score": 2,
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
    }

    game_id, source = _classify_and_id_raw_game(raw_game)
    index = _build_raw_game_index([raw_game])

    assert game_id == "ncaa_api_20260418_louisville_at_california_4_2"
    assert source == "ncaa_api"
    assert index[("20260418", "louisville", "california", "4", "2")][0][:2] == (game_id, source)


def test_raw_game_index_preserves_duplicate_matchups_with_unique_ids():
    raw_game = {
        "metadata": {
            "date": "03/15/2024",
            "away_team": "Texas",
            "home_team": "Oklahoma",
            "away_team_score": 5,
            "home_team_score": 1,
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
    }

    index = _build_raw_game_index([raw_game, raw_game])
    bucket = index[("20240315", "texas", "oklahoma", "5", "1")]

    assert [record[0] for record in bucket] == [
        "ncaa_pdf_20240315_texas_at_oklahoma_5_1",
        "ncaa_pdf_20240315_texas_at_oklahoma_5_1_2",
    ]


def test_road_only_partner_team_counts_as_home_equivalent_when_seen():
    raw_game = {
        "metadata": {
            "source": "partner",
            "date": "05/20/2026",
            "date_yyyymmdd": "20260520",
            "away_team": "RedPocket Mobiles",
            "home_team": "Oakland Ballers",
            "away_team_score": 3,
            "home_team_score": 4,
            "venue": "Raimondi Park",
            "league": {"away": "Pioneer League", "home": "Pioneer League"},
            "sport_level": {"away": "Partner", "home": "Partner"},
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
    }

    payload = _serialize_data({}, [raw_game])
    pioneer = payload["milbChecklist"]["Independent"]["leagues"]["Pioneer League"]
    redpocket = next(team for team in pioneer["teams"] if team["team"] == "RedPocket Mobiles")

    assert pioneer["teamStatus"]["RedPocket Mobiles"] == "home"
    assert redpocket["venue"] == "Road-only team"
    assert redpocket["roadOnly"] is True
    assert all(
        location.get("team") != "RedPocket Mobiles"
        for location in payload["partnerStadiumLocations"].values()
    )


def test_data_quality_report_summarizes_source_merge_warnings():
    raw_game = {
        "metadata": {
            "date": "03/14/2025",
            "date_yyyymmdd": "20250314",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
        "data_quality": {
            "source_merge": {
                "sources": ["ncaa_pdf", "ncaa_api"],
                "stats_source": "ncaa_pdf",
                "identity_source": "ncaa_api",
                "confidence": "review",
                "warning_count": 1,
                "info_count": 0,
                "issue_count": 1,
                "sections": {"away_batting": {"matched_rows": 1}},
                "issues": [
                    {
                        "code": "source_stat_disagreement",
                        "severity": "warning",
                        "section": "away_batting",
                        "player": "Jay Woolfolk",
                        "field": "HR",
                        "primary_value": 1,
                        "secondary_value": 2,
                    }
                ],
            }
        },
    }

    report = _build_data_quality_report([raw_game])

    assert report["summary"]["mergedSourceGames"] == 1
    assert report["summary"]["sourceMergeWarnings"] == 1
    assert report["summary"]["sourceMergeReviewGames"] == 1
    assert report["sourceMerge"]["issues"][0]["game_id"] == "ncaa_pdf_20250314_virginia_at_california_1_6"
    assert report["sourceMerge"]["issues"][0]["field"] == "HR"


def test_data_quality_report_includes_unmerged_source_candidates():
    raw_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6294409",
            "date": "03/30/2024",
            "date_yyyymmdd": "20240330",
            "away_team": "Santa Clara",
            "home_team": "San Francisco",
            "away_team_score": 2,
            "home_team_score": 1,
            "venue": "Benedetti Diamond (San Francisco, CA)",
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
        "data_quality": {
            "source_candidate": {
                "confidence": "not_merged",
                "reason": "score_mismatch",
                "pdf_score": (2, 0),
                "api_score": (2, 1),
                "api_game_id": "6294409",
            }
        },
    }

    report = _build_data_quality_report([raw_game])

    assert report["summary"]["mergedSourceGames"] == 0
    assert report["summary"]["unmergedSourceCandidates"] == 1
    assert report["sourceMerge"]["unmergedCandidates"][0]["reason"] == "score_mismatch"


def test_scrub_json_value_replaces_nan_and_infinity():
    payload = {"ok": 1.5, "bad": float("nan"), "items": [float("inf"), {"low": float("-inf")}]}

    assert scrub_json_value(payload) == {"ok": 1.5, "bad": None, "items": [None, {"low": None}]}


def test_detail_box_score_uses_frontend_aliases_for_ncaa_pdf_rows():
    raw_game = {
        "metadata": {
            "date": "03/15/2024",
            "away_team": "Texas",
            "home_team": "Oklahoma",
            "away_team_score": 5,
            "home_team_score": 1,
        },
        "box_score": {
            "away_batting": [
                {
                    "name": "Batter One",
                    "at_bats": 4,
                    "runs": 2,
                    "hits": 3,
                    "walks": 1,
                    "strikeouts": 0,
                }
            ],
            "home_batting": [],
            "away_pitching": [
                {
                    "name": "Pitcher One",
                    "innings_pitched": "7.0",
                    "hits": 2,
                    "runs": 1,
                    "earned_runs": 1,
                    "walks": 0,
                    "strikeouts": 8,
                    "pitches": 92,
                }
            ],
            "home_pitching": [],
        },
    }

    box_score = _serialize_detail_box_score(normalize_game(raw_game))

    assert box_score["away_batting"][0]["ab"] == 4
    assert box_score["away_batting"][0]["h"] == 3
    assert box_score["away_batting"][0]["k"] == 0
    assert box_score["away_pitching"][0]["ip"] == "7.0"
    assert box_score["away_pitching"][0]["er"] == 1
    assert box_score["away_pitching"][0]["k"] == 8
    assert box_score["away_pitching"][0]["np"] == 92


def test_detail_box_score_filters_placeholder_player_rows():
    raw_game = {
        "metadata": {
            "date": "03/15/2024",
            "away_team": "Texas",
            "home_team": "Oklahoma",
            "away_team_score": 5,
            "home_team_score": 1,
        },
        "box_score": {
            "away_batting": [
                {"name": "Unknown", "ab": 4, "h": 2},
                {"name": "Named Batter", "ab": 4, "h": 1},
            ],
            "home_batting": [],
            "away_pitching": [
                {"name": "Unknown", "ip": "1.0", "h": 0},
                {"name": "Named Pitcher", "ip": "2.0", "h": 1},
            ],
            "home_pitching": [],
        },
    }

    box_score = _serialize_detail_box_score(normalize_game(raw_game))

    assert [row["name"] for row in box_score["away_batting"]] == ["Named Batter"]
    assert [row["name"] for row in box_score["away_pitching"]] == ["Named Pitcher"]


def test_detail_box_score_filters_zero_stat_pitcher_batting_artifacts():
    raw_game = {
        "metadata": {
            "date": "05/20/2026",
            "away_team": "Missoula PaddleHeads",
            "home_team": "Oakland Ballers",
            "away_team_score": 8,
            "home_team_score": 13,
        },
        "box_score": {
            "away_batting": [
                {"name": "Real Batter", "position": "CF", "ab": 4, "h": 1},
                {"name": "Pitcher Only", "position": "", "ab": 0, "r": 0, "h": 0, "rbi": 0, "bb": 0, "so": 0},
            ],
            "home_batting": [],
            "away_pitching": [
                {"name": "Pitcher Only", "ip": "1.0", "h": 1, "r": 0, "er": 0, "bb": 0, "so": 1},
            ],
            "home_pitching": [],
        },
    }

    box_score = _serialize_detail_box_score(normalize_game(raw_game))

    assert [row["name"] for row in box_score["away_batting"]] == ["Real Batter"]
    assert [row["name"] for row in box_score["away_pitching"]] == ["Pitcher Only"]


def test_detail_box_score_merges_game_note_extra_base_stats():
    raw_game = {
        "metadata": {
            "date": "03/15/2024",
            "away_team": "Texas",
            "home_team": "Oklahoma",
            "away_team_score": 5,
            "home_team_score": 1,
        },
        "box_score": {
            "away_batting": [
                {"name": "Power Hitter", "ab": 4, "h": 2, "rbi": 3, "hr": 0},
            ],
            "home_batting": [],
            "away_pitching": [],
            "home_pitching": [],
        },
        "game_notes": {
            "home_runs": [{"player": "Power Hitter", "game_count": 1}],
        },
    }

    box_score = _serialize_detail_box_score(normalize_game(raw_game))

    row = box_score["away_batting"][0]
    assert row["hr"] == 1
    assert row["HR"] == 1
