"""Tests for the likeness calculation module."""

from app.game.likeness import calculate_likeness


class TestCalculateLikeness:
    def test_exact_match(self):
        assert calculate_likeness("REACTOR", "REACTOR") == 7

    def test_no_match(self):
        assert calculate_likeness("AAAAAAA", "ZZZZZZZ") == 0

    def test_partial_match(self):
        # REACTOR vs REACTED: R-E-A-C-T match (5), E vs O differ, D vs R differ
        assert calculate_likeness("REACTOR", "REACTED") == 5

    def test_single_char_match(self):
        assert calculate_likeness("ABCDEFG", "AXYZXYZ") == 1

    def test_case_insensitive(self):
        assert calculate_likeness("reactor", "REACTOR") == 7

    def test_mixed_case(self):
        assert calculate_likeness("ReAcToR", "rEaCtOr") == 7

    def test_empty_strings(self):
        assert calculate_likeness("", "") == 0

    def test_single_character(self):
        assert calculate_likeness("A", "A") == 1
        assert calculate_likeness("A", "B") == 0

    def test_different_lengths_uses_shorter(self):
        # zip stops at shorter string
        assert calculate_likeness("ABC", "ABCD") == 3

    def test_all_same_position_matches(self):
        assert calculate_likeness("TERMINAL", "TERMINAL") == 8

    def test_no_position_matches_despite_same_letters(self):
        # ABCD vs DCBA — no positional matches
        assert calculate_likeness("ABCD", "DCBA") == 0

    def test_typical_fallout_scenario(self):
        # SECURITY vs TERMINAL
        # S!=T, E!=E(match), C!=R, U!=M, R!=I, I!=N, T!=A, Y!=L
        # Position 1: E==E → 1 match
        assert calculate_likeness("SECURITY", "TERMINAL") == 1
