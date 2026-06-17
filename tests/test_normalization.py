"""Tests for source-neutral game normalization."""

from baseball_processor.normalization import build_player_name_aliases, normalize_game, resolve_player_name_alias
from baseball_processor.utils.helpers import normalize_venue_name, resolve_player_display_name


class FakePlayerNameMapper:
    def __init__(self, names):
        self.names = names

    def get_player_name(self, any_id):
        return self.names.get(any_id)


def test_resolves_single_initial_names_from_chadwick_id():
    mapper = FakePlayerNameMapper(
        {
            "ford--002hen": "Henry Ford",
            "mcken-000tj": "Thomas McKenzie",
            "colaru000aj-": "A. J. Colarusso",
        }
    )

    assert resolve_player_display_name("H. Ford", "ford--002hen", mapper) == "Henry Ford"
    assert resolve_player_display_name("T.J. McKenzie", "mcken-000tj", mapper) == "T.J. McKenzie"
    assert resolve_player_display_name("a Colarusso", "colaru000aj-", mapper) == "A.J. Colarusso"
    assert resolve_player_display_name("H. Ford", "wrong-id", mapper) == "H. Ford"


def test_normalizes_box_score_single_initial_display_names(monkeypatch):
    def fake_resolve(name, bref_id):
        if bref_id == "ford--002hen":
            return "Henry Ford"
        return name

    monkeypatch.setattr("baseball_processor.normalization.resolve_player_display_name", fake_resolve)

    game = {
        "metadata": {
            "date": "03/15/2025",
            "away_team": "Virginia",
            "home_team": "California",
            "away_team_score": 10,
            "home_team_score": 8,
        },
        "box_score": {
            "away_batting": [{"name": "H. Ford", "bref_id": "ford--002hen", "ab": 4, "h": 2}],
            "home_batting": [],
            "away_pitching": [],
            "home_pitching": [],
        },
    }

    normalized = normalize_game(game)

    assert normalized["batting"]["away"][0]["name"] == "Henry Ford"
    assert normalized["batting"]["away"][0]["full_name"] == "Henry Ford"


def test_preserves_source_suffix_when_roster_alias_lacks_suffix():
    aliases = {
        ("louisville", "eddie king"): {
            "display_name": "Eddie King",
            "bref_id": "king--000edd",
            "source": "roster",
        }
    }
    game = {
        "metadata": {
            "date": "06/15/2025",
            "away_team": "Arizona",
            "home_team": "Louisville",
            "away_team_score": 3,
            "home_team_score": 8,
        },
        "box_score": {
            "away_batting": [],
            "home_batting": [
                {
                    "name": "Eddie King Jr.",
                    "full_name": "Eddie King",
                    "bref_id": "king--000edd",
                    "ab": 4,
                    "h": 1,
                }
            ],
            "away_pitching": [],
            "home_pitching": [],
        },
    }

    normalized = normalize_game(game, aliases)

    assert normalized["batting"]["home"][0]["name"] == "Eddie King Jr."
    assert normalized["batting"]["home"][0]["full_name"] == "Eddie King Jr."


def test_preserves_suffix_without_leaking_source_caps_jank():
    aliases = {
        ("example", "harris williams"): {
            "display_name": "Harris Williams",
            "bref_id": "willia000har",
            "source": "roster",
        }
    }
    game = {
        "metadata": {
            "date": "03/15/2025",
            "away_team": "Example",
            "home_team": "Other",
            "away_team_score": 5,
            "home_team_score": 2,
        },
        "box_score": {
            "away_batting": [
                {
                    "name": "Harris WILLIAMS III",
                    "full_name": "Harris Williams",
                    "bref_id": "willia000har",
                    "ab": 4,
                    "h": 1,
                }
            ],
            "home_batting": [],
            "away_pitching": [],
            "home_pitching": [],
        },
    }

    normalized = normalize_game(game, aliases)

    assert normalized["batting"]["away"][0]["name"] == "Harris Williams III"


def test_builds_roster_backed_aliases_for_rows_without_bref_ids():
    games = [
        {
            "metadata": {
                "date": "03/15/2025",
                "away_team": "Virginia",
                "home_team": "California",
            },
            "box_score": {
                "away_batting": [],
                "home_batting": [{"name": "J Johnston", "ab": 1}],
                "away_pitching": [],
                "home_pitching": [],
            },
        },
        {
            "metadata": {
                "date": "05/11/2024",
                "away_team": "Staten Island FerryHawks",
                "home_team": "Lancaster Stormers",
                "source": "partner",
            },
            "box_score": {
                "away_batting": [],
                "home_batting": [{"name": "Dunston Jr., S", "ab": 1}],
                "away_pitching": [],
                "home_pitching": [],
            },
        },
    ]

    aliases = build_player_name_aliases(games)

    assert resolve_player_name_alias("J Johnston", "California", aliases) == {
        "display_name": "Jack Johnston",
        "bref_id": "johnst002jac",
        "source": "roster",
    }
    assert resolve_player_name_alias("Dunston Jr., S", "Lancaster Stormers", aliases) == {
        "display_name": "Shawon Dunston",
        "bref_id": "dunsto002sha",
        "source": "roster",
    }


