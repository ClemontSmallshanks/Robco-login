"""Tests for the word list module."""

from app.game.word_list import WORDS, get_words_by_length


class TestWordList:
    def test_all_words_correct_length(self):
        for word in WORDS:
            assert 7 <= len(word) <= 12, f"Word '{word}' has length {len(word)}"

    def test_all_words_uppercase(self):
        for word in WORDS:
            assert word == word.upper(), f"Word '{word}' is not uppercase"

    def test_all_words_alphabetic(self):
        for word in WORDS:
            assert word.isalpha(), f"Word '{word}' contains non-alpha chars"

    def test_no_duplicates(self):
        assert len(WORDS) == len(set(WORDS)), "Duplicate words found"

    def test_minimum_word_count(self):
        # We need enough words for puzzle generation
        assert len(WORDS) >= 50, f"Only {len(WORDS)} words, need at least 50"

    def test_get_words_by_length_12(self):
        words = get_words_by_length(12)
        assert len(words) > 0
        assert all(len(w) == 12 for w in words)

    def test_get_words_invalid_length(self):
        words = get_words_by_length(3)
        assert len(words) == 0

    def test_enough_words_per_length(self):
        # The finalized game uses strictly length 12
        for length in [12]:
            words = get_words_by_length(length)
            assert len(words) >= 16, (
                f"Length {length} has only {len(words)} words, need at least 16 for num_candidates=16"
            )
