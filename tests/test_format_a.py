"""Tests for format_a PDF box-score parsing helpers."""

import parsers
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


def test_parse_one_page_format_a_no_num_statcrew_pdf(monkeypatch):
    text = "\n".join(
        [
            "2025 Virginia Baseball",
            "Virginia at California",
            "Mar 14, 2025 at Berkeley, CA (Stu Gordon Stadium)",
            "Virginia 1 (10-6,1-3 ACC) California 6 (9-8,2-2 ACC)",
            "Player ab r h rbi bb so po a lob Player ab r h rbi bb so po a lob",
            "Harrison Didawick lf 3 0 0 0 0 2 5 0 3 Moutzouridis ss 3 1 0 0 1 0 3 4 0",
            "James Nunnallee dh 2 1 0 0 0 0 0 0 0 French,J rf/lf 4 1 2 0 0 1 0 0 0",
            "Totals 28 1 4 1 5 8 24 8 10 Totals 32 6 8 5 3 8 27 8 6",
            "Score by Innings 1 2 3 4 5 6 7 8 9 R H E",
            "Virginia 0 0 0 0 1 0 0 0 0 1 4 2",
            "California 0 3 0 2 0 1 0 0 X 6 8 0",
            "Virginia ip h r er bb so ab bf np California ip h r er bb so ab bf np",
            "Jay Woolfolk 5.0 6 5 4 3 4 20 24 86 Turkington,A 6.2 3 1 1 3 7 21 28 107",
        ]
    )

    class FakePage:
        width = 612

        def extract_text(self):
            return text

        def extract_words(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(parsers.pdfplumber, "open", lambda _path: FakePdf())

    parsed = parsers.parse_ncaab_pdf("unused.pdf")

    assert parsed["format"] == "format_a_no_num"
    assert parsed["box_score"]["home_batting"][0]["name"] == "Moutzouridis"
    assert parsed["box_score"]["home_batting"][1]["name"] == "French,J"
    assert parsed["box_score"]["home_batting"][1]["position"] == "rf/lf"
    assert parsed["box_score"]["home_pitching"][0]["name"] == "Turkington,A"
    assert parsed["box_score"]["home_pitching"][0]["at_bats"] == 21
    assert parsed["box_score"]["home_pitching"][0]["batters_faced"] == 28