def test_builds_roster_backed_aliases_for_full_names_missing_bref_ids():
    games = [
        {
            "metadata": {
                "date": "02/14/2026",
                "away_team": "Western Illinois",
                "home_team": "San Francisco",
            },
            "box_score": {
                "away_batting": [{"name": "Isaiah Monge", "ab": 4}],
                "home_batting": [{"name": "Wyatt Davis", "ab": 4}],
                "away_pitching": [],
                "home_pitching": [],
            },
        }
    ]

    aliases = build_player_name_aliases(games)

    assert resolve_player_name_alias("Isaiah Monge", "Western Illinois", aliases) == {
        "display_name": "Isaiah Monge",
        "bref_id": "monge-000isa",
        "source": "roster",
    }
    assert resolve_player_name_alias("Wyatt Davis", "San Francisco", aliases) == {
        "display_name": "Wyatt Davis",
        "bref_id": "davis-000wya",
        "source": "roster",
    }


def test_builds_roster_backed_aliases_for_source_name_variants():
    games = [
        {
            "metadata": {
                "date": "04/25/2025",
                "away_team": "LMU",
                "home_team": "Saint Mary's",
            },
            "box_score": {
                "away_batting": [{"name": "Jimmy Pelletier", "ab": 1}],
                "home_batting": [{"name": "Castro, Daniel Gueva", "ab": 0}],
                "away_pitching": [{"name": "Trey Newmann", "ip": "1.0"}],
                "home_pitching": [],
            },
        },
        {
            "metadata": {
                "date": "02/17/2025",
                "away_team": "Sacramento State",
                "home_team": "San Francisco",
            },
            "box_score": {
                "away_batting": [],
                "home_batting": [{"name": "Jimmy Pelletier", "ab": 2}],
                "away_pitching": [],
                "home_pitching": [],
            },
        },
        {
            "metadata": {
                "date": "04/06/2024",
                "away_team": "Arizona",
                "home_team": "California",
            },
            "box_score": {
                "away_batting": [],
                "home_batting": [],
                "away_pitching": [],
                "home_pitching": [{"name": "Trey Newmann", "ip": "3.1"}],
            },
        }
    ]

    aliases = build_player_name_aliases(games)

    assert resolve_player_name_alias("Jimmy Pelletier", "San Francisco", aliases) == {
        "display_name": "Charles-Etienne Pelletier",
        "bref_id": "pellet000cha",
        "source": "roster",
    }
    assert resolve_player_name_alias("Castro, Daniel Gueva", "Saint Mary's", aliases) == {
        "display_name": "Daniel Guevara",
        "bref_id": "guevar003dan",
        "source": "roster",
    }
    assert resolve_player_name_alias("Trey Newmann", "California", aliases) == {
        "display_name": "Trey Newman",
        "bref_id": "newman002tre",
        "source": "roster",
    }


def test_normalizes_mixed_pitching_sections_and_drops_zero_pitcher_batting_artifacts():
    game = {
        "metadata": {
            "date": "04/25/2025",
            "away_team": "LMU",
            "home_team": "Saint Mary's",
            "away_team_score": 3,
            "home_team_score": 8,
        },
        "box_score": {
            "away_batting": [{"name": "Kenji Pallares", "position": "p", "at_bats": 0}],
            "home_batting": [
                {"name": "Castro, Daniel Gueva", "position": "p", "at_bats": 0},
                {"name": "Madrigal, Eddie", "position": "1b", "at_bats": 4, "hits": 2},
            ],
            "away_pitching": [
                {"name": "Kenji Pallares", "innings_pitched": 7.0},
                {"name": "Castro, Daniel Gueva", "innings_pitched": 1.0},
            ],
            "home_pitching": [],
        },
    }

    aliases = build_player_name_aliases([game])
    normalized = normalize_game(game, aliases)

    assert [row["name"] for row in normalized["batting"]["away"]] == []
    assert [row["name"] for row in normalized["batting"]["home"]] == ["Eddie Madrigal"]
    assert [row["name"] for row in normalized["pitching"]["away"]] == ["Kenji Pallares"]
    assert normalized["pitching"]["away"][0]["bref_id"] == "pallar000ken"
    assert [row["name"] for row in normalized["pitching"]["home"]] == ["Daniel Guevara"]
    assert normalized["pitching"]["home"][0]["bref_id"] == "guevar003dan"


