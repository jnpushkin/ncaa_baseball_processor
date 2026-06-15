"""Tests for player crossover identity resolution."""

from player_crossover import PlayerCrossover


def test_partial_name_match_does_not_merge_different_first_names():
    # "Jake Jackson" (with a register id) and "Jaren Jackson" (no id) share a
    # last name and first initial but are different people -> separate records.
    pc = PlayerCrossover()
    jake = pc._get_or_create_player("Jake Jackson", bref_id="jackso009jak")
    jaren = pc._get_or_create_player("Jaren Jackson")  # no id (e.g. partner box)
    assert jake != jaren


def test_partial_name_match_still_links_initial_to_full_name():
    # The intended use case: "Johnson, K" should link to "Kyle Johnson".
    pc = PlayerCrossover()
    kyle = pc._get_or_create_player("Kyle Johnson", bref_id="johnso001kyl")
    initial = pc._get_or_create_player("Johnson, K")  # initial form, no id
    assert kyle == initial
