"""Puzzle generator for the Fallout-style hacking minigame.

Generates:
  - A set of candidate words (all same length)
  - A correct password chosen from those candidates
  - A two-column hex-dump layout with words embedded in junk characters
  - Bracket pairs scattered in the junk for bracket tricks

The layout mimics the actual Fallout terminal: 2 columns of 17 lines,
each line 12 characters wide, prefixed with hex addresses.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from app.game.likeness import calculate_likeness
from app.game.word_list import get_words_by_length

# Characters used as junk filler around words
JUNK_CHARS = list("!@#$%^&*;:'\",./\\|?`~+-=_()[]{}<>")

# Bracket types
BRACKET_PAIRS = [("(", ")"), ("[", "]"), ("{", "}"), ("<", ">")]


@dataclass
class WordPosition:
    """Position of a word within the hex-dump grid."""
    word: str
    column: int     # 0 = left column, 1 = right column
    row: int        # row index within the column
    start_col: int  # character offset within the row
    is_removed: bool = False


@dataclass
class BracketPosition:
    """Position of a bracket pair within the hex-dump grid."""
    pair_id: int
    open_char: str
    close_char: str
    column: int
    row: int
    start_col: int
    length: int     # total length including brackets and filler
    used: bool = False


@dataclass
class HexDumpLayout:
    """The complete hex-dump display data."""
    left_column: list[str]          # lines of text for left column
    right_column: list[str]         # lines of text for right column
    left_addresses: list[str]      # hex addresses for left column
    right_addresses: list[str]     # hex addresses for right column
    word_positions: list[WordPosition]
    bracket_positions: list[BracketPosition]


@dataclass
class Puzzle:
    """A complete hacking puzzle."""
    candidates: list[str]
    correct_password: str
    word_length: int
    layout: HexDumpLayout


def _fill_junk(length: int) -> str:
    """Generate a string of random junk characters."""
    return "".join(random.choice(JUNK_CHARS) for _ in range(length))


def _generate_bracket_content(max_len: int) -> str:
    """Generate content for inside a bracket pair (1-4 junk chars)."""
    inner_len = min(random.randint(1, 4), max_len - 2)
    if inner_len < 1:
        return ""
    return _fill_junk(inner_len)


def _build_column_lines(
    words: list[str],
    line_width: int,
    num_lines: int,
    column_index: int,
    word_positions: list[WordPosition],
    bracket_positions: list[BracketPosition],
    bracket_id_start: int,
) -> list[str]:
    """Build lines of junk text with embedded words and bracket pairs.

    Words are distributed evenly across available lines with some
    randomization to avoid a rigid pattern.
    """
    lines: list[str] = []
    bracket_id = bracket_id_start

    # Distribute words across lines somewhat evenly
    word_row_assignments: dict[int, str] = {}
    if words:
        # Create candidate rows — skip some to leave room for junk-only lines
        available_rows = list(range(num_lines))
        random.shuffle(available_rows)
        for i, word in enumerate(words):
            if i < len(available_rows):
                word_row_assignments[available_rows[i]] = word

    for row in range(num_lines):
        line = list(_fill_junk(line_width))

        # Place a word if assigned to this row
        if row in word_row_assignments:
            word = word_row_assignments[row]
            max_start = line_width - len(word)
            if max_start < 0:
                max_start = 0
            start = random.randint(0, max(0, max_start))
            for i, ch in enumerate(word):
                if start + i < line_width:
                    line[start + i] = ch
            word_positions.append(WordPosition(
                word=word,
                column=column_index,
                row=row,
                start_col=start,
            ))

        # Try to place a bracket pair in remaining junk space
        if random.random() < 0.45:
            open_ch, close_ch = random.choice(BRACKET_PAIRS)
            inner = _generate_bracket_content(6)
            bracket_str = open_ch + inner + close_ch
            blen = len(bracket_str)

            # Find a gap not overlapping a word
            for _attempt in range(10):
                bs = random.randint(0, max(0, line_width - blen))
                # Check no overlap with placed word in this row
                overlaps = False
                for wp in word_positions:
                    if wp.row == row and wp.column == column_index:
                        ws = wp.start_col
                        we = ws + len(wp.word)
                        if not (bs + blen <= ws or bs >= we):
                            overlaps = True
                            break
                if not overlaps and bs + blen <= line_width:
                    for i, ch in enumerate(bracket_str):
                        line[bs + i] = ch
                    bracket_positions.append(BracketPosition(
                        pair_id=bracket_id,
                        open_char=open_ch,
                        close_char=close_ch,
                        column=column_index,
                        row=row,
                        start_col=bs,
                        length=blen,
                    ))
                    bracket_id += 1
                    break

        lines.append("".join(line))

    return lines


def _generate_hex_addresses(count: int, base: int = 0xF400) -> list[str]:
    """Generate hex address labels."""
    return [f"0x{base + i * 0x0C:04X}" for i in range(count)]


def generate_puzzle(
    min_word_length: int = 7,
    max_word_length: int = 10,
    num_candidates: int = 12,
    num_lines: int = 17,
    line_width: int = 12,
) -> Puzzle:
    """Generate a complete hacking puzzle.

    - Picks a random word length
    - Selects candidates from the word list
    - Designates one as the correct password
    - Builds a two-column hex-dump layout
    """
    # Pick a word length and get available words
    word_length = random.randint(min_word_length, max_word_length)
    available = get_words_by_length(word_length)

    if len(available) < num_candidates:
        # Fall back to any length that has enough words
        for wl in range(min_word_length, max_word_length + 1):
            available = get_words_by_length(wl)
            if len(available) >= num_candidates:
                word_length = wl
                break

    # Sample candidates
    actual_count = min(num_candidates, len(available))
    candidates = random.sample(available, actual_count)

    # Choose the correct password
    correct_password = random.choice(candidates)

    # Split candidates between left and right columns
    half = (len(candidates) + 1) // 2
    left_words = candidates[:half]
    right_words = candidates[half:]

    word_positions: list[WordPosition] = []
    bracket_positions: list[BracketPosition] = []

    left_lines = _build_column_lines(
        left_words, line_width, num_lines, 0,
        word_positions, bracket_positions, 0,
    )
    right_lines = _build_column_lines(
        right_words, line_width, num_lines, 1,
        word_positions, bracket_positions,
        len(bracket_positions),
    )

    left_addresses = _generate_hex_addresses(len(left_lines), 0xF400)
    right_addresses = _generate_hex_addresses(
        len(right_lines), 0xF400 + len(left_lines) * 0x0C
    )

    layout = HexDumpLayout(
        left_column=left_lines,
        right_column=right_lines,
        left_addresses=left_addresses,
        right_addresses=right_addresses,
        word_positions=word_positions,
        bracket_positions=bracket_positions,
    )

    return Puzzle(
        candidates=candidates,
        correct_password=correct_password,
        word_length=word_length,
        layout=layout,
    )
