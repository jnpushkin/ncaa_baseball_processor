"""Tests for Excel/website dataframe preparation."""

from baseball_processor.excel.workbook_generator import create_milb_batters


def test_create_milb_batters_calculates_partner_rate_stats_from_xbh():
    games = [
        {
            "metadata": {
                "source": "partner",
                "date": "5/20/2026",
                "away_team": "Missoula PaddleHeads",
                "home_team": "Oakland Ballers",
                "away_team_score": 8,
                "home_team_score": 13,
                "league": {"home": "Pioneer League", "away": "Pioneer League"},
                "sport_level": {"home": "Partner", "away": "Partner"},
            },
            "box_score": {
                "away_batting": [],
                "home_batting": [
                    {
                        "name": "T.J. McKenzie",
                        "ab": 3,
                        "r": 4,
                        "h": 3,
                        "rbi": 6,
                        "bb": 1,
                        "k": 0,
                        "doubles": 0,
                        "triples": 0,
                        "hr": 3,
                        "sb": 0,
                    }
                ],
                "away_pitching": [],
                "home_pitching": [],
            },
        }
    ]

    df = create_milb_batters(games)
    row = df.iloc[0]

    assert row["AVG"] == "1.000"
    assert row["OBP"] == "1.000"
    assert row["SLG"] == "4.000"
    assert row["OPS"] == "5.000"
