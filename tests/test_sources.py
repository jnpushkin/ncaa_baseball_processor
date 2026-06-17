"""Tests for CLI source-loading selection rules."""

from types import SimpleNamespace

from baseball_processor import sources


def _args(**overrides):
    values = {
        "ncaa_api_game": None,
        "ncaa_api_date": None,
        "ncaa_api_date_range": None,
        "ncaa_api_only": False,
        "milb_game": None,
        "milb_only": False,
        "partner_game": None,
        "pioneer_by_date": None,
        "from_db": False,
        "from_cache_only": True,
        "no_ncaa_api": False,
        "no_milb": False,
        "include_milb": True,
        "include_partner": True,
        "no_partner": False,
        "download_pioneer_pdfs": False,
        "pioneer_artifact_dir": "",
        "roster_dir": "",
        "input_path": "",
        "no_cache": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_default_cache_mode_loads_all_source_groups(monkeypatch):
    monkeypatch.setattr(sources, "load_ncaa_from_cache", lambda: [{"source": "ncaa"}])
    monkeypatch.setattr(sources, "load_ncaa_api_from_cache", lambda: [{"source": "ncaa_api"}])
    monkeypatch.setattr(sources, "load_milb_from_cache", lambda: [{"source": "milb"}])
    monkeypatch.setattr(sources, "load_partner_from_cache", lambda: [{"source": "partner"}])

    loaded = sources.load_source_games(_args())

    assert [g["source"] for g in loaded.all_games] == ["ncaa", "ncaa_api", "milb", "partner"]


def test_processing_games_merge_exact_ncaa_pdf_api_duplicates():
    pdf_game = {
        "metadata": {
            "date": "6/18/2023",
            "away_team": "TCU",
            "home_team": "Virginia",
            "away_team_score": 4,
            "home_team_score": 3,
        },
        "box_score": {
            "away_pitching": [
                {"number": "15", "name": "Stoutenborou", "innings_pitched": 4.2, "bref_id": "stout-001sam"}
            ],
            "home_pitching": [],
        },
        "play_by_play": {"1": {"top": [{"description": "PDF detail"}]}},
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6147529",
            "date": "06/18/2023",
            "date_yyyymmdd": "20230618",
            "away_team": "TCU",
            "home_team": "Virginia",
            "away_team_score": 4,
            "home_team_score": 3,
        },
        "box_score": {
            "away_pitching": [
                {"number": "15", "name": "Sam Stoutenborough", "ip": "4.2"}
            ],
            "home_pitching": [
                {"number": "4", "name": "Jay Woolfolk", "ip": "0.2"}
            ],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])

    processing_games = loaded.processing_games

    assert len(processing_games) == 1
    merged = processing_games[0]
    assert merged["metadata"]["away_team_score"] == 4
    assert merged["metadata"]["home_team_score"] == 3
    assert merged["metadata"]["merged_sources"] == ["ncaa", "ncaa_api"]
    assert merged["metadata"]["ncaa_api_game_id"] == "6147529"
    assert merged["box_score"]["away_pitching"][0]["name"] == "Sam Stoutenborough"
    assert merged["box_score"]["away_pitching"][0]["bref_id"] == "stout-001sam"
    assert merged["box_score"]["home_pitching"][0]["name"] == "Jay Woolfolk"
    assert merged["play_by_play"] == {"1": {"top": [{"description": "PDF detail"}]}}


def test_processing_games_does_not_merge_same_date_matchup_when_scores_differ():
    pdf_game = {
        "metadata": {
            "date": "3/30/2024",
            "away_team": "Santa Clara",
            "home_team": "San Francisco",
            "away_team_score": 2,
            "home_team_score": 0,
            "venue": "Benedetti Diamond (San Francisco, CA)",
            "stadium": "Benedetti Diamond",
            "city": "San Francisco, CA",
        },
        "box_score": {"away_batting": [{"name": "PDF Player", "h": 2}]},
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6294409",
            "date": "03/30/2024",
            "date_yyyymmdd": "20240330",
            "away_team": "Santa Clara",
            "home_team": "San Francisco",
            "away_team_score": 2,
            "home_team_score": 1,
        },
        "box_score": {"away_batting": [{"number": "26", "name": "API Player", "h": 1}]},
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    processing_games = loaded.processing_games

    assert len(processing_games) == 2
    assert processing_games[0]["metadata"]["home_team_score"] == 0
    api_result = processing_games[1]
    assert api_result["metadata"]["source"] == "ncaa_api"
    assert api_result["metadata"]["venue"] == "Benedetti Diamond (San Francisco, CA)"
    assert api_result["metadata"]["venue_source"] == "same_date_pdf_matchup"
    assert api_result["data_quality"]["source_candidate"]["reason"] == "score_mismatch"


