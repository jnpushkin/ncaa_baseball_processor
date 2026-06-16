"""Tests for box-score notes (extra-base hit) extraction."""

from parsers.game_notes import extract_game_notes


def _players(entries):
    return [e["player"] for e in entries]


def test_extracts_full_semicolon_separated_list():
    text = "2B: Aiden Robbins (1); Ethan Mendoza (1); Adrian Rodriguez (2)"
    notes = extract_game_notes(text)
    assert _players(notes["doubles"]) == ["Aiden Robbins", "Ethan Mendoza", "Adrian Rodriguez"]


def test_extracts_labels_that_appear_mid_line_two_column_box_score():
    # pdfplumber merges the two note columns onto one line, so a stat label can
    # follow the other column's "(count) ". All of these must be captured.
    text = (
        "SB: Justin Lebron (1) 2B: Aiden Robbins (1); Ethan Mendoza (1); Adrian Rodriguez (2)\n"
        "HBP: Justin Lebron (1) 3B: Adrian Rodriguez (1)\n"
        "E: Justin Lebron (1) HR: Anthony Pack Jr. (1); Adrian Rodriguez (1)"
    )
    notes = extract_game_notes(text)
    assert "Adrian Rodriguez" in _players(notes["doubles"])
    assert _players(notes["triples"]) == ["Adrian Rodriguez"]
    assert "Adrian Rodriguez" in _players(notes["home_runs"])
    # Adrian Rodriguez has a 2B, 3B, and HR here -> the makings of a cycle.


def test_skips_base_umpire_names_without_counts():
    # Umpire line lists "2B: Name" / "3B: Name" without a "(count)" -> ignored.
    text = "Umpires - HP: Joe Smith; 1B: Bob Jones; 2B: Al Green; 3B: Cy Young"
    notes = extract_game_notes(text)
    assert notes["doubles"] == []
    assert notes["triples"] == []
