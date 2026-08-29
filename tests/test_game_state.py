"""Tests for the game state machine."""

import pytest

from app.game.game_state import GamePhase, GameState


class TestGameStateTransitions:
    def test_initial_phase_is_boot(self):
        gs = GameState()
        assert gs.phase == GamePhase.BOOT

    def test_advance_to_menu(self):
        gs = GameState()
        gs.advance_to_menu()
        assert gs.phase == GamePhase.MENU

    def test_start_game_from_menu(self):
        gs = GameState()
        gs.advance_to_menu()
        puzzle = gs.start_game()
        assert gs.phase == GamePhase.PLAYING
        assert puzzle is not None
        assert len(puzzle.candidates) > 0

    def test_start_game_not_from_boot(self):
        gs = GameState()
        with pytest.raises(RuntimeError):
            gs.start_game()

    def test_correct_guess_authenticates(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        result = gs.guess(gs.correct_password)
        assert result.is_correct
        assert gs.phase == GamePhase.AUTHENTICATED
        assert gs.is_authenticated

    def test_set_authenticated(self):
        gs = GameState()
        gs.set_authenticated()
        assert gs.is_authenticated


class TestGameStateAttempts:
    def test_initial_attempts(self):
        gs = GameState(initial_attempts=4)
        gs.advance_to_menu()
        gs.start_game()
        assert gs.attempts_remaining == 4

    def test_wrong_guess_decrements(self):
        gs = GameState(initial_attempts=4)
        gs.advance_to_menu()
        gs.start_game()
        # Pick a wrong candidate
        wrong = [w for w in gs.candidates if w != gs.correct_password][0]
        result = gs.guess(wrong)
        assert not result.is_correct
        assert gs.attempts_remaining == 3

    def test_lockout_after_all_attempts(self):
        gs = GameState(initial_attempts=4)
        gs.advance_to_menu()
        gs.start_game()

        wrongs = [w for w in gs.candidates if w != gs.correct_password]
        for i, wrong in enumerate(wrongs[:4]):
            if gs.is_locked_out:
                break
            gs.guess(wrong)

        assert gs.is_locked_out
        assert gs.phase == GamePhase.LOCKOUT
        assert gs.attempts_remaining <= 0

    def test_cannot_guess_after_lockout(self):
        gs = GameState(initial_attempts=1)
        gs.advance_to_menu()
        gs.start_game()
        wrong = [w for w in gs.candidates if w != gs.correct_password][0]
        gs.guess(wrong)
        assert gs.is_locked_out
        with pytest.raises(RuntimeError):
            gs.guess(wrong)

    def test_force_lockout(self):
        gs = GameState()
        gs.force_lockout()
        assert gs.is_locked_out


class TestGameStateGuessing:
    def test_invalid_candidate_raises(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        with pytest.raises(ValueError):
            gs.guess("ZZZZZZZZZ")

    def test_guess_result_likeness(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        result = gs.guess(gs.correct_password)
        assert result.likeness == result.likeness_total

    def test_guess_history_tracked(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        gs.guess(gs.correct_password)
        assert len(gs.guess_history) == 1
        assert gs.guess_history[0].is_correct

    def test_case_insensitive_guess(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        result = gs.guess(gs.correct_password.lower())
        assert result.is_correct


class TestGameStateBrackets:
    def test_use_bracket(self):
        gs = GameState()
        gs.advance_to_menu()
        puzzle = gs.start_game()
        if puzzle.layout.bracket_positions:
            pair_id = puzzle.layout.bracket_positions[0].pair_id
            result = gs.use_bracket(pair_id)
            assert result is not None

    def test_bracket_single_use(self):
        gs = GameState()
        gs.advance_to_menu()
        puzzle = gs.start_game()
        if puzzle.layout.bracket_positions:
            pair_id = puzzle.layout.bracket_positions[0].pair_id
            result1 = gs.use_bracket(pair_id)
            result2 = gs.use_bracket(pair_id)
            assert result1 is not None
            assert result2 is None

    def test_bracket_not_in_playing(self):
        gs = GameState()
        result = gs.use_bracket(0)
        assert result is None

    def test_removed_duds_tracked(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        # Simulate manual dud removal
        initial_count = len(gs.candidates)
        # Use bracket directly through internal method for deterministic test
        from app.game.bracket_tricks import apply_dud_removal
        removed: set[str] = set()
        victim = apply_dud_removal(
            gs.candidates, gs.correct_password, removed
        )
        if victim:
            assert victim not in gs.candidates or victim in removed

    def test_candidates_excludes_removed(self):
        gs = GameState()
        gs.advance_to_menu()
        gs.start_game()
        initial = set(gs.candidates)
        # Manually remove a dud
        wrong = [w for w in gs.candidates if w != gs.correct_password][0]
        gs._removed_duds.add(wrong)
        assert wrong not in gs.candidates
        assert gs.correct_password in gs.candidates
