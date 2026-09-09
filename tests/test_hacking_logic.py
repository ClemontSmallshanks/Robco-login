import unittest
from unittest.mock import MagicMock
from app.game.game_state import GameState, GamePhase, GuessResult
from app.game.puzzle_generator import HexDumpLayout, Puzzle, WordPosition

class TestHackingLogic(unittest.TestCase):
    def setUp(self):
        self.puzzle = Puzzle(
            candidates=[
                "PASSWORD1234",
                "INCORRECT123",
                "ANOTHERWRONG",
                "FAILWORD1234",
                "LASTCHANCE12",
            ],
            word_length=12,
            correct_password="PASSWORD1234",
            layout=HexDumpLayout(
                left_addresses=["0x0000"] * 17,
                right_addresses=["0x0010"] * 17,
                left_column=["." * 12] * 17,
                right_column=["." * 12] * 17,
                word_positions=[
                    WordPosition("PASSWORD1234", 0, 0, 0),
                    WordPosition("INCORRECT123", 0, 1, 0),
                    WordPosition("ANOTHERWRONG", 0, 2, 0),
                    WordPosition("FAILWORD1234", 0, 3, 0),
                    WordPosition("LASTCHANCE12", 0, 4, 0),
                ],
                bracket_positions=[]
            )
        )
        
        # Initialize game state with 4 attempts
        self.game = GameState(max_attempts=4)
        self.game._puzzle = self.puzzle
        self.game._phase = GamePhase.PLAYING

    def test_incorrect_word_with_attempts_remaining(self):
        """TEST 1: Select an incorrect word with attempts remaining."""
        # Initial attempts should be 4
        self.assertEqual(self.game.attempts_remaining, 4)
        self.assertEqual(self.game.phase, GamePhase.PLAYING)
        
        # Guess an incorrect word
        result = self.game.guess("INCORRECT123")
        
        # Verify attempt decrement and state continuity
        self.assertFalse(result.is_correct)
        self.assertEqual(self.game.attempts_remaining, 3)
        self.assertEqual(self.game.phase, GamePhase.PLAYING)
        self.assertEqual(result.likeness_total, 12)

    def test_incorrect_word_final_attempt(self):
        """TEST 2: Select an incorrect word when it consumes the final attempt."""
        # Burn 3 attempts
        self.game.guess("INCORRECT123")
        self.game.guess("ANOTHERWRONG")
        self.game.guess("FAILWORD1234")
        
        self.assertEqual(self.game.attempts_remaining, 1)
        self.assertEqual(self.game.phase, GamePhase.PLAYING)
        
        # Guess the 4th incorrect word
        result = self.game.guess("LASTCHANCE12")
        
        # Verify lockout
        self.assertFalse(result.is_correct)
        self.assertEqual(self.game.attempts_remaining, 0)
        self.assertEqual(self.game.phase, GamePhase.LOCKOUT)

    def test_correct_word_multiple_attempts(self):
        """TEST 3: Select the correct word with multiple attempts remaining."""
        self.assertEqual(self.game.attempts_remaining, 4)
        
        # Guess the correct word
        result = self.game.guess("PASSWORD1234")
        
        # Verify success without attempt decrement
        self.assertTrue(result.is_correct)
        self.assertEqual(self.game.attempts_remaining, 4) # Should NOT decrement
        self.assertEqual(self.game.phase, GamePhase.AUTHENTICATED) # NOT LOCKOUT

    def test_correct_word_one_attempt(self):
        """TEST 4: Select the correct word when only ONE attempt remains."""
        # Burn 3 attempts
        self.game.guess("INCORRECT123")
        self.game.guess("ANOTHERWRONG")
        self.game.guess("FAILWORD1234")
        
        self.assertEqual(self.game.attempts_remaining, 1)
        
        # Guess the correct word on the final attempt
        result = self.game.guess("PASSWORD1234")
        
        # Verify SUCCESS, NOT LOCKOUT, and NO decrement
        self.assertTrue(result.is_correct)
        self.assertEqual(self.game.attempts_remaining, 1) # Should NOT decrement
        self.assertEqual(self.game.phase, GamePhase.AUTHENTICATED)

    def test_direct_password_entry_flow(self):
        """TEST 5 & 6: Direct password entry logic in UI."""
        # This tests the UI logic separation in HackingState._process_word_deferred
        # We can simulate the branching logic directly.
        
        correct_minigame_word = "PASSWORD1234"
        incorrect_minigame_word = "INCORRECT123"
        custom_real_password = "MyRealLinuxPassword"
        custom_fake_password = "WrongPassword"
        
        # Test 5: Custom correct password (bypasses minigame logic)
        self.assertFalse(self.game.is_valid_candidate(custom_real_password))
        
        # Test 6: Custom incorrect password (bypasses minigame logic)
        self.assertFalse(self.game.is_valid_candidate(custom_fake_password))
        
        # Test 3/4: Minigame correct word (hits minigame logic)
        self.assertTrue(self.game.is_valid_candidate(correct_minigame_word))
        
        # Test 1/2: Minigame incorrect word (hits minigame logic)
        self.assertTrue(self.game.is_valid_candidate(incorrect_minigame_word))

if __name__ == '__main__':
    unittest.main()