def test_drops_zero_pitcher_batting_artifact_when_pitcher_uses_nickname_alias():
    game = {
        "metadata": {
            "date": "03/30/2024",
            "away_team": "Santa Clara",
            "home_team": "San Francisco",
        },
        "box_score": {
            "away_batting": [
                {"name": "BARRETT, Gabriel", "position": "p", "at_bats": 0},
                {"name": "BERRING, JonJon", "position": "lf", "at_bats": 4, "hits": 1},
            ],
            "home_batting": [],
            "away_pitching": [],
            "home_pitching": [
                {
                    "name": "BARRETT, Gabriel",
                    "full_name": "Gabe Barrett",
                    "bref_id": "barret000gab",
                    "innings_pitched": 2.2,
                    "strikeouts": 1,
                }
            ],
        },
    }

    normalized = normalize_game(game, build_player_name_aliases([game]))

    assert [row["name"] for row in normalized["batting"]["away"]] == ["JonJon Berring"]
    assert [row["name"] for row in normalized["pitching"]["home"]] == ["Gabe Barrett"]


def test_drops_zero_offense_pitcher_batting_artifact_with_fielding_stats():
    game = {
        "metadata": {
            "date": "03/14/2025",
            "away_team": "Virginia",
            "home_team": "California",
        },
        "box_score": {
            "home_batting": [
                {"name": "Real Batter", "position": "1b", "at_bats": 4, "hits": 2},
                {
                    "name": "Pitcher Fielding Row",
                    "position": "p",
                    "at_bats": 0,
                    "runs": 0,
                    "hits": 0,
                    "rbi": 0,
                    "walks": 0,
                    "strikeouts": 0,
                    "assists": 2,
                },
            ],
            "home_pitching": [
                {"name": "Pitcher Fielding Row", "innings_pitched": 1.0, "hits": 0},
            ],
        },
    }

    normalized = normalize_game(game)

    assert [row["name"] for row in normalized["batting"]["home"]] == ["Real Batter"]


def test_drops_zero_contribution_batting_artifacts_without_stable_identity():
    game = {
        "metadata": {
            "date": "06/15/2026",
            "away_team": "Georgia",
            "home_team": "Oklahoma",
        },
        "box_score": {
            "away_batting": [],
            "home_batting": [
                {
                    "name": "Scott Newman",
                    "position": "cf",
                    "at_bats": 0,
                    "runs": 0,
                    "hits": 0,
                    "rbi": 0,
                    "walks": 0,
                    "strikeouts": 0,
                    "put_outs": 0,
                    "assists": 0,
                    "left_on_base": 0,
                },
                {"name": "Real Batter", "position": "rf", "at_bats": 4, "hits": 2},
                {"name": "Known Defender", "position": "lf", "bref_id": "known000def", "at_bats": 0},
            ],
            "away_pitching": [],
            "home_pitching": [],
        },
    }

    normalized = normalize_game(game)

    assert [row["name"] for row in normalized["batting"]["home"]] == ["Real Batter", "Known Defender"]


def test_dedupes_batting_rows_by_roster_identity_without_merging_siblings():
    game = {
        "metadata": {
            "date": "03/02/2025",
            "away_team": "San Jose State",
            "home_team": "San Francisco",
            "away_team_score": 3,
            "home_team_score": 7,
        },
        "box_score": {
            "away_batting": [
                {"name": "ja. Lewis", "number": "3", "ab": 1, "h": 1, "bb": 1, "k": 0},
                {"name": "je. Lewis", "number": "0", "ab": 4, "h": 0, "bb": 0, "k": 0},
                {"name": "LEWIS, Jeriah", "at_bats": 4, "hits": 0, "walks": 0, "strikeouts": 2, "bref_id": "lewis-008jer"},
                {"name": "LEWIS, Jared", "position": "dh", "at_bats": 1, "hits": 1, "walks": 1, "strikeouts": 0, "bref_id": "lewis-001jar"},
            ],
            "home_batting": [],
            "away_pitching": [],
            "home_pitching": [],
        },
    }

    aliases = build_player_name_aliases([game])
    normalized = normalize_game(game, aliases)

    rows = normalized["batting"]["away"]
    assert [(row["name"], row["bref_id"], row.get("position", ""), row["AB"], row["SO"]) for row in rows] == [
        ("Jared Lewis", "lewis-001jar", "dh", 1, 0),
        ("Jeriah Lewis", "lewis-008jer", "", 4, 2),
    ]


