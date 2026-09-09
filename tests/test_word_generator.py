"""Tests for the word generator and puzzle randomness."""
import unittest

from app.game.puzzle_generator import generate_puzzle
from app.game.word_list import WORDS, get_words_by_length

class TestWordGenerator(unittest.TestCase):
    def test_word_length_strictly_12(self):
        """Verify that all generated candidates are exactly 12 letters."""
        puzzle = generate_puzzle(min_word_length=12, max_word_length=12, num_candidates=16)
        for word in puzzle.candidates:
            self.assertEqual(len(word), 12, f"Word '{word}' is not 12 letters long!")

    def test_candidates_unique_in_session(self):
        """Verify that candidates within one hacking session are unique."""
        puzzle = generate_puzzle(min_word_length=12, max_word_length=12, num_candidates=16)
        self.assertEqual(len(puzzle.candidates), len(set(puzzle.candidates)), "Duplicate candidates found in session!")
        self.assertEqual(len(puzzle.candidates), 16, "Not enough candidates generated.")

    def test_repeated_sessions_different_sets(self):
        """Verify that repeated hacking sessions produce different candidate sets."""
        puzzle1 = generate_puzzle(min_word_length=12, max_word_length=12, num_candidates=16)
        puzzle2 = generate_puzzle(min_word_length=12, max_word_length=12, num_candidates=16)
        
        # In a 250+ word pool, the probability of selecting the exact same 16 words is astronomically low.
        # We ensure they are not identical. Overlap is acceptable and mathematically expected, but not identical.
        self.assertNotEqual(set(puzzle1.candidates), set(puzzle2.candidates), "Two successive sessions generated identical candidate sets!")

    def test_correct_password_in_candidates(self):
        """Verify that the correct password remains one of the generated candidates."""
        puzzle = generate_puzzle(min_word_length=12, max_word_length=12, num_candidates=16)
        self.assertIn(puzzle.correct_password, puzzle.candidates, "Correct password is not in the generated candidates!")

    def test_pool_size(self):
        """Verify that the 12-letter word pool is sufficiently large."""
        pool = get_words_by_length(12)
        self.assertGreater(len(pool), 150, "12-letter word pool is too small to ensure randomness!")

if __name__ == '__main__':
    unittest.main()
