"""Tests for data integrity and stat accuracy audits."""

import json

from baseball_processor.audit import audit_generated_website


def _write_site(web_dir, site_data, details):
    data_dir = web_dir / "src" / "data"
    games_dir = web_dir / "public" / "games"
    data_dir.mkdir(parents=True)
    games_dir.mkdir(parents=True)
    (data_dir / "site-data.json").write_text(json.dumps(site_data), encoding="utf-8")
    for game_id, detail in details.items():
        (games_dir / f"{game_id}.json").write_text(json.dumps(detail), encoding="utf-8")


def _empty_site(game_id):
    return {
        "unifiedGameLog": [{"game_id": game_id}],
        "unifiedBatters": [],
        "unifiedPitchers": [],
        "batterGames": [],
        "pitcherGames": [],
        "milestones": {},
    }


def _detail_payload(game_id, box_score):
    return {
        "game_id": game_id,
        "source": "ncaa",
        "date_yyyymmdd": "20250222",
        "away_team": "Source Away",
        "home_team": "Source Home",
        "away_score": 5,
        "home_score": 3,
        "venue": "Source Field",
        "box_score": box_score,
    }


def _source_truth_payload(game_id, box_score):
    return {
        game_id: {
            "game_id": game_id,
            "source": "ncaa",
            "date_yyyymmdd": "20250222",
            "away_team": "Source Away",
            "home_team": "Source Home",
            "away_score": 5,
            "home_score": 3,
            "venue": "Source Field",
            "box_score": box_score,
        }
    }


def _box_score(**sections):
    box_score = {
        "away_batting": [],
        "home_batting": [],
        "away_pitching": [],
        "home_pitching": [],
    }
    box_score.update(sections)
    return box_score


