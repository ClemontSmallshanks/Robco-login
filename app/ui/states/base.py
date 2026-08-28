"""Base class for terminal UI states."""

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from app.ui.terminal.grid import TerminalGrid
from app.config.defaults import AppConfig


class TerminalState(QObject):
    """Abstract base class for all terminal screen states (Boot, Menu, Hacking, etc.)."""
    
    def __init__(self, config: AppConfig, parent: QObject | None = None):
        super().__init__(parent)
        self.config = config
        self.grid: TerminalGrid | None = None

    def enter(self, grid: TerminalGrid) -> None:
        """Called when this state becomes active."""
        self.grid = grid
        self.render()

    def exit(self) -> None:
        """Called when this state is deactivated."""
        if self.grid:
            self.grid.clear()
        self.grid = None

    def render(self) -> None:
        """Completely redraw this state onto the grid."""
        if not self.grid:
            return
        self.grid.clear()
        self._draw_state()

    def _draw_state(self) -> None:
        """Override to draw specific screen content to self.grid."""
        pass

    def resize(self, grid: TerminalGrid) -> None:
        """Called when the terminal renderer resizes the grid."""
        self.grid = grid
        self.render()

    def keyPressEvent(self, event: QKeyEvent) -> bool:
        """Handle key press. Return True if event was handled."""
        return False

    def mouseMoveEvent(self, event: QMouseEvent, row: int, col: int) -> bool:
        """Handle mouse movement over the grid coordinates."""
        return False

    def mousePressEvent(self, event: QMouseEvent, row: int, col: int) -> bool:
        """Handle mouse click on the grid coordinates."""
        return False
