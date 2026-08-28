"""Boot state: Simulates hardware BIOS POST sequence on the terminal grid."""

import random
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QKeyEvent

from app.ui.states.base import TerminalState
from app.ui.theme import get_active_theme

BOOT_SEQUENCE = [
    ("ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM", 30),
    ("COPYRIGHT 2075-2077 ROBCO INDUSTRIES", 30),
    ("-SERVER 06-", 30),
    ("", 0),
    ("RBIOS v4.02.08.00", 30),
    ("", 0),
    ("MEMORY CHECK", 10),
    ("00000000 - 00FFFFFF ............ ", 10),
    ("OK", 400),
    ("", 0),
    ("CPU INITIALIZATION ............. ", 10),
    ("OK", 100),
    ("TERMINAL CONTROLLER ............ ", 10),
    ("OK", 100),
    ("MEMORY CONTROLLER .............. ", 10),
    ("OK", 200),
    ("SECURITY SYSTEM ................ ", 10),
    ("OK", 200),
    ("USER DATABASE .................. ", 10),
    ("OK", 100),
    ("", 0),
    ("LOADING TERMLINK PROTOCOL...", 200),
    ("", 0),
    ("[ OK ]", 500),
    ("", 0),
    ("SYSTEM READY", 50),
    ("", 0),
    (">", 50),
]


class BootState(TerminalState):
    """Handles the sequential rendering of boot text to the grid."""

    def __init__(self, config, parent):
        super().__init__(config, parent)
        self._current_step = 0
        self._current_char = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        
        # Grid layout tracking
        self._start_row = 2
        self._start_col = 4
        self._lines: list[str] = [""]
        self._cursor_row = 0
        self._cursor_col = 0
        self._finished = False

    def enter(self, grid) -> None:
        super().enter(grid)
        self._current_step = 0
        self._current_char = 0
        self._lines = [""]
        self._cursor_row = 0
        self._cursor_col = 0
        self._finished = False
        
        if self.config.boot.show_animation:
            self._timer.start(20)
        else:
            self.skip()

    def exit(self) -> None:
        self._timer.stop()
        super().exit()

    def skip(self) -> None:
        self._timer.stop()
        
        # Fast forward all text
        final_lines = []
        current_str = ""
        for text, _ in BOOT_SEQUENCE:
            if text in ("OK", "[ OK ]", ">"):
                current_str += text
                if final_lines:
                    final_lines[-1] = current_str
            else:
                if current_str:
                    final_lines.append(text)
                else:
                    final_lines.append(text)
                current_str = text
                
        self._lines = final_lines
        self._finished = True
        self.render()
        
        # Schedule transition to menu after a brief pause
        QTimer.singleShot(500, self._transition_to_menu)

    def _advance(self) -> None:
        if self._current_step >= len(BOOT_SEQUENCE):
            self._timer.stop()
            self._finished = True
            QTimer.singleShot(1000, self._transition_to_menu)
            return

        text, delay = BOOT_SEQUENCE[self._current_step]
        is_continuation = text in ("OK", "[ OK ]", ">")
        
        if self._current_char == 0 and not is_continuation:
            if self._current_step > 0:
                self._lines.append("")

        if self._current_char < len(text):
            self._lines[-1] += text[self._current_char]
            self._current_char += 1
            
            # Request re-render of this character
            self.render()
            
            if delay > 0:
                self._timer.setInterval(max(5, delay + random.randint(-5, 10)))
            else:
                self._timer.setInterval(0)
        else:
            self._current_step += 1
            self._current_char = 0
            if self._current_step < len(BOOT_SEQUENCE):
                _, next_delay = BOOT_SEQUENCE[self._current_step]
                if next_delay > 50:
                    self._timer.setInterval(next_delay)
                else:
                    self._timer.setInterval(20)

    def _transition_to_menu(self) -> None:
        if self.parent():
            # Notify MainWindow to change state
            self.parent()._show_state(1)  # 1 = SCREEN_MENU

    def _draw_state(self) -> None:
        theme = get_active_theme()
        
        for r, line in enumerate(self._lines):
            row_idx = self._start_row + r
            # Use dim color for routine status, normal color for headers
            if "OK" in line or "READY" in line or ">" in line:
                color = theme.text
            else:
                color = theme.dim
                
            if r < 3: # Headers
                color = theme.text
                
            self.grid.write_string(line, row_idx, self._start_col, fg=color)
            self._cursor_row = row_idx
            self._cursor_col = self._start_col + len(line)

        # Draw blinking cursor block if we are waiting for transition
        if self._finished:
            # We would toggle visibility based on a timer, but since Boot transitions quickly,
            # we just draw a solid block for now.
            self.grid.write_string("█", self._cursor_row, self._cursor_col, fg=theme.text)

    def keyPressEvent(self, event: QKeyEvent) -> bool:
        if not self._finished:
            self.skip()
            return True
        return False
