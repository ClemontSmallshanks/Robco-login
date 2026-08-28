"""Terminal Character Grid buffer abstraction."""

from dataclasses import dataclass
from typing import Optional
from PyQt6.QtGui import QColor

@dataclass
class Cell:
    """A single character cell in the terminal grid."""
    char: str = " "
    fg_color: Optional[QColor] = None  # None implies default theme text color
    bg_color: Optional[QColor] = None  # None implies default theme bg color (transparent)


class TerminalGrid:
    """Maintains a 2D buffer of characters representing the terminal screen."""
    
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self._buffer: list[list[Cell]] = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self._cursor_col = 0
        self._cursor_row = 0

    def clear(self) -> None:
        """Clear the entire terminal grid."""
        for r in range(self.rows):
            for c in range(self.cols):
                self._buffer[r][c].char = " "
                self._buffer[r][c].fg_color = None
                self._buffer[r][c].bg_color = None
        self._cursor_col = 0
        self._cursor_row = 0

    def set_cursor(self, row: int, col: int) -> None:
        self._cursor_row = row
        self._cursor_col = col

    def write_string(self, text: str, row: int, col: int, fg: Optional[QColor] = None, bg: Optional[QColor] = None) -> None:
        """Write a string horizontally starting at (row, col)."""
        if row < 0 or row >= self.rows:
            return
            
        for i, char in enumerate(text):
            c = col + i
            if 0 <= c < self.cols:
                self._buffer[row][c].char = char
                self._buffer[row][c].fg_color = fg
                self._buffer[row][c].bg_color = bg

    def fill_rect(self, start_row: int, start_col: int, height: int, width: int, char: str = " ", fg: Optional[QColor] = None, bg: Optional[QColor] = None) -> None:
        """Fill a rectangular area with a character and colors."""
        for r in range(start_row, start_row + height):
            if 0 <= r < self.rows:
                for c in range(start_col, start_col + width):
                    if 0 <= c < self.cols:
                        self._buffer[r][c].char = char
                        self._buffer[r][c].fg_color = fg
                        self._buffer[r][c].bg_color = bg

    def get_cell(self, row: int, col: int) -> Cell:
        """Retrieve a specific cell. Returns an empty default cell if out of bounds."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self._buffer[row][col]
        return Cell()
