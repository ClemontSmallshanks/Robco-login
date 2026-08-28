"""Hacking state on the terminal grid."""

import random
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from app.ui.states.base import TerminalState
from app.ui.theme import get_active_theme
from app.game.game_state import GameState, GamePhase, GuessResult, BracketResult
from app.game.puzzle_generator import Puzzle


class HackingState(TerminalState):
    """The core hacking minigame state."""

    def __init__(self, config, parent):
        super().__init__(config, parent)
        # We need the game state and auth from the parent MainWindow
        self._game: GameState = parent._game if hasattr(parent, "_game") else None
        
        self._hover_word: str | None = None
        self._hover_bracket: int | None = None
        
        self._start_row = 8
        self._left_col = 2
        self._right_col = 20  # Will be calculated dynamically
        
        self._input_buffer = ""
        self._blink_state = True
        
        self._flicker_timer = QTimer(self)
        self._flicker_timer.timeout.connect(self._flicker_junk)
        self._flicker_chars: list[tuple[int, int, str]] = []

    def enter(self, grid) -> None:
        super().enter(grid)
        self._hover_word = None
        self._hover_bracket = None
        self._input_buffer = ""
        self._blink_state = True
        
        # Calculate dynamic layout based on grid size
        if self._game and self._game.puzzle:
            line_width = len(self._game.puzzle.layout.left_column[0])
            total_width = (7 + line_width) * 2 + 2
            
            self._left_col = max(2, (self.grid.cols - total_width) // 2)
            self._right_col = self._left_col + (7 + line_width) + 2
        
        self._flicker_timer.start(150)
        self.render()

    def exit(self) -> None:
        self._flicker_timer.stop()
        super().exit()

    def _flicker_junk(self) -> None:
        if not self._game or not self._game.puzzle:
            return
            
        junk = "!@#$%^&*;:'\",./\\|?`~+-=_"
        
        # Increase number of flickering chars based on grid size
        num_flickers = max(1, self.grid.rows // 10)
        
        self._flicker_chars = [
            (random.randint(0, 1), random.randint(0, len(self._game.puzzle.layout.left_column) - 1), random.choice(junk))
            for _ in range(num_flickers)
        ]
        
        self._blink_state = not self._blink_state
        self.render()

    def _hit_test(self, row: int, col: int) -> tuple[str | None, int | None]:
        if not self._game or not self._game.puzzle:
            return None, None
            
        r_offset = row - self._start_row
        num_lines = len(self._game.puzzle.layout.left_column)
        if r_offset < 0 or r_offset >= num_lines:
            return None, None
            
        c_col_idx = -1
        c_char_idx = -1
        
        line_width = len(self._game.puzzle.layout.left_column[0])
        
        # Left column
        if self._left_col + 7 <= col < self._left_col + 7 + line_width:
            c_col_idx = 0
            c_char_idx = col - (self._left_col + 7)
        # Right column
        elif self._right_col + 7 <= col < self._right_col + 7 + line_width:
            c_col_idx = 1
            c_char_idx = col - (self._right_col + 7)
            
        if c_col_idx == -1:
            return None, None
            
        # Check words
        for wp in self._game.puzzle.layout.word_positions:
            if wp.word in self._game.removed_duds:
                continue
            if wp.column == c_col_idx and wp.row == r_offset:
                if wp.start_col <= c_char_idx < wp.start_col + len(wp.word):
                    return wp.word, None
                    
        # Check brackets
        for bp in self._game.puzzle.layout.bracket_positions:
            if bp.pair_id in self._game.used_brackets:
                continue
            if bp.column == c_col_idx and bp.row == r_offset:
                if bp.start_col <= c_char_idx < bp.start_col + bp.length:
                    return None, bp.pair_id
                    
        return None, None

    def mouseMoveEvent(self, event, row: int, col: int) -> bool:
        word, bracket = self._hit_test(row, col)
        if word != self._hover_word or bracket != self._hover_bracket:
            self._hover_word = word
            self._hover_bracket = bracket
            self.render()
            return True
        return False

    def mousePressEvent(self, event, row: int, col: int) -> bool:
        if self._hover_word:
            self._handle_word(self._hover_word)
            return True
        elif self._hover_bracket is not None:
            self._handle_bracket(self._hover_bracket)
            return True
        return False

    def _handle_word(self, word: str) -> None:
        if self._game.phase != GamePhase.PLAYING:
            return
            
        result = self._game.guess(word)
        self._input_buffer = ""
        
        if result.is_correct:
            if hasattr(self.parent(), "_on_hacking_authenticated"):
                self.parent()._on_hacking_authenticated()
        elif result.attempts_remaining <= 0:
            if hasattr(self.parent(), "_on_lockout"):
                self.parent()._on_lockout()
        self.render()

    def _handle_bracket(self, pair_id: int) -> None:
        if self._game.phase != GamePhase.PLAYING:
            return
            
        result = self._game.use_bracket(pair_id)
        # Effect is recorded in game history, just re-render
        self.render()

    def keyPressEvent(self, event: QKeyEvent) -> bool:
        key = event.key()

        if key == Qt.Key.Key_Tab:
            if hasattr(self.parent(), "_on_system_login_requested"):
                self.parent()._on_system_login_requested()
            return True
            
        elif key == Qt.Key.Key_Escape:
            if hasattr(self.parent(), "_on_return_to_menu"):
                self.parent()._on_return_to_menu()
            return True
            
        elif key == Qt.Key.Key_Backspace:
            if self._input_buffer:
                self._input_buffer = self._input_buffer[:-1]
                self.render()
            return True
            
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._input_buffer and self._game and self._game.is_valid_candidate(self._input_buffer):
                self._handle_word(self._input_buffer)
            else:
                self._input_buffer = ""
                self.render()
            return True
            
        ch = event.text()
        if ch and ch.isprintable():
            # Standard fallout hacking only uses uppercase
            self._input_buffer += ch.upper()
            self.render()
            return True
            
        return False

    def _draw_state(self) -> None:
        if not self._game:
            return
            
        theme = get_active_theme()
        
        # Header
        self.grid.write_string("ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL", 2, self._left_col, fg=theme.text)
        self.grid.write_string("ENTER PASSWORD NOW", 3, self._left_col, fg=theme.text)
        
        attempts = self._game.attempts_remaining
        blocks = "■ " * attempts
        self.grid.write_string(f"{self.config.game.max_attempts} ATTEMPT(S) LEFT: {blocks}", 5, self._left_col, fg=theme.text)

        if not self._game.puzzle:
            return

        # Hex Dump Columns
        num_lines = len(self._game.puzzle.layout.left_column)
        
        for r in range(num_lines):
            row_idx = self._start_row + r
            
            # Left column
            addr_l = self._game.puzzle.layout.left_addresses[r] + " "
            data_l = list(self._game.puzzle.layout.left_column[r])
            self._draw_hex_row(row_idx, self._left_col, addr_l, data_l, 0, r, theme)
            
            # Right column
            addr_r = self._game.puzzle.layout.right_addresses[r] + " "
            data_r = list(self._game.puzzle.layout.right_column[r])
            self._draw_hex_row(row_idx, self._right_col, addr_r, data_r, 1, r, theme)

        # Terminal History Log
        log_row = self._start_row + num_lines + 2
        
        # Calculate how many history items we can actually fit
        max_history_lines = max(1, self.grid.rows - log_row - 2)
        
        history = self._game.terminal_history[-max_history_lines:]
        for entry in history:
            self.grid.write_string(entry, log_row, self._left_col, fg=theme.text)
            log_row += 1
            
        # Current input line
        self.grid.write_string(f"> {self._input_buffer}", log_row, self._left_col, fg=theme.text)
        
        # Blinking cursor
        if self._blink_state:
            self.grid.write_string("█", log_row, self._left_col + 2 + len(self._input_buffer), fg=theme.text)
            
        # Draw current hover word if present and we aren't typing
        if self._hover_word and not self._input_buffer:
            self.grid.write_string(self._hover_word, log_row, self._left_col + 2, fg=theme.text)

    def _draw_hex_row(self, row: int, col: int, addr: str, data: list[str], col_idx: int, r_idx: int, theme) -> None:
        # Draw address
        self.grid.write_string(addr, row, col, fg=theme.dim)
        
        # Determine if any sequence in this row needs to be highlighted
        hl_start, hl_end = -1, -1
        
        if self._hover_word:
            for wp in self._game.puzzle.layout.word_positions:
                if wp.word == self._hover_word and wp.column == col_idx and wp.row == r_idx:
                    hl_start = wp.start_col
                    hl_end = wp.start_col + len(wp.word)
                    
        elif self._hover_bracket is not None:
            for bp in self._game.puzzle.layout.bracket_positions:
                if bp.pair_id == self._hover_bracket and bp.column == col_idx and bp.row == r_idx:
                    hl_start = bp.start_col
                    hl_end = bp.start_col + bp.length

        # Apply flicker
        for fc, fr, char in self._flicker_chars:
            if fc == col_idx and fr == r_idx:
                # Replace character if it's not part of a valid word/bracket and not being highlighted
                idx = random.randint(0, len(data) - 1)
                # Ensure we don't flicker the highlighted area to keep it readable
                if not (hl_start <= idx < hl_end):
                    data[idx] = char

        # Duds replacement
        for wp in self._game.puzzle.layout.word_positions:
            if wp.word in self._game.removed_duds and wp.column == col_idx and wp.row == r_idx:
                for i in range(len(wp.word)):
                    data[wp.start_col + i] = "."
                    
        # Used brackets replacement
        for bp in self._game.puzzle.layout.bracket_positions:
            if bp.pair_id in self._game.used_brackets and bp.column == col_idx and bp.row == r_idx:
                for i in range(bp.length):
                    data[bp.start_col + i] = "."
                    
        # Now render data character by character to handle inverse highlighting
        data_col = col + len(addr)
        
        for i, char in enumerate(data):
            if hl_start <= i < hl_end:
                # Inverse video highlight
                self.grid.write_string(char, row, data_col + i, fg=theme.bg, bg=theme.accent)
            else:
                self.grid.write_string(char, row, data_col + i, fg=theme.text)
