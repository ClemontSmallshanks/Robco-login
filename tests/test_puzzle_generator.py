"""Tests for the puzzle generator module."""

import random

from app.game.puzzle_generator import generate_puzzle


class TestPuzzleGenerator:
    def test_all_candidates_same_length(self):
        puzzle = generate_puzzle()
        lengths = {len(w) for w in puzzle.candidates}
        assert len(lengths) == 1, f"Mixed lengths: {lengths}"

    def test_word_length_matches(self):
        puzzle = generate_puzzle()
        assert all(len(w) == puzzle.word_length for w in puzzle.candidates)

    def test_correct_password_in_candidates(self):
        puzzle = generate_puzzle()
        assert puzzle.correct_password in puzzle.candidates

    def test_no_duplicate_candidates(self):
        puzzle = generate_puzzle()
        assert len(puzzle.candidates) == len(set(puzzle.candidates))

    def test_candidate_count(self):
        puzzle = generate_puzzle(num_candidates=8)
        assert len(puzzle.candidates) == 8

    def test_default_candidate_count(self):
        puzzle = generate_puzzle()
        assert len(puzzle.candidates) == 12

    def test_word_length_in_range(self):
        for _ in range(20):
            puzzle = generate_puzzle(min_word_length=7, max_word_length=10)
            assert 7 <= puzzle.word_length <= 10

    def test_layout_has_lines(self):
        puzzle = generate_puzzle()
        assert len(puzzle.layout.left_column) > 0
        assert len(puzzle.layout.right_column) > 0

    def test_layout_columns_same_length(self):
        puzzle = generate_puzzle()
        assert len(puzzle.layout.left_column) == len(puzzle.layout.right_column)

    def test_layout_has_addresses(self):
        puzzle = generate_puzzle()
        assert len(puzzle.layout.left_addresses) == len(puzzle.layout.left_column)
        assert len(puzzle.layout.right_addresses) == len(puzzle.layout.right_column)

    def test_addresses_are_hex(self):
        puzzle = generate_puzzle()
        for addr in puzzle.layout.left_addresses + puzzle.layout.right_addresses:
            assert addr.startswith("0x")

    def test_word_positions_exist(self):
        puzzle = generate_puzzle()
        assert len(puzzle.layout.word_positions) == len(puzzle.candidates)

    def test_word_positions_contain_all_candidates(self):
        puzzle = generate_puzzle()
        positioned_words = {wp.word for wp in puzzle.layout.word_positions}
        assert positioned_words == set(puzzle.candidates)

    def test_words_embedded_in_lines(self):
        puzzle = generate_puzzle()
        for wp in puzzle.layout.word_positions:
            if wp.column == 0:
                line = puzzle.layout.left_column[wp.row]
            else:
                line = puzzle.layout.right_column[wp.row]
            embedded = line[wp.start_col : wp.start_col + len(wp.word)]
            assert embedded == wp.word, (
                f"Word '{wp.word}' not found at position {wp.start_col} "
                f"in line '{line}'"
            )

    def test_bracket_positions_exist(self):
        # Run multiple times since bracket placement is probabilistic
        found_brackets = False
        for _ in range(20):
            puzzle = generate_puzzle()
            if len(puzzle.layout.bracket_positions) > 0:
                found_brackets = True
                break
        assert found_brackets, "No bracket pairs generated in 20 attempts"

    def test_reproducible_with_seed(self):
        random.seed(42)
        p1 = generate_puzzle()
        random.seed(42)
        p2 = generate_puzzle()
        assert p1.candidates == p2.candidates
        assert p1.correct_password == p2.correct_password