def test_processing_games_merge_ncaa_ca_suffix_team_variants():
    pdf_game = {
        "metadata": {
            "date": "4/25/2025",
            "away_team": "LMU",
            "home_team": "Saint Mary's",
            "away_team_score": 3,
            "home_team_score": 8,
        },
        "box_score": {"home_batting": [{"name": "Castellanos, Diego"}]},
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6420918",
            "date": "04/25/2025",
            "away_team": "LMU (CA)",
            "home_team": "Saint Mary's (CA)",
            "away_team_score": 3,
            "home_team_score": 8,
        },
        "box_score": {"home_batting": [{"name": "Castellanos"}]},
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])

    processing_games = loaded.processing_games

    assert len(processing_games) == 1
    assert processing_games[0]["box_score"]["home_batting"] == [
        {"name": "Castellanos, Diego"}
    ]


def test_processing_games_merge_state_abbreviation_and_nickname_variants():
    pdf_game = {
        "metadata": {
            "date": "6/16/2025",
            "away_team": "Arkansas Razorbacks",
            "home_team": "Murray State Racers",
            "away_team_score": 3,
            "home_team_score": 0,
            "venue": "Charles Schwab Field (Omaha, Neb.)",
        },
        "box_score": {"away_batting": [{"number": "1", "name": "PDF Player"}]},
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6455124",
            "date": "06/16/2025",
            "date_yyyymmdd": "20250616",
            "away_team": "Arkansas",
            "home_team": "Murray St.",
            "away_team_score": 3,
            "home_team_score": 0,
        },
        "box_score": {"away_batting": [{"number": "1", "name": "API Player"}]},
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])

    processing_games = loaded.processing_games

    assert len(processing_games) == 1
    merged = processing_games[0]
    assert merged["metadata"]["ncaa_api_game_id"] == "6455124"
    assert merged["metadata"]["venue"] == "Charles Schwab Field (Omaha, Neb.)"
    assert merged["box_score"]["away_batting"][0]["name"] == "API Player"


def test_processing_games_merge_period_abbreviated_state_name_variants():
    # NCAA API emits "Western Ill." while the PDF box score reads
    # "Western Illinois Leathernecks"; these must merge into one game.
    pdf_game = {
        "metadata": {
            "date": "2/14/2026",
            "away_team": "Western Illinois Leathernecks",
            "home_team": "San Francisco Dons",
            "away_team_score": 4,
            "home_team_score": 5,
            "venue": "Dante Benedetti Diamond",
        },
        "box_score": {"away_batting": [{"number": "1", "name": "PDF Player"}]},
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6544183",
            "date": "02/14/2026",
            "date_yyyymmdd": "20260214",
            "away_team": "Western Ill.",
            "home_team": "San Francisco",
            "away_team_score": 4,
            "home_team_score": 5,
        },
        "box_score": {"away_batting": [{"number": "1", "name": "API Player"}]},
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])

    processing_games = loaded.processing_games

    assert len(processing_games) == 1
    assert processing_games[0]["metadata"]["venue"] == "Dante Benedetti Diamond"


