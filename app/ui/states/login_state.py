"""Login state on the terminal grid."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent

from app.ui.states.base import TerminalState
from app.ui.theme import get_active_theme


class LoginState(TerminalState):
    """System Login handling raw key events to render onto the grid."""

    def __init__(self, config, parent):
        super().__init__(config, parent)
        # Using parent._auth is a bit hacky, but avoids circular imports
        self._auth = parent._auth if hasattr(parent, "_auth") else None
        
        self._username = config.system.username or "dev"
        self._password = ""
        self._status_message = ""
        self._status_color = None
        self._field_focus = 1  # 0=username, 1=password
        self._cooldown_active = False
        
        self._blink_state = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)

        self._start_row = 4
        self._start_col = 4

    def enter(self, grid) -> None:
        super().enter(grid)
        self._password = ""
        self._status_message = ""
        self._field_focus = 1
        self._cooldown_active = False
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
        key = event.key()

        if key == Qt.Key.Key_Escape:
            if hasattr(self.parent(), "_on_system_login_cancelled"):
                self.parent()._on_system_login_cancelled()
            return True

        if self._cooldown_active:
            return True

        if key == Qt.Key.Key_Tab:
            self._field_focus = 1 - self._field_focus
            self.render()
            return True

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._attempt_login()
            return True

        if key == Qt.Key.Key_Backspace:
            if self._field_focus == 0:
                self._username = self._username[:-1]
            else:
                self._password = self._password[:-1]
            self.render()
            return True

        ch = event.text()
        if ch and ch.isprintable():
            if self._field_focus == 0:
                self._username += ch
            else:
                self._password += ch
            self.render()
            return True

        return False

    def _attempt_login(self) -> None:
        if not self._username or not self._password:
            self._status_message = "> ENTER USERNAME AND PASSWORD"
            self._status_color = "error"
            self.render()
            return

        success = False
        if self._auth:
            success = self._auth.authenticate(self._username, self._password)

        if success:
            self._status_message = "> ACCESS GRANTED"
            self._status_color = "accent"
            self.render()
            QTimer.singleShot(1000, self._on_success)
        else:
            self._status_message = "> ACCESS DENIED - INVALID CREDENTIALS"
            self._status_color = "error"
            self._password = ""
            self.render()
            
            self._cooldown_active = True
            QTimer.singleShot(3000, self._end_cooldown)

    def _on_success(self) -> None:
        if hasattr(self.parent(), "_on_system_authenticated"):
            self.parent()._on_system_authenticated(self._username)

    def _end_cooldown(self) -> None:
        self._cooldown_active = False
        self._status_message = ""
        self.render()

    def _draw_state(self) -> None:
        theme = get_active_theme()
        row = self._start_row
        col = self._start_col

        self.grid.write_string("ROBCO INDUSTRIES", row, col, fg=theme.text)
        row += 1
        self.grid.write_string("SYSTEM OVERRIDE", row, col, fg=theme.text)
        row += 2
        
        self.grid.write_string("==================================", row, col, fg=theme.dim)
        row += 2

        # Username field
        u_color = theme.text if self._field_focus == 0 else theme.dim
        u_text = f"USERNAME: {self._username}".upper()
        self.grid.write_string(u_text, row, col, fg=u_color)
        if self._field_focus == 0 and self._blink_state:
            self.grid.write_string("█", row, col + len(u_text), fg=theme.text)
        row += 2

        # Password field
        p_color = theme.text if self._field_focus == 1 else theme.dim
        masked = "*" * len(self._password)
        p_text = f"PASSWORD: {masked}".upper()
        self.grid.write_string(p_text, row, col, fg=p_color)
        if self._field_focus == 1 and self._blink_state:
            self.grid.write_string("█", row, col + len(p_text), fg=theme.text)
        row += 2
        
        self.grid.write_string("==================================", row, col, fg=theme.dim)
        row += 2

        # Status
        if self._status_message:
            if self._status_color == "accent":
                scolor = theme.accent
            elif self._status_color == "error":
                # Fallback to theme text but we can also use a hardcoded color if we want,
                # but pure monochrome means we just use text or dim. We'll use text.
                scolor = theme.text 
            else:
                scolor = theme.dim
            self.grid.write_string(self._status_message, row, col, fg=scolor)
            row += 2

        if self._cooldown_active:
            self.grid.write_string("PLEASE WAIT...", row, col, fg=theme.dim)
            row += 2

        row += 2
        self.grid.write_string("[ENTER] AUTHENTICATE    [ESC] RETURN TO TERMLINK", row, col, fg=theme.dim)
        row += 2
        
        self.grid.write_string(">", row, col, fg=theme.text)
        if not self._cooldown_active and self._blink_state:
            # The cursor block is already blinking on the active field, but we can have one at the bottom too
            self.grid.write_string("_", row, col + 2, fg=theme.text)
