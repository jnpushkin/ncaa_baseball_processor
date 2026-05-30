"""Tests for NCAA API parser edge cases."""

from parsers.ncaa_api import _enrich_batters_from_pbp, parse_boxscore, parse_ncaa_api_batting


def test_ncaa_api_batting_skips_pitcher_stat_echo_rows():
    players = [
        {
            "firstName": "ben",
            "lastName": "Jacobs",
            "position": "",
            "number": 22,
            "starter": True,
            "participated": True,
            "batterStats": {
                "atBats": "0",
                "runsScored": "3",
                "hits": "4",
                "runsBattedIn": "0",
                "walks": "1",
                "strikeouts": "11",
            },
            "pitcherStats": {
                "hitsAllowed": "4",
                "runsAllowed": "3",
                "walksAllowed": "1",
                "inningsPitched": "5",
                "battersFaced": "20",
            },
            "fieldStats": {},
        },
        {
            "firstName": "actual",
            "lastName": "Batter",
            "position": "DH",
            "number": 7,
            "starter": True,
            "participated": True,
            "batterStats": {
                "atBats": "0",
                "runsScored": "1",
                "hits": "0",
                "runsBattedIn": "0",
                "walks": "1",
                "strikeouts": "0",
            },
            "pitcherStats": {},
            "fieldStats": {},
        },
    ]

    batters = parse_ncaa_api_batting(players)

    assert [row["name"] for row in batters] == ["actual Batter"]


def test_ncaa_api_batting_skips_strikeout_only_pitcher_echo_rows():
    players = [
        {
            "firstName": "relief",
            "lastName": "Pitcher",
            "position": "",
            "number": 14,
            "starter": False,
            "participated": True,
            "batterStats": {
                "atBats": "0",
                "runsScored": "0",
                "hits": "0",
                "runsBattedIn": "0",
                "walks": "0",
                "strikeouts": "1",
            },
            "pitcherStats": {
                "hitsAllowed": "0",
                "runsAllowed": "0",
                "walksAllowed": "0",
                "strikeouts": "1",
                "inningsPitched": "1",
                "battersFaced": "4",
            },
            "fieldStats": {},
        },
        {
            "firstName": "actual",
            "lastName": "Batter",
            "position": "PH",
            "number": 7,
            "starter": False,
            "participated": True,
            "batterStats": {
                "atBats": "0",
                "runsScored": "0",
                "hits": "0",
                "runsBattedIn": "0",
                "walks": "1",
                "strikeouts": "0",
            },
            "pitcherStats": {},
            "fieldStats": {},
        },
    ]

    batters = parse_ncaa_api_batting(players)

    assert [row["name"] for row in batters] == ["actual Batter"]


def test_ncaa_api_pbp_enrichment_uses_comma_initial_for_duplicate_last_names():
    batters = [
        {"name": "Kuhio Aloy", "doubles": 0, "triples": 0, "hr": 0, "sb": 0},
        {"name": "Wehiwa Aloy", "doubles": 0, "triples": 0, "hr": 0, "sb": 0},
    ]
    game_notes = {
        "doubles": [{"player": "aloy, w.", "game_count": 1}],
        "stolen_bases": [{"player": "aloy, w.", "game_count": 1}],
    }

    _enrich_batters_from_pbp(batters, game_notes)

    assert batters[0]["doubles"] == 0
    assert batters[0]["sb"] == 0
    assert batters[1]["doubles"] == 1
    assert batters[1]["sb"] == 1


def test_parse_boxscore_does_not_swap_home_away_for_null_pbp_placeholders():
    boxscore = {
        "teams": [
            {"teamId": "43306", "isHome": True, "nameShort": "Grand Canyon", "name6Char": "GCANYN"},
            {"teamId": "42879", "isHome": False, "nameShort": "Rutgers", "name6Char": "RUTGER"},
        ],
        "teamBoxscore": [
            {
                "teamId": "43306",
                "playerStats": [
                    {
                        "firstName": "Home",
                        "lastName": "Batter",
                        "position": "1B",
                        "participated": True,
                        "starter": True,
                        "batterStats": {"atBats": "4", "runsScored": "10", "hits": "3"},
                        "fieldStats": {},
                    }
                ],
            },
            {
                "teamId": "42879",
                "playerStats": [
                    {
                        "firstName": "Away",
                        "lastName": "Batter",
                        "position": "1B",
                        "participated": True,
                        "starter": True,
                        "batterStats": {"atBats": "4", "runsScored": "3", "hits": "1"},
                        "fieldStats": {},
                    }
                ],
            },
        ],
    }
    pbp = {
        "periods": [
            {
                "periodNumber": 1,
                "playbyplayStats": [
                    {"teamId": 43306, "plays": [{"playText": "null"}]},
                ],
            }
        ]
    }

    parsed = parse_boxscore(boxscore, pbp_data=pbp)

    assert parsed["metadata"]["away_team"] == "Rutgers"
    assert parsed["metadata"]["home_team"] == "Grand Canyon"
    assert parsed["metadata"]["away_team_score"] == 3
    assert parsed["metadata"]["home_team_score"] == 10
