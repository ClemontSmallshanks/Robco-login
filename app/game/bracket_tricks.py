"""Bracket trick detection and effects for the Fallout hacking minigame.

Bracket pairs: (), [], {}, <>
Each pair can be selected once. Selecting triggers either:
  - Dud removal (remove one incorrect candidate)
  - Allowance replenishment (restore attempts to max)
"""

from __future__ import annotations

import random
from enum import Enum, auto

from app.game.puzzle_generator import BracketPosition


class BracketEffect(Enum):
    DUD_REMOVED = auto()
    ALLOWANCE_REPLENISHED = auto()


def find_bracket_pairs(text: str) -> list[tuple[int, int, str, str]]:
    """Find matching bracket pairs in a line of text.

    Returns list of (start_index, end_index, open_char, close_char).
    Pairs cannot be nested — the first matching close bracket is used.
    """
    pairs: list[tuple[int, int, str, str]] = []
    openers = {"(": ")", "[": "]", "{": "}", "<": ">"}
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in openers:
            closer = openers[ch]
            # Find matching closer
            j = i + 1
            while j < len(text):
                if text[j] == closer:
                    pairs.append((i, j, ch, closer))
                    i = j  # skip past this pair
                    break
                # If we hit another opener of the same type, stop
                if text[j] in openers:
                    break
                j += 1
        i += 1
    return pairs


def choose_bracket_effect() -> BracketEffect:
    """Randomly choose what effect a bracket trick has."""
    return random.choice([
        BracketEffect.DUD_REMOVED,
        BracketEffect.ALLOWANCE_REPLENISHED,
    ])


def apply_dud_removal(
    candidates: list[str],
    correct_password: str,
    removed: set[str],
) -> str | None:
    """Remove one incorrect candidate. Never removes the correct password.

    Returns the removed word, or None if no duds remain.
    """
    duds = [
        w for w in candidates
        if w != correct_password and w not in removed
    ]
    if not duds:
        return None
    victim = random.choice(duds)
    removed.add(victim)
    return victim


def apply_allowance_replenishment(
    current_attempts: int,
    max_attempts: int,
) -> int:
    """Restore attempts to max. Returns the new attempt count."""
    return max_attempts
