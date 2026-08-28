"""Main application window.

Manages screen transitions via QStackedWidget with CRT overlay on top.
Fullscreen frameless in production, windowed in development mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QMouseEvent, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

from app.auth.authenticator import Authenticator, MockAuthenticator
from app.game.game_state import GamePhase, GameState
from app.system import lockout_persistence
from app.system.power import shutdown, restart
from app.system.session import start_session
from app.ui.crt_overlay import CRTOverlay
from app.ui.terminal.renderer import TerminalRenderer
from app.ui.states.base import TerminalState

if TYPE_CHECKING:
    from app.config.defaults import AppConfig

# Screen indices in the stacked widget
SCREEN_BOOT = 0
SCREEN_MENU = 1
SCREEN_HACKING = 2
SCREEN_SYSTEM_LOGIN = 3
SCREEN_LOCKOUT = 4
SCREEN_TWEAKS = 5


class MainWindow(QMainWindow):
    """Top-level window managing the terminal grid surface and states."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._dev_mode = config.system.development_mode

        # Create authenticator
        if config.system.mock_auth:
            self._auth: Authenticator = MockAuthenticator()
        else:
            self._auth = MockAuthenticator()  # fallback for now

        # Create game state
        self._game = GameState(
            initial_attempts=config.game.initial_attempts,
            max_attempts=config.game.max_attempts,
            min_word_length=config.game.min_word_length,
            max_word_length=config.game.max_word_length,
            num_candidates=config.game.num_candidates,
        )

        self.setWindowTitle("RobCo Terminal")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #080808;")

        # Single terminal rendering surface
        self._renderer = TerminalRenderer(self._config, self)
        self.setCentralWidget(self._renderer)

        # State management
        self._current_state: TerminalState | None = None
        self._states: dict[int, TerminalState] = {}
        self._setup_states()

        # Input event forwarding
        self._renderer.keyPressEvent = self._forward_key_press
        self._renderer.mouseMoveEvent = self._forward_mouse_move
        self._renderer.mousePressEvent = self._forward_mouse_press

        # CRT effect layer overlaying everything
        self._setup_crt_overlay()

        if not self._dev_mode:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.showFullScreen()

        # Start sequence
        if config.boot.show_animation and not lockout_persistence.is_locked_out():
            self._show_state(SCREEN_BOOT)
        else:
            if lockout_persistence.is_locked_out():
                self._show_state(SCREEN_LOCKOUT)
            else:
                self._show_state(SCREEN_MENU)

    def _setup_states(self) -> None:
        """Initialize all terminal states."""
        from app.ui.states.boot_state import BootState
        from app.ui.states.menu_state import MenuState
        from app.ui.states.hacking_state import HackingState
        from app.ui.states.login_state import LoginState
        from app.ui.states.lockout_state import LockoutState
        from app.ui.states.tweaks_state import TweaksState

        self._states[SCREEN_BOOT] = BootState(self._config, self)
        self._states[SCREEN_MENU] = MenuState(self._config, self)
        self._states[SCREEN_HACKING] = HackingState(self._config, self)
        self._states[SCREEN_SYSTEM_LOGIN] = LoginState(self._config, self)
        self._states[SCREEN_LOCKOUT] = LockoutState(self._config, self)
        self._states[SCREEN_TWEAKS] = TweaksState(self._config, self)

    def _setup_crt_overlay(self) -> None:
        """Create the CRT overlay on top of everything."""
        self._crt = CRTOverlay(self._config.display, self)
        self._crt.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._crt.setGeometry(self.rect())
        if self._current_state and self._renderer.grid:
            self._current_state.resize(self._renderer.grid)

    def _show_state(self, state_id: int) -> None:
        """Transition to a new state."""
        if state_id == SCREEN_MENU and self._game.phase == GamePhase.BOOT:
            self._game.advance_to_menu()
            
        if self._current_state:
            self._current_state.exit()
            
        self._current_state = self._states.get(state_id)
        if self._current_state and self._renderer.grid:
            self._current_state.enter(self._renderer.grid)
            
        self._renderer.update()

    def _forward_key_press(self, event: QKeyEvent) -> None:
        if self._current_state:
            if self._current_state.keyPressEvent(event):
                self._renderer.update()

    def _get_grid_coords(self, pos) -> tuple[int, int]:
        """Convert pixel pos to (row, col)."""
        x = pos.x() - self._renderer._offset_x
        y = pos.y() - self._renderer._offset_y
        col = int(x // self._renderer._char_width)
        row = int(y // self._renderer._char_height)
        return row, col

    def _forward_mouse_move(self, event: QMouseEvent) -> None:
        if self._current_state:
            row, col = self._get_grid_coords(event.position())
            if self._current_state.mouseMoveEvent(event, row, col):
                self._renderer.update()

    def _forward_mouse_press(self, event: QMouseEvent) -> None:
        if self._current_state:
            row, col = self._get_grid_coords(event.position())
            if self._current_state.mousePressEvent(event, row, col):
                self._renderer.update()

    def _on_login_selected(self) -> None:
        if self._game.phase == GamePhase.MENU:
            if self._renderer.grid:
                total_rows = self._renderer.grid.rows
                total_cols = self._renderer.grid.cols
                
                # Header uses ~7 rows. Footer uses ~8 rows. We want at least 15 rows.
                num_lines = max(10, total_rows - 16)
                
                # Two columns. Left and right margins = 10 cols total.
                # Center gap = 2 cols.
                # Address = 7 cols per column.
                # Total fixed cols = 10 + 2 + 14 = 26.
                avail_width = total_cols - 26
                line_width = max(10, avail_width // 2)
                
                self._game.start_game(num_lines=num_lines, line_width=line_width)
            else:
                self._game.start_game()
        self._show_state(SCREEN_HACKING)

    def _on_return_to_menu(self) -> None:
        self._game._phase = GamePhase.MENU
        self._show_state(SCREEN_MENU)

    def _on_tweaks_selected(self) -> None:
        self._show_state(SCREEN_TWEAKS)

    def _on_lockout(self) -> None:
        lockout_persistence.set_lockout()
        self._show_state(SCREEN_LOCKOUT)

    def _on_hacking_authenticated(self) -> None:
        start_session("user", self._dev_mode)

    def _on_system_login_requested(self) -> None:
        self._show_state(SCREEN_SYSTEM_LOGIN)

    def _on_system_login_cancelled(self) -> None:
        self._show_state(SCREEN_HACKING)

    def _on_system_authenticated(self, username: str) -> None:
        start_session(username, self._dev_mode)

    def _on_shutdown(self) -> None:
        shutdown(self._dev_mode)

    def _on_restart(self) -> None:
        restart(self._dev_mode)
