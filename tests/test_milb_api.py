"""Tests for MiLB Stats API parsing."""

from parsers.milb_api import parse_boxscore, parse_game_feed_play_by_play


def _boxscore(away_league, home_league, away_parent="", home_parent=""):
    return {
        "teams": {
            "away": {
                "team": {
                    "name": "Away Team",
                    "abbreviation": "AWY",
                    "id": 1,
                    "parentOrgName": away_parent,
                    "league": {"name": away_league},
                    "sport": {"name": "High-A"},
                },
                "players": {},
                "teamStats": {"batting": {"runs": 0}},
            },
            "home": {
                "team": {
                    "name": "Home Team",
                    "abbreviation": "HOM",
                    "id": 2,
                    "parentOrgName": home_parent,
                    "league": {"name": home_league},
                    "sport": {"name": "High-A"},
                },
                "players": {},
                "teamStats": {"batting": {"runs": 2}},
            },
        },
        "info": [],
    }


def _feed():
    return {
        "gameData": {
            "game": {"pk": 12345},
            "datetime": {"officialDate": "2026-05-31"},
            "venue": {"name": "Maimonides Park", "location": {"city": "Brooklyn", "state": "New York"}},
        }
    }


def _pitcher(player_id, name, ip="1.0"):
    return {
        "person": {"id": player_id, "fullName": name},
        "stats": {
            "pitching": {
                "inningsPitched": ip,
                "battersFaced": 4,
            }
        },
    }


def test_south_atlantic_league_is_not_classified_as_partner():
    game = parse_boxscore(
        _boxscore(
            "South Atlantic League",
            "South Atlantic League",
            away_parent="Washington Nationals",
            home_parent="New York Mets",
        ),
        _feed(),
    )

    assert game["metadata"]["source"] == "milb"


def test_affiliated_league_without_parent_org_is_not_classified_as_partner():
    game = parse_boxscore(
        _boxscore("South Atlantic League", "South Atlantic League"),
        _feed(),
    )

    assert game["metadata"]["source"] == "milb"


def test_atlantic_league_of_professional_baseball_is_classified_as_partner():
    game = parse_boxscore(
        _boxscore("Atlantic League of Professional Baseball", "Atlantic League of Professional Baseball"),
        _feed(),
    )

    assert game["metadata"]["source"] == "partner"


def test_mlb_draft_league_is_classified_as_partner():
    game = parse_boxscore(
        _boxscore(
            "MLB Draft League",
            "MLB Draft League",
            away_parent="Office of the Commissioner",
            home_parent="Office of the Commissioner",
        ),
        _feed(),
    )

    assert game["metadata"]["source"] == "partner"


def test_pitchers_preserve_api_appearance_order():
    boxscore = _boxscore(
        "South Atlantic League",
        "South Atlantic League",
        away_parent="Washington Nationals",
        home_parent="New York Mets",
    )
    boxscore["teams"]["away"]["pitchers"] = [300, 100, 200]
    boxscore["teams"]["away"]["players"] = {
        "ID100": _pitcher(100, "Second Pitcher"),
        "ID200": _pitcher(200, "Third Pitcher"),
        "ID300": _pitcher(300, "Starting Pitcher", ip="5.0"),
    }

    game = parse_boxscore(boxscore, _feed())

    assert [row["name"] for row in game["box_score"]["away_pitching"]] == [
        "Starting Pitcher",
        "Second Pitcher",
        "Third Pitcher",
    ]


def test_pinchrunners_with_runs_are_kept_without_plate_appearance():
    boxscore = _boxscore(
        "Carolina League",
        "Carolina League",
        away_parent="Houston Astros",
        home_parent="Kansas City Royals",
    )
    boxscore["teams"]["home"]["players"] = {
        "ID100": {
            "person": {"id": 100, "fullName": "Starting Batter"},
            "position": {"abbreviation": "CF"},
            "battingOrder": "101",
            "stats": {
                "batting": {
                    "atBats": 4,
                    "runs": 0,
                    "hits": 1,
                    "rbi": 0,
                    "baseOnBalls": 0,
                    "strikeOuts": 1,
                }
            },
        },
        "ID200": {
            "person": {"id": 200, "fullName": "Pinch Runner"},
            "position": {"abbreviation": "PR"},
            "battingOrder": "102",
            "stats": {
                "batting": {
                    "atBats": 0,
                    "runs": 1,
                    "hits": 0,
                    "rbi": 0,
                    "baseOnBalls": 0,
                    "strikeOuts": 0,
                }
            },
        },
    }

    game = parse_boxscore(boxscore, _feed())

    home_names = [row["name"] for row in game["box_score"]["home_batting"]]
    assert "Pinch Runner" in home_names
    pinch_runner = next(row for row in game["box_score"]["home_batting"] if row["name"] == "Pinch Runner")
    assert pinch_runner["ab"] == 0
    assert pinch_runner["r"] == 1


def test_attendance_is_parsed_from_labeled_info_entry_not_first():
    # The first info entry is a decoy (umpire-style name); attendance must be
    # read from the entry whose label is "Att"/"Attendance", not info[0].
    boxscore = _boxscore("Pacific Coast League", "Pacific Coast League")
    boxscore["info"] = [
        {"label": "Weather", "value": "72 degrees, Clear."},
        {"label": "Wind", "value": "5 mph, Out To LF."},
        {"label": "Att", "value": "5,123."},
        {"label": "Venue", "value": "Werner Park"},
    ]

    game = parse_boxscore(boxscore, _feed())

    assert game["metadata"]["attendance"] == 5123


def test_attendance_is_none_when_absent():
    boxscore = _boxscore("Pacific Coast League", "Pacific Coast League")
    boxscore["info"] = [{"label": "Weather", "value": "72 degrees, Clear."}]

    game = parse_boxscore(boxscore, _feed())

    assert game["metadata"]["attendance"] is None


def test_parse_game_feed_play_by_play_groups_all_plays_by_inning_half():
    pbp = parse_game_feed_play_by_play(
        {
            "liveData": {
                "plays": {
                    "allPlays": [
                        {
                            "about": {"inning": 1, "halfInning": "top"},
                            "result": {
                                "description": "Away Batter singles on a line drive.",
                                "rbi": 0,
                                "awayScore": 0,
                                "homeScore": 0,
                                "event": "Single",
                            },
                            "count": {"balls": 1, "strikes": 2},
                            "matchup": {
                                "batter": {"fullName": "Away Batter"},
                                "pitcher": {"fullName": "Home Pitcher"},
                            },
                        },
                        {
                            "about": {"inning": 1, "halfInning": "bottom"},
                            "result": {
                                "description": "Home Batter doubles. Runner scores.",
                                "rbi": 1,
                                "awayScore": 0,
                                "homeScore": 1,
                                "event": "Double",
                            },
                            "count": {"balls": 0, "strikes": 1},
                            "matchup": {
                                "batter": {"fullName": "Home Batter"},
                                "pitcher": {"fullName": "Away Pitcher"},
                            },
                        },
                    ]
                }
            }
        }
    )

    assert pbp[1]["top"][0]["description"] == "Away Batter singles on a line drive."
    assert pbp[1]["top"][0]["pitch_count"] == "1-2"
    assert pbp[1]["bottom"][0]["rbi"] == 1
    assert pbp[1]["bottom"][0]["home_score"] == 1