def test_normalizes_ncaa_pdf_shape_aliases():
    game = {
        "metadata": {
            "date": "03/15/2024",
            "away_team": "Texas",
            "home_team": "Oklahoma",
            "away_team_score": 5,
            "home_team_score": 3,
            "venue": "Example Field",
        },
        "box_score": {
            "away_batting": [{"name": "Batter One", "ab": 4, "h": 2, "so": 1, "hr": 1}],
            "home_batting": [],
            "away_pitching": [{"name": "Pitcher One", "innings_pitched": 9.0, "k": 10, "h": 0}],
            "home_pitching": [],
        },
    }

    normalized = normalize_game(game)

    assert normalized["source"] == "ncaa"
    assert normalized["game_id"] == "ncaa_pdf_20240315_texas_at_oklahoma_5_3"
    assert normalized["basic_info"]["away_score_value"] == 5
    assert normalized["batting"]["away"][0]["SO"] == 1
    assert normalized["batting"]["away"][0]["HR"] == 1
    assert normalized["pitching"]["away"][0]["IP"] == 9.0
    assert normalized["pitching"]["away"][0]["SO"] == 10


def test_normalizes_venue_aliases():
    game = {
        "metadata": {
            "date": "06/16/2025",
            "away_team": "UCLA",
            "home_team": "LSU",
            "away_team_score": 5,
            "home_team_score": 9,
            "venue": "Charles Schwab Field (Omaha, Neb.)",
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
    }

    normalized = normalize_game(game)

    assert normalized["basic_info"]["venue"] == "Charles Schwab Field Omaha"


def test_normalizes_source_specific_venue_aliases():
    assert normalize_venue_name("Phoenix Muni Stadium") == "Phoenix Municipal Stadium"
    assert normalize_venue_name("Br. Ronald Gallagher") == "Louis Guisto Field at Br. Ronald Gallagher Stadium"
    assert normalize_venue_name("Davenport Field") == "Disharoon Park"
    assert normalize_venue_name("Charles Schwab Stad. (Omaha, Neb.)") == "Charles Schwab Field Omaha"


def test_resolves_known_api_only_venue_overrides():
    game = {
        "metadata": {
            "source": "ncaa_api",
            "game_id": "6416348",
            "date": "02/22/2025",
            "away_team": "Rutgers",
            "home_team": "Grand Canyon",
            "away_team_score": 3,
            "home_team_score": 10,
            "venue": "",
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
    }

    normalized = normalize_game(game)

    assert normalized["basic_info"]["venue"] == "GCU Ballpark"


def test_normalizes_milb_shape_and_boolean_decision():
    game = {
        "format": "milb_api",
        "metadata": {
            "source": "milb",
            "date": "2025-05-01",
            "date_yyyymmdd": "20250501",
            "away_team": "Away Club",
            "home_team": "Home Club",
            "away_team_score": 4,
            "home_team_score": 2,
            "game_pk": 123456,
            "sport_level": {"home": "Triple-A", "away": "Triple-A"},
            "league": {"home": "Pacific Coast League", "away": "Pacific Coast League"},
        },
        "box_score": {
            "away_batting": [{"name": "Pro Hitter", "ab": 5, "h": 3, "k": 0, "doubles": 2}],
            "home_batting": [],
            "away_pitching": [{"name": "Pro Pitcher", "ip": "6.0", "k": 8, "bf": 22, "win": True}],
            "home_pitching": [],
        },
    }

    normalized = normalize_game(game)

    assert normalized["source"] == "milb"
    assert normalized["game_id"] == "milb_123456"
    assert normalized["batting"]["away"][0]["2B"] == 2
    assert normalized["pitching"]["away"][0]["batters_faced"] == 22
    assert normalized["pitching"]["away"][0]["decision"] == "W"


def test_partner_source_takes_precedence_over_milb_api_format_for_game_id():
    game = {
        "format": "milb_api",
        "metadata": {
            "source": "partner",
            "date": "2026-06-01",
            "date_yyyymmdd": "20260601",
            "away_team": "Aberdeen IronBirds",
            "home_team": "Trenton Thunder",
            "away_team_score": 3,
            "home_team_score": 4,
            "game_pk": 999999,
            "sport_level": {"home": "College Baseball", "away": "College Baseball"},
            "league": {"home": "MLB Draft League", "away": "MLB Draft League"},
        },
        "box_score": {"away_batting": [], "home_batting": [], "away_pitching": [], "home_pitching": []},
    }

    normalized = normalize_game(game)

    assert normalized["source"] == "partner"
    assert normalized["basic_info"]["level"] == "Independent"
    assert normalized["basic_info"]["league"] == "MLB Draft League"
    assert normalized["game_id"] == "partner_mlb_draft_league_999999"
