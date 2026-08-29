"""Tests for the bracket tricks module."""

from app.game.bracket_tricks import (
    BracketEffect,
    apply_allowance_replenishment,
    apply_dud_removal,
    find_bracket_pairs,
)


class TestFindBracketPairs:
    def test_simple_parens(self):
        pairs = find_bracket_pairs("abc(def)ghi")
        assert len(pairs) == 1
        assert pairs[0] == (3, 7, "(", ")")

    def test_simple_brackets(self):
        pairs = find_bracket_pairs("[abc]")
        assert len(pairs) == 1
        assert pairs[0] == (0, 4, "[", "]")

    def test_simple_braces(self):
        pairs = find_bracket_pairs("{xy}")
        assert len(pairs) == 1
        assert pairs[0] == (0, 3, "{", "}")

    def test_angle_brackets(self):
        pairs = find_bracket_pairs("<ab>")
        assert len(pairs) == 1
        assert pairs[0] == (0, 3, "<", ">")

    def test_multiple_pairs(self):
        pairs = find_bracket_pairs("(a)[b]{c}<d>")
        assert len(pairs) == 4

    def test_no_brackets(self):
        pairs = find_bracket_pairs("abcdefg")
        assert len(pairs) == 0

    def test_unmatched_opener(self):
        pairs = find_bracket_pairs("abc(def")
        assert len(pairs) == 0

    def test_empty_string(self):
        pairs = find_bracket_pairs("")
        assert len(pairs) == 0

    def test_adjacent_pairs(self):
        pairs = find_bracket_pairs("(a)(b)")
        assert len(pairs) == 2

    def test_mixed_junk(self):
        pairs = find_bracket_pairs("!@#(abc)$%^")
        assert len(pairs) == 1
        assert pairs[0][2] == "("
        assert pairs[0][3] == ")"


class TestApplyDudRemoval:
    def test_removes_incorrect_word(self):
        candidates = ["REACTOR", "NETWORK", "PROGRAM"]
        removed = set()
        victim = apply_dud_removal(candidates, "REACTOR", removed)
        assert victim is not None
        assert victim != "REACTOR"
        assert victim in removed

    def test_never_removes_correct(self):
        candidates = ["REACTOR", "NETWORK"]
        removed = set()
        for _ in range(100):
            removed_copy = removed.copy()
            victim = apply_dud_removal(candidates, "REACTOR", removed_copy)
            if victim is not None:
                assert victim != "REACTOR"
                removed = removed_copy

    def test_no_duds_returns_none(self):
        candidates = ["REACTOR"]
        removed = set()
        victim = apply_dud_removal(candidates, "REACTOR", removed)
        assert victim is None

    def test_all_duds_removed(self):
        candidates = ["REACTOR", "NETWORK", "PROGRAM"]
        removed: set[str] = set()
        # Remove all duds
        for _ in range(10):
            v = apply_dud_removal(candidates, "REACTOR", removed)
            if v is None:
                break
        assert "NETWORK" in removed
        assert "PROGRAM" in removed
        assert "REACTOR" not in removed

    def test_already_removed_not_picked_again(self):
        candidates = ["REACTOR", "NETWORK", "PROGRAM"]
        removed = {"NETWORK"}
        victim = apply_dud_removal(candidates, "REACTOR", removed)
        assert victim == "PROGRAM"


class TestApplyAllowanceReplenishment:
    def test_restores_to_max(self):
        assert apply_allowance_replenishment(1, 4) == 4

    def test_already_at_max(self):
        assert apply_allowance_replenishment(4, 4) == 4

    def test_zero_attempts(self):
        assert apply_allowance_replenishment(0, 4) == 4
