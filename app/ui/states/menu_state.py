"""Main Menu state on the terminal grid."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent

from app.ui.states.base import TerminalState
from app.ui.theme import get_active_theme


class MenuState(TerminalState):
    """Handles the main RobCo system menu."""

    def __init__(self, config, parent):
        super().__init__(config, parent)
        self._current = 0
        self._confirming: int | None = None
        self._items = ["LOGIN", "TWEAKS", "SHUTDOWN", "RESTART"]
        
        # Grid layout geometry
        self._start_row = 2
        self._start_col = 4
        
        self._blink_state = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)

    def enter(self, grid) -> None:
        super().enter(grid)
        self._current = 0
        self._confirming = None
        self._blink_state = True
        self._cursor_timer.start(530)
        self.render()

    def exit(self) -> None:
        self._cursor_timer.stop()
        super().exit()

    def _toggle_cursor(self) -> None:
        self._blink_state = not self._blink_state
        self.render()

    def mouseMoveEvent(self, event, row: int, col: int) -> bool:
        # Menus are on rows: start_row + 21 (since we write 21 header lines before menu)
        menu_start_row = self._start_row + 21
        if menu_start_row <= row < menu_start_row + len(self._items):
            idx = row - menu_start_row
            if self._current != idx:
                self._current = idx
                self.render()
            return True
        return False

    def mousePressEvent(self, event, row: int, col: int) -> bool:
        menu_start_row = self._start_row + 21
        if menu_start_row <= row < menu_start_row + len(self._items):
            self._select(self._current)
            return True
        return False

    def keyPressEvent(self, event: QKeyEvent) -> bool:
        key = event.key()

        # Confirmation mode
        if self._confirming is not None:
            if key == Qt.Key.Key_Y:
                idx = self._confirming
                self._confirming = None
                self.render()
                if idx == 2:
                    if hasattr(self.parent(), "_on_shutdown"):
                        self.parent()._on_shutdown()
                elif idx == 3:
                    if hasattr(self.parent(), "_on_restart"):
                        self.parent()._on_restart()
            elif key in (Qt.Key.Key_N, Qt.Key.Key_Escape):
                self._confirming = None
                self.render()
            return True

        if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self._current = (self._current - 1) % len(self._items)
            self.render()
            return True
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self._current = (self._current + 1) % len(self._items)
            self.render()
            return True
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._select(self._current)
            return True
            
        return False

    def _select(self, idx: int) -> None:
        if idx == 0:
            if hasattr(self.parent(), "_on_login_selected"):
                self.parent()._on_login_selected()
        elif idx == 1:
            if hasattr(self.parent(), "_on_tweaks_selected"):
                self.parent()._on_tweaks_selected()
        elif idx in (2, 3):
            self._confirming = idx
            self.render()

    def _draw_state(self) -> None:
        theme = get_active_theme()
        row = self._start_row
        col = self._start_col

        lines = [
            "ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM",
            "COPYRIGHT 2075-2077 ROBCO INDUSTRIES",
            "-SERVER 06-",
            "",
            "-RobCo Terminal Management System-",
            "==================================",
            "",
            "RobCoOS v.0.85",
            "(C)2076 RobCo",
            "",
            "SYSTEM STATUS",
            "",
            "MEMORY ................. 640K OK",
            "TERMINAL ............... ONLINE",
            "SECURITY ............... ACTIVE",
            "NETWORK ................ OFFLINE",
            "",
            "==================================",
            "",
            "USER AUTHENTICATION",
            "",
        ]

        for line in lines:
            if "==================================" in line:
                self.grid.write_string(line, row, col, fg=theme.dim)
            elif "OK" in line or "ONLINE" in line or "ACTIVE" in line or "OFFLINE" in line:
                self.grid.write_string(line, row, col, fg=theme.text)
            else:
                self.grid.write_string(line, row, col, fg=theme.text)
            row += 1

        # Menu options
        for i, item in enumerate(self._items):
            if i == self._current:
                self.grid.write_string(">> " + item, row, col, fg=theme.accent)
            else:
                self.grid.write_string("   " + item, row, col, fg=theme.dim)
            row += 1

        row += 1
        self.grid.write_string("==================================", row, col, fg=theme.dim)
        row += 2

        if self._confirming is not None:
            action = self._items[self._confirming]
            self.grid.write_string(f"CONFIRM SYSTEM {action}? [Y/N]", row, col, fg=theme.accent)
            row += 2

        self.grid.write_string(">", row, col, fg=theme.text)
        if self._blink_state:
            self.grid.write_string("█", row, col + 2, fg=theme.text)