def test_processing_games_preserve_pdf_names_when_api_names_are_clipped():
    pdf_game = {
        "metadata": {
            "date": "2/14/2026",
            "away_team": "Western Illinois",
            "home_team": "San Francisco",
            "away_team_score": 6,
            "home_team_score": 10,
        },
        "box_score": {
            "away_batting": [
                {"name": "Wandel Campana", "at_bats": 4, "hits": 1, "rbi": 2},
                {"name": "Kenneth Perez", "at_bats": 4, "hits": 0},
            ],
            "away_pitching": [
                {"name": "Harrison Dubois", "innings_pitched": 2.2, "hits": 7},
            ],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6544183",
            "date": "02/14/2026",
            "date_yyyymmdd": "20260214",
            "away_team": "Western Ill.",
            "home_team": "San Francisco",
            "away_team_score": 6,
            "home_team_score": 10,
        },
        "box_score": {
            "away_batting": [
                {"number": "2", "name": "Wandel Campa", "full_name": "Wandel Campa", "ab": 4, "h": 1, "rbi": 2},
                {"number": "3", "name": "Kenneth Pere", "full_name": "Kenneth Pere", "ab": 4, "h": 0},
            ],
            "away_pitching": [
                {"number": "10", "name": "Harrison Dub", "full_name": "Harrison Dub", "ip": "2.2", "h": 7},
            ],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    merged = loaded.processing_games[0]

    assert [row["name"] for row in merged["box_score"]["away_batting"]] == [
        "Wandel Campana",
        "Kenneth Perez",
    ]
    assert [row["name"] for row in merged["box_score"]["away_pitching"]] == [
        "Harrison Dubois",
    ]


def test_processing_games_merge_one_day_offset_keeps_pdf_box_score_date():
    # When a PDF and NCAA API record for the same game differ by one day, the
    # PDF box-score date is authoritative (the NCAA API sometimes reports a +1
    # day offset, e.g. the 2023 CWS Virginia/Florida game). The games still
    # merge into one, but the merged date comes from the PDF, with date_yyyymmdd
    # backfilled from it.
    pdf_game = {
        "metadata": {
            "date": "6/16/2025",
            "away_team": "UCLA Bruins",
            "home_team": "LSU Tigers",
            "away_team_score": 5,
            "home_team_score": 9,
            "venue": "Charles Schwab Field (Omaha, Neb.)",
        },
        "box_score": {"away_batting": [{"number": "3", "name": "PDF Player"}]},
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6455125",
            "date": "06/17/2025",
            "date_yyyymmdd": "20250617",
            "away_team": "UCLA",
            "home_team": "LSU",
            "away_team_score": 5,
            "home_team_score": 9,
        },
        "box_score": {"away_batting": [{"number": "3", "name": "API Player"}]},
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])

    processing_games = loaded.processing_games

    assert len(processing_games) == 1
    merged = processing_games[0]
    assert merged["metadata"]["date"] == "6/16/2025"
    assert merged["metadata"]["date_yyyymmdd"] == "20250616"
    assert merged["metadata"]["venue"] == "Charles Schwab Field (Omaha, Neb.)"
    assert merged["metadata"]["ncaa_api_game_id"] == "6455125"
    assert merged["box_score"]["away_batting"][0]["name"] == "API Player"


def test_processing_games_drop_unmatched_api_placeholders_when_pdf_has_section():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"number": "4", "name": "Jay Woolfolk"}],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"number": "4", "name": "Unknown"},
                {"number": "99", "name": "Named API Player"},
            ],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    away_batting = loaded.processing_games[0]["box_score"]["away_batting"]

    assert [row["name"] for row in away_batting] == ["Jay Woolfolk", "Named API Player"]


def test_processing_games_records_source_merge_stat_disagreements_as_info():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"number": "4", "name": "Jay Woolfolk", "hr": 1, "rbi": 2}],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6412345",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"number": "4", "name": "Jay Woolfolk", "hr": 2, "rbi": 2}],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["sections"]["away_batting"]["matched_rows"] == 1
    assert source_merge["issues"][0] == {
        "code": "source_stat_disagreement",
        "severity": "info",
        "section": "away_batting",
        "category": "batting",
        "player": "Jay Woolfolk",
        "field": "HR",
        "primary_source": "ncaa_pdf",
        "secondary_source": "ncaa_api",
        "primary_value": 1,
        "secondary_value": 2,
        "match_method": "number",
    }


def test_processing_games_treats_api_whole_inning_ip_as_info():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "home_pitching": [{"number": "28", "name": "Jake Andreas", "innings_pitched": 2.1, "hits": 3}],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6412345",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "home_pitching": [{"number": "28", "name": "Jake Andreas", "ip": "2", "h": 3}],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["issues"][0] == {
        "code": "secondary_ip_partial_outs_unavailable",
        "severity": "info",
        "section": "home_pitching",
        "category": "pitching",
        "player": "Jake Andreas",
        "field": "IP",
        "primary_source": "ncaa_pdf",
        "secondary_source": "ncaa_api",
        "primary_value": 2.333,
        "secondary_value": 2.0,
        "match_method": "number",
    }


def test_processing_games_records_non_partial_out_ip_disagreements_as_info():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "home_pitching": [{"number": "28", "name": "Jake Andreas", "innings_pitched": 3.0, "hits": 3}],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6412345",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "home_pitching": [{"number": "28", "name": "Jake Andreas", "ip": "2", "h": 3}],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["issues"][0]["code"] == "source_stat_disagreement"
    assert source_merge["issues"][0]["severity"] == "info"
    assert source_merge["issues"][0]["field"] == "IP"


