"""Game state machine for the Fallout hacking minigame.

States: BOOT → MENU → PLAYING → LOCKOUT | AUTHENTICATED
Manages attempts, guesses, bracket tricks, and dud tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from app.game.bracket_tricks import (
    BracketEffect,
    apply_allowance_replenishment,
    apply_dud_removal,
    choose_bracket_effect,
)
from app.game.likeness import calculate_likeness
from app.game.puzzle_generator import Puzzle, generate_puzzle


class GamePhase(Enum):
    BOOT = auto()
    MENU = auto()
    PLAYING = auto()
    LOCKOUT = auto()
    AUTHENTICATED = auto()


@dataclass
class GuessResult:
    """Result of a password guess."""
    word: str
    is_correct: bool
    likeness: int
    likeness_total: int
    attempts_remaining: int


@dataclass
class BracketResult:
    """Result of using a bracket trick."""
    effect: BracketEffect
    removed_word: str | None = None
    new_attempts: int = 0


class GameState:
    """Manages the full state of a hacking game session."""

    def __init__(
        self,
        initial_attempts: int = 4,
        max_attempts: int = 4,
        min_word_length: int = 7,
        max_word_length: int = 10,
        num_candidates: int = 12,
    ) -> None:
        self._initial_attempts = initial_attempts
        self._max_attempts = max_attempts
        self._min_word_length = min_word_length
        self._max_word_length = max_word_length
        self._num_candidates = num_candidates

        self._phase: GamePhase = GamePhase.BOOT
        self._attempts_remaining: int = initial_attempts
        self._puzzle: Puzzle | None = None
        self._removed_duds: set[str] = set()
        self._used_brackets: set[int] = set()
        self._guess_history: list[GuessResult] = []
        self._terminal_history: list[str] = []

    # --- Properties ---

    @property
    def phase(self) -> GamePhase:
        return self._phase

    @property
    def attempts_remaining(self) -> int:
        return self._attempts_remaining

    @property
    def puzzle(self) -> Puzzle | None:
        return self._puzzle

    @property
    def candidates(self) -> list[str]:
        if self._puzzle is None:
            return []
        return [
            w for w in self._puzzle.candidates
            if w not in self._removed_duds
        ]

    @property
    def correct_password(self) -> str:
        if self._puzzle is None:
            return ""
        return self._puzzle.correct_password

    @property
    def removed_duds(self) -> set[str]:
        return self._removed_duds.copy()

    @property
    def used_brackets(self) -> set[int]:
        return self._used_brackets.copy()

    @property
    def guess_history(self) -> list[GuessResult]:
        return list(self._guess_history)

    @property
    def terminal_history(self) -> list[str]:
        return list(self._terminal_history)

    @property
    def is_locked_out(self) -> bool:
        return self._phase == GamePhase.LOCKOUT

    @property
    def is_authenticated(self) -> bool:
        return self._phase == GamePhase.AUTHENTICATED

    # --- State transitions ---

    def advance_to_menu(self) -> None:
        """Move from BOOT to MENU."""
        if self._phase == GamePhase.BOOT:
            self._phase = GamePhase.MENU

    def start_game(self, num_lines: int = 17, line_width: int = 12) -> Puzzle:
        """Generate a new puzzle and enter PLAYING phase."""
        if self._phase != GamePhase.MENU:
            raise RuntimeError(f"Cannot start game from phase {self._phase}")
            
        self._puzzle = generate_puzzle(
            min_word_length=self._min_word_length,
            max_word_length=self._max_word_length,
            num_candidates=self._num_candidates,
            num_lines=num_lines,
            line_width=line_width,
        )
        self._attempts_remaining = self._initial_attempts
        self._removed_duds.clear()
        self._used_brackets.clear()
        self._guess_history.clear()
        self._terminal_history.clear()
        self._phase = GamePhase.PLAYING
        return self._puzzle

    def set_authenticated(self) -> None:
        """Mark the session as authenticated (e.g., by real password bypass)."""
        self._phase = GamePhase.AUTHENTICATED

    def force_lockout(self) -> None:
        """Force lockout (e.g., loaded from persistence)."""
        self._phase = GamePhase.LOCKOUT

    # --- Game actions ---

    def guess(self, word: str) -> GuessResult:
        """Submit a password guess.

        Returns a GuessResult. Consumes one attempt if incorrect.
        Raises RuntimeError if not in PLAYING phase.
        """
        if self._phase != GamePhase.PLAYING:
            raise RuntimeError(f"Cannot guess in phase {self._phase}")

        word = word.upper().strip()

        # Check if the word is a valid candidate
        if word not in self.candidates:
            raise ValueError(f"'{word}' is not a valid candidate")

        likeness = calculate_likeness(word, self.correct_password)
        is_correct = (word == self.correct_password)

        if is_correct:
            self._phase = GamePhase.AUTHENTICATED
        else:
            self._attempts_remaining -= 1
            if self._attempts_remaining <= 0:
                self._phase = GamePhase.LOCKOUT

        result = GuessResult(
            word=word,
            is_correct=is_correct,
            likeness=likeness,
            likeness_total=len(self.correct_password),
            attempts_remaining=self._attempts_remaining,
        )
        self._guess_history.append(result)
        
        # Add to terminal history
        self._terminal_history.append(f"> {word}")
        if is_correct:
            self._terminal_history.append("EXACT MATCH!")
            self._terminal_history.append("PLEASE WAIT - WHILE SYSTEM IS ACCESSED")
        else:
            self._terminal_history.append("ENTRY DENIED")
            self._terminal_history.append(f"LIKENESS={likeness}/{len(self.correct_password)}")
        
        return result

    def use_bracket(self, pair_id: int) -> BracketResult | None:
        """Use a bracket trick.

        Returns the effect, or None if the bracket was already used.
        """
        if self._phase != GamePhase.PLAYING:
            return None

        if pair_id in self._used_brackets:
            return None

        # Record the bracket text in terminal history
        bracket_str = ""
        if self._puzzle:
            for bp in self._puzzle.layout.bracket_positions:
                if bp.pair_id == pair_id:
                    if bp.column == 0:
                        bracket_str = self._puzzle.layout.left_column[bp.row][bp.start_col:bp.start_col+bp.length]
                    else:
                        bracket_str = self._puzzle.layout.right_column[bp.row][bp.start_col:bp.start_col+bp.length]
                    break
        if bracket_str:
            self._terminal_history.append(f"> {bracket_str}")

        self._used_brackets.add(pair_id)
        effect = choose_bracket_effect()

        if effect == BracketEffect.DUD_REMOVED:
            removed = apply_dud_removal(
                self.candidates, self.correct_password, self._removed_duds
            )
            if removed is None:
                # No duds left to remove, replenish instead
                effect = BracketEffect.ALLOWANCE_REPLENISHED
                self._attempts_remaining = apply_allowance_replenishment(
                    self._attempts_remaining, self._max_attempts
                )
                self._terminal_history.append("> Allowance replenished.")
                return BracketResult(
                    effect=effect,
                    new_attempts=self._attempts_remaining,
                )
            
            self._terminal_history.append("> Dud removed.")
            return BracketResult(effect=effect, removed_word=removed)

        elif effect == BracketEffect.ALLOWANCE_REPLENISHED:
            self._attempts_remaining = apply_allowance_replenishment(
                self._attempts_remaining, self._max_attempts
            )
            self._terminal_history.append("> Allowance replenished.")
            return BracketResult(
                effect=effect,
                new_attempts=self._attempts_remaining,
            )

        return None

    def is_valid_candidate(self, word: str) -> bool:
        """Check if a word is in the active candidate list."""
        return word.upper().strip() in self.candidates
