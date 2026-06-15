"""Tests for format_a PDF box-score parsing helpers."""

from parsers.format_a import _parse_score_by_innings

HEADER = "Score by Innings 1 2 3 4 5 6 7 8 9 R H E"


def test_line_score_assigned_by_row_order_not_team_name():
    # Away team is the first row, home the second -- regardless of team name.
    # (Previously hardcoded to VMI/Virginia, which dropped every other matchup.)
    rows = [
        "Virginia 0 1 0 2 0 0 0 2 0 5 9 1",
        "Florida 0 0 0 0 0 0 4 0 2 6 8 0",
    ]
    away, home = _parse_score_by_innings(HEADER, rows)
    assert sum(away) == 5
    assert sum(home) == 6


def test_line_score_handles_multiword_names_and_x_marker():
    rows = [
        "Troy 0 1 3 0 0 0 1 0 0 5 9 2",
        "West Virginia 1 2 1 1 0 0 0 2 X 7 9 0",  # home didn't bat in 9th
    ]
    away, home = _parse_score_by_innings(HEADER, rows)
    assert away == [0, 1, 3, 0, 0, 0, 1, 0, 0]
    assert home == [1, 2, 1, 1, 0, 0, 0, 2, 0]


def test_line_score_handles_extra_innings():
    header = "Score by Innings 1 2 3 4 5 6 7 8 9 10 R H E"
    rows = [
        "North Carolina 0 0 0 0 1 0 0 0 0 1 2 7 0",
        "LSU 0 0 0 0 1 0 0 0 0 0 1 5 1",
    ]
    away, home = _parse_score_by_innings(header, rows)
    assert sum(away) == 2
    assert sum(home) == 1
    assert len(away) == 10 and len(home) == 10