def test_processing_games_ignores_missing_secondary_stats_for_merge_quality():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"number": "4", "name": "Jay Woolfolk", "hr": 1, "rbi": 2}],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"number": "4", "name": "Jay Woolfolk"}],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["issue_count"] == 0


def test_processing_games_treats_all_zero_api_strikeouts_as_unavailable():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"number": "4", "name": "Jay Woolfolk", "strikeouts": 2},
                {"number": "5", "name": "Named Batter", "strikeouts": 1},
            ],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"number": "4", "name": "Jay Woolfolk", "k": 0},
                {"number": "5", "name": "Named Batter", "k": 0},
            ],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["issues"][0]["code"] == "secondary_stat_field_unavailable"
    assert source_merge["issues"][0]["field"] == "K"


def test_processing_games_treats_placeholder_only_api_strikeouts_as_unavailable():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"number": "4", "name": "Jay Woolfolk", "strikeouts": 2},
                {"number": "5", "name": "Named Batter", "strikeouts": 1},
            ],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"number": "4", "name": "Jay Woolfolk", "k": 0},
                {"number": "5", "name": "Named Batter", "k": 0},
                {"number": "99", "name": "Unknown", "ab": 4, "k": 1},
            ],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["issues"][0]["code"] == "secondary_stat_field_unavailable"
    assert source_merge["issues"][0]["field"] == "K"


def test_processing_games_does_not_use_clipped_api_names_for_merge_quality_or_rows():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"name": "Aiden Taurek", "rbi": 1}],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [{"name": "aide Taurek", "rbi": 2}],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    merged = loaded.processing_games[0]
    source_merge = merged["data_quality"]["source_merge"]

    assert merged["box_score"]["away_batting"][0]["name"] == "Aiden Taurek"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["issues"][0]["severity"] == "info"
    assert source_merge["issues"][0]["player"] == "Aiden Taurek"


def test_processing_games_ignores_impossible_api_batting_strikeout_echoes():
    pdf_game = {
        "metadata": {
            "date": "3/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"name": "Aiden Taurek", "strikeouts": 1},
                {"name": "Daniel Guevara", "at_bats": 0, "walks": 0, "strikeouts": 0},
            ],
        },
    }
    api_game = {
        "metadata": {
            "source": "ncaa_api",
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 1,
            "home_team_score": 6,
        },
        "box_score": {
            "away_batting": [
                {"name": "aide Taurek", "ab": 4, "k": 0},
                {"name": "dani Castro", "ab": 0, "bb": 1, "k": 1},
            ],
        },
    }

    loaded = sources.SourceGames([pdf_game], [api_game], [], [])
    source_merge = loaded.processing_games[0]["data_quality"]["source_merge"]

    assert source_merge["confidence"] == "high"
    assert source_merge["warning_count"] == 0
    assert source_merge["info_count"] == 1
    assert source_merge["issues"][0]["code"] == "secondary_stat_field_unavailable"
    assert source_merge["issues"][0]["field"] == "K"


def test_milb_only_cache_mode_does_not_load_ncaa_api_or_partner(monkeypatch):
    def fail_loader():
        raise AssertionError("unexpected default source load")

    monkeypatch.setattr(sources, "load_ncaa_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_ncaa_api_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_partner_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_milb_from_cache", lambda: [{"source": "milb"}])

    loaded = sources.load_source_games(_args(milb_only=True))

    assert loaded.ncaa_games == []
    assert loaded.ncaa_api_games == []
    assert loaded.milb_games == [{"source": "milb"}]
    assert loaded.partner_games == []


def test_single_milb_game_does_not_load_default_sources(monkeypatch):
    def fail_loader():
        raise AssertionError("unexpected default source load")

    monkeypatch.setattr(sources, "load_ncaa_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_ncaa_api_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_milb_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_partner_from_cache", fail_loader)
    monkeypatch.setattr(
        "parsers.milb_api.process_milb_game",
        lambda game_id, cache_dir: {
            "metadata": {
                "away_team": "Away",
                "home_team": "Home",
                "away_team_score": 1,
                "home_team_score": 2,
            }
        },
    )

    loaded = sources.load_source_games(_args(milb_game=123, from_cache_only=False))

    assert len(loaded.milb_games) == 1
    assert loaded.all_ncaa == []
    assert loaded.partner_games == []