def test_generated_audit_flags_impossible_detail_batting_stats(tmp_path):
    game_id = "bad_game"
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [{"game_id": game_id}],
            "unifiedBatters": [{"name": "Bad Batter", "ab": 1, "h": 2, "doubles": 0, "triples": 0, "hr": 0, "avg": "2.000", "slg": "2.000"}],
            "unifiedPitchers": [],
            "batterGames": [],
            "pitcherGames": [],
            "milestones": {},
        },
        {
            game_id: {
                "box_score": {
                    "away_batting": [{"name": "Bad Batter", "ab": 1, "r": 0, "h": 2, "rbi": 0, "bb": 0, "k": 0, "doubles": 0, "triples": 0, "hr": 0, "sb": 0}],
                    "home_batting": [],
                    "away_pitching": [],
                    "home_pitching": [],
                }
            }
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert any("hits (2) exceed at-bats (1)" in issue for issue in issues)


def test_generated_audit_flags_missing_game_log_venues(tmp_path):
    game_id = "missing_venue"
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [
                {
                    "game_id": game_id,
                    "date": "02/22/2025",
                    "date_sort": "20250222",
                    "away_team": "Rutgers",
                    "home_team": "Grand Canyon",
                    "away_score": 3,
                    "home_score": 10,
                    "level": "NCAA",
                    "venue": "",
                }
            ],
            "unifiedBatters": [],
            "unifiedPitchers": [],
            "batterGames": [],
            "pitcherGames": [],
            "milestones": {},
        },
        {
            game_id: {
                "box_score": {
                    "away_batting": [],
                    "home_batting": [],
                    "away_pitching": [],
                    "home_pitching": [],
                }
            }
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert any("unifiedGameLog row(s) missing venue" in issue for issue in issues)


def test_generated_audit_flags_semantic_game_log_duplicates(tmp_path):
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [
                {
                    "game_id": "pdf_game",
                    "date": "06/16/2025",
                    "date_sort": "20250616",
                    "away_team": "Arkansas Razorbacks",
                    "home_team": "Murray State Racers",
                    "away_score": 3,
                    "home_score": 0,
                    "level": "NCAA",
                    "venue": "Charles Schwab Field Omaha",
                },
                {
                    "game_id": "api_game",
                    "date": "06/16/2025",
                    "date_sort": "20250616",
                    "away_team": "Arkansas",
                    "home_team": "Murray St.",
                    "away_score": 3,
                    "home_score": 0,
                    "level": "NCAA",
                    "venue": "Charles Schwab Field Omaha",
                },
            ],
            "unifiedBatters": [],
            "unifiedPitchers": [],
            "batterGames": [],
            "pitcherGames": [],
            "milestones": {},
        },
        {
            "pdf_game": {"box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []}},
            "api_game": {"box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []}},
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert any("duplicate unifiedGameLog game key" in issue for issue in issues)


def test_generated_audit_flags_single_initial_names_with_bref_ids(tmp_path):
    game_id = "initial_name_game"
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [{"game_id": game_id}],
            "unifiedBatters": [
                {
                    "name": "H. Ford",
                    "team": "Virginia",
                    "bref_id": "ford--002hen",
                    "ab": 4,
                    "h": 2,
                    "doubles": 0,
                    "triples": 0,
                    "hr": 1,
                    "avg": ".500",
                    "slg": "1.250",
                }
            ],
            "unifiedPitchers": [],
            "batterGames": [],
            "pitcherGames": [],
            "milestones": {},
        },
        {
            game_id: {
                "box_score": {
                    "away_batting": [
                        {
                            "name": "H. Ford",
                            "full_name": "H. Ford",
                            "bref_id": "ford--002hen",
                            "ab": 4,
                            "r": 1,
                            "h": 2,
                            "rbi": 3,
                            "bb": 0,
                            "k": 0,
                            "doubles": 0,
                            "triples": 0,
                            "hr": 1,
                            "sb": 0,
                        }
                    ],
                    "home_batting": [],
                    "away_pitching": [],
                    "home_pitching": [],
                }
            }
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert any("single-initial player names" in issue for issue in issues)


def test_generated_audit_flags_ncaa_player_rows_missing_bref_links(tmp_path):
    game_id = "missing_player_link"
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [{"game_id": game_id}],
            "unifiedBatters": [
                {
                    "name": "Isaiah Monge",
                    "team": "Western Illinois",
                    "level": "NCAA",
                    "bref_id": "",
                    "ab": 4,
                    "h": 1,
                    "doubles": 0,
                    "triples": 0,
                    "hr": 0,
                    "avg": ".250",
                    "slg": ".250",
                }
            ],
            "unifiedPitchers": [],
            "batterGames": [],
            "pitcherGames": [],
            "milestones": {},
        },
        {
            game_id: {
                "box_score": {
                    "away_batting": [],
                    "home_batting": [],
                    "away_pitching": [],
                    "home_pitching": [],
                }
            }
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert any("missing B-Ref/Chadwick link" in issue for issue in issues)


def test_generated_audit_flags_duplicate_ncaa_player_game_rows(tmp_path):
    game_id = "duplicate_player_game"
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [{"game_id": game_id}],
            "unifiedBatters": [],
            "unifiedPitchers": [],
            "batterGames": [
                {
                    "Name": "Jeriah Lewis",
                    "team": "San Jose State",
                    "level": "NCAA",
                    "game_id": game_id,
                    "bref_id": "lewis-008jer",
                    "ab": 4,
                },
                {
                    "Name": "Jeriah Lewis",
                    "team": "San Jose State",
                    "level": "NCAA",
                    "game_id": game_id,
                    "bref_id": "lewis-008jer",
                    "ab": 4,
                },
            ],
            "pitcherGames": [],
            "milestones": {},
        },
        {
            game_id: {
                "box_score": {
                    "away_batting": [],
                    "home_batting": [],
                    "away_pitching": [],
                    "home_pitching": [],
                }
            }
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert any("duplicate NCAA player-game row" in issue for issue in issues)


def test_generated_audit_accepts_mckenzie_golden_game(tmp_path):
    game_id = "partner_pioneer_league_20260520_6ela"
    _write_site(
        tmp_path,
        {
            "unifiedGameLog": [{"game_id": game_id}],
            "unifiedBatters": [
                {
                    "name": "T.J. McKenzie",
                    "team": "Oakland Ballers",
                    "ab": 3,
                    "h": 3,
                    "doubles": 0,
                    "triples": 0,
                    "hr": 3,
                    "rbi": 6,
                    "avg": "1.000",
                    "slg": "4.000",
                }
            ],
            "unifiedPitchers": [],
            "batterGames": [],
            "pitcherGames": [],
            "milestones": {
                "threeHrGames": [
                    {"GameID": game_id, "Player": "T.J. McKenzie", "HR": 3, "H": 3, "RBI": 6}
                ]
            },
        },
        {
            game_id: {
                "box_score": {
                    "away_batting": [],
                    "home_batting": [{"name": "T.J. McKenzie", "ab": 3, "r": 4, "h": 3, "rbi": 6, "bb": 1, "k": 0, "doubles": 0, "triples": 0, "hr": 3, "sb": 0}],
                    "away_pitching": [],
                    "home_pitching": [],
                }
            }
        },
    )

    _summary, issues, _warnings = audit_generated_website(tmp_path)

    assert issues == []


def test_source_truth_mismatches_warn_without_blocking(tmp_path):
    game_id = "source_truth_warning"
    actual_row = {
        "name": "Source Batter",
        "full_name": "Source Batter",
        "team": "Source Away",
        "bref_id": "source-batter-1",
        "ab": 4,
        "r": 1,
        "h": 1,
        "rbi": 0,
        "bb": 0,
        "k": 1,
        "doubles": 0,
        "triples": 0,
        "hr": 0,
        "sb": 0,
        "cs": 0,
    }
    expected_row = {**actual_row, "h": 2}
    _write_site(
        tmp_path,
        _empty_site(game_id),
        {game_id: _detail_payload(game_id, _box_score(away_batting=[actual_row]))},
    )

    summary, issues, warnings = audit_generated_website(
        tmp_path,
        expected_source_truth=_source_truth_payload(game_id, _box_score(away_batting=[expected_row])),
    )

    assert issues == []
    assert summary["source_truth_mismatches"] == 1
    assert any("source_truth" in warning and "generated h=1" in warning for warning in warnings)


def test_source_truth_mismatches_can_be_strict_errors(tmp_path):
    game_id = "source_truth_strict"
    actual_row = {
        "name": "Source Batter",
        "full_name": "Source Batter",
        "team": "Source Away",
        "bref_id": "source-batter-1",
        "ab": 4,
        "r": 1,
        "h": 1,
        "rbi": 0,
        "bb": 0,
        "k": 1,
        "doubles": 0,
        "triples": 0,
        "hr": 0,
        "sb": 0,
        "cs": 0,
    }
    expected_row = {**actual_row, "h": 2}
    _write_site(
        tmp_path,
        _empty_site(game_id),
        {game_id: _detail_payload(game_id, _box_score(away_batting=[actual_row]))},
    )

    _summary, issues, warnings = audit_generated_website(
        tmp_path,
        expected_source_truth=_source_truth_payload(game_id, _box_score(away_batting=[expected_row])),
        strict_source_truth=True,
    )

    assert warnings == []
    assert any("source_truth" in issue and "generated h=1" in issue for issue in issues)


def test_source_truth_flags_missing_generated_rows(tmp_path):
    game_id = "source_truth_missing_row"
    expected_row = {
        "name": "Missing Batter",
        "full_name": "Missing Batter",
        "team": "Source Away",
        "bref_id": "missing-batter-1",
        "ab": 4,
        "r": 1,
        "h": 2,
        "rbi": 0,
        "bb": 0,
        "k": 1,
        "doubles": 0,
        "triples": 0,
        "hr": 0,
        "sb": 0,
        "cs": 0,
    }
    _write_site(
        tmp_path,
        _empty_site(game_id),
        {game_id: _detail_payload(game_id, _box_score())},
    )

    _summary, issues, _warnings = audit_generated_website(
        tmp_path,
        expected_source_truth=_source_truth_payload(game_id, _box_score(away_batting=[expected_row])),
        strict_source_truth=True,
    )

    assert any("missing generated row for Missing Batter" in issue for issue in issues)


def test_source_truth_skips_untrusted_pitcher_np_and_hr(tmp_path):
    game_id = "source_truth_untrusted_pitching"
    actual_row = {
        "name": "Source Pitcher",
        "full_name": "Source Pitcher",
        "team": "Source Away",
        "bref_id": "source-pitcher-1",
        "ip": "1.0",
        "h": 1,
        "r": 0,
        "er": 0,
        "bb": 0,
        "k": 2,
        "hr": 0,
        "bf": 4,
        "np": 0,
    }
    expected_row = {**actual_row, "hr": 3, "np": 99}
    _write_site(
        tmp_path,
        _empty_site(game_id),
        {game_id: _detail_payload(game_id, _box_score(away_pitching=[actual_row]))},
    )

    _summary, issues, warnings = audit_generated_website(
        tmp_path,
        expected_source_truth=_source_truth_payload(game_id, _box_score(away_pitching=[expected_row])),
        strict_source_truth=True,
    )

    assert not any(issue.startswith("source_truth") for issue in issues)
    assert warnings == []
