"""Lockout state on the terminal grid."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent

from app.ui.states.base import TerminalState
from app.ui.theme import get_active_theme


class LockoutState(TerminalState):
    """System Lockout handling."""

    def __init__(self, config, parent):
        super().__init__(config, parent)
        self._blink_state = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)

        self._start_row = 6

    def enter(self, grid) -> None:
        super().enter(grid)
        self._blink_state = True
        self._cursor_timer.start(530)
        self.render()

    def exit(self) -> None:
        self._cursor_timer.stop()
        super().exit()

    def _toggle_cursor(self) -> None:
        self._blink_state = not self._blink_state
        self.render()

    def keyPressEvent(self, event: QKeyEvent) -> bool:
        # Ignore all keys, the system is locked
        return True

    def _draw_state(self) -> None:
        theme = get_active_theme()
        row = self._start_row
        
        lines = [
            "!!! SECURITY LOCKOUT !!!",
            "",
            "TERMLINK ACCESS DENIED",
            "",
            "MAXIMUM INVALID ATTEMPTS EXCEEDED",
            "",
            "SECURITY PROTOCOL 4.7 ACTIVE",
            "",
            "NO FURTHER AUTHENTICATION ATTEMPTS PERMITTED",
            "",
            "SYSTEM REBOOT REQUIRED",
            "",
            "==================================",
            "",
            "STATUS: LOCKED",
            "",
        ]

        # Calculate a nice left margin to center the block a bit
        col = max(4, (self.grid.cols - 40) // 2)

        for line in lines:
            if "!!!" in line or "DENIED" in line or "LOCKED" in line:
                color = theme.accent
            elif "====" in line:
                color = theme.dim
            else:
                color = theme.text
            self.grid.write_string(line, row, col, fg=color)
            row += 1

        self.grid.write_string(">", row, col, fg=theme.text)
        if self._blink_state:
            self.grid.write_string("█", row, col + 2, fg=theme.text)