def test_single_ncaa_api_game_does_not_load_default_sources(monkeypatch):
    def fail_loader():
        raise AssertionError("unexpected default source load")

    monkeypatch.setattr(sources, "load_ncaa_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_ncaa_api_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_milb_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_partner_from_cache", fail_loader)
    monkeypatch.setattr(
        "parsers.ncaa_api.process_ncaa_api_game",
        lambda game_id, cache_dir: {
            "metadata": {
                "away_team": "Away",
                "home_team": "Home",
                "away_team_score": 3,
                "home_team_score": 4,
            }
        },
    )

    loaded = sources.load_source_games(_args(ncaa_api_game="abc123", from_cache_only=False))

    assert len(loaded.ncaa_api_games) == 1
    assert loaded.ncaa_games == []
    assert loaded.milb_games == []
    assert loaded.partner_games == []


def test_single_partner_game_does_not_load_default_sources(monkeypatch):
    def fail_loader():
        raise AssertionError("unexpected default source load")

    monkeypatch.setattr(sources, "load_ncaa_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_ncaa_api_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_milb_from_cache", fail_loader)
    monkeypatch.setattr(sources, "load_partner_from_cache", fail_loader)
    monkeypatch.setattr(
        "parsers.partner_leagues.process_partner_game",
        lambda game_id, league, cache_dir, **kwargs: {
            "metadata": {
                "league": {"home": league},
                "away_team": "Away",
                "home_team": "Home",
                "away_team_score": 5,
                "home_team_score": 6,
            }
        },
    )

    loaded = sources.load_source_games(_args(partner_game="pioneer:game123", from_cache_only=False))

    assert len(loaded.partner_games) == 1
    assert loaded.all_ncaa == []
    assert loaded.milb_games == []


def test_cache_only_single_milb_game_loads_exact_cache_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "MILB_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "parsers.milb_api.process_milb_game",
        lambda game_id, cache_dir: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )
    (tmp_path / "milb_123.json").write_text(
        '{"metadata":{"away_team":"Away","home_team":"Home","away_team_score":1,"home_team_score":2}}'
    )

    loaded = sources.load_source_games(_args(milb_game=123, from_cache_only=True))

    assert len(loaded.milb_games) == 1


def test_cache_only_single_milb_game_does_not_fetch_on_cache_miss(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "MILB_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "parsers.milb_api.process_milb_game",
        lambda game_id, cache_dir: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )

    loaded = sources.load_source_games(_args(milb_game=123, from_cache_only=True))

    assert loaded.all_games == []


def test_cache_only_single_ncaa_api_game_does_not_fetch_on_cache_miss(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "NCAA_API_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "parsers.ncaa_api.process_ncaa_api_game",
        lambda game_id, cache_dir: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )

    loaded = sources.load_source_games(_args(ncaa_api_game="abc123", from_cache_only=True))

    assert loaded.all_games == []


def test_cache_only_single_partner_game_does_not_fetch_or_enrich_on_cache_miss(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "PARTNER_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "parsers.partner_leagues.process_partner_game",
        lambda game_id, league, cache_dir, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )

    loaded = sources.load_source_games(_args(partner_game="pioneer:game123", from_cache_only=True))

    assert loaded.all_games == []


def test_cache_only_ncaa_api_date_filters_cached_games(monkeypatch):
    monkeypatch.setattr(
        sources,
        "load_ncaa_api_from_cache",
        lambda: [
            {"metadata": {"date_yyyymmdd": "20260418", "away_team": "A", "home_team": "B"}},
            {"metadata": {"date_yyyymmdd": "20260419", "away_team": "C", "home_team": "D"}},
        ],
    )
    monkeypatch.setattr(
        "parsers.ncaa_api.process_ncaa_api_date_range",
        lambda start, end, cache_dir: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )

    loaded = sources.load_source_games(_args(ncaa_api_date="2026-04-18", from_cache_only=True))

    assert [game["metadata"]["away_team"] for game in loaded.ncaa_api_games] == ["A"]


def test_cache_only_pioneer_by_date_does_not_fetch_schedule(monkeypatch):
    monkeypatch.setattr(
        "parsers.partner_leagues.list_pioneer_games_for_date",
        lambda date: (_ for _ in ()).throw(AssertionError("unexpected schedule fetch")),
    )

    loaded = sources.load_source_games(_args(pioneer_by_date="2026-05-20", from_cache_only=True))

    assert loaded.all_games == []
