"""Terminal Renderer Widget.

This is the ONLY visual widget in the application (other than the CRT overlay).
It renders a TerminalGrid abstraction to the screen, converting logical character
coordinates into pixel-perfect monospace text rendering.
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QColor, QFontMetrics, QFont, QFontDatabase
from PyQt6.QtWidgets import QWidget

from app.config.defaults import AppConfig
from app.ui.theme import get_active_theme
from app.ui.terminal.grid import TerminalGrid

def _get_terminal_font(size: int) -> QFont:
    """Return the terminal font."""
    font = QFont("Share Tech Mono")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(size)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108.0)
    return font


class TerminalRenderer(QWidget):
    """Renders a TerminalGrid to the screen."""
    
    def __init__(self, config: AppConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self._config = config
        
        self._font_size = config.display.font_size
        self._font = _get_terminal_font(self._font_size)
        
        # Calculate cell dimensions
        fm = QFontMetrics(self._font)
        # For a true monospace font, all chars have the same advance.
        self._char_width = fm.horizontalAdvance("A")
        self._char_height = self._font_size + 4  # Line height with spacing
        
        # We will determine rows/cols dynamically in resizeEvent
        self._grid: TerminalGrid | None = None
        
        # Track offsets to center the grid (or align it left)
        self._offset_x = 0
        self._offset_y = 0
        
        # Reference resolution assumption for "classic" feel:
        # e.g., 80 columns by 25 rows
        # We'll allow the grid to fill the space, but we might pad it.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @property
    def grid(self) -> TerminalGrid:
        if not self._grid:
            self._grid = TerminalGrid(80, 24)
        return self._grid

    def set_font_size(self, size: int) -> None:
        """Update font size and force a grid recalculation."""
        if self._font_size == size:
            return
            
        self._font_size = size
        self._font = _get_terminal_font(self._font_size)
        
        fm = QFontMetrics(self._font)
        self._char_width = fm.horizontalAdvance("A")
        self._char_height = self._font_size + 4
        
        # Force recreation of grid with new dimensions
        self._grid = None
        
        from PyQt6.QtGui import QResizeEvent
        self.resizeEvent(QResizeEvent(self.size(), self.size()))
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        
        # Recalculate how many cols/rows we can fit
        w = self.width()
        h = self.height()
        
        # We want to leave a large "black margin" typical of old CRTs.
        # Let's say 10% margin on left/right, 10% on top/bottom
        margin_x = w * 0.1
        margin_y = h * 0.1
        
        usable_w = w - (margin_x * 2)
        usable_h = h - (margin_y * 2)
        
        cols = int(usable_w // self._char_width)
        rows = int(usable_h // self._char_height)
        
        # Enforce minimums so logic doesn't crash on tiny windows
        cols = max(cols, 60)
        rows = max(rows, 20)
        
        # Center the actual grid rendering
        actual_grid_w = cols * self._char_width
        actual_grid_h = rows * self._char_height
        
        self._offset_x = (w - actual_grid_w) // 2
        self._offset_y = (h - actual_grid_h) // 2
        
        # Only recreate grid if dimensions changed, to avoid wiping state constantly
        if not self._grid or self._grid.cols != cols or self._grid.rows != rows:
            old_grid = self._grid
            self._grid = TerminalGrid(cols, rows)
            # We don't port old text over dynamically yet; states will redraw on resize.

    def paintEvent(self, event) -> None:
        theme = get_active_theme()
        painter = QPainter(self)
        painter.setFont(self._font)
        
        # Fill pure black background
        painter.fillRect(self.rect(), theme.bg)
        
        if not self._grid:
            return
            
        # Draw the grid cells
        # We optimize by only changing pens/brushes when colors change.
        current_bg = theme.bg
        current_fg = theme.text
        painter.setPen(current_fg)
        
        # Pre-calculate baseline Y (QFontMetrics ascent)
        fm = painter.fontMetrics()
        baseline = fm.ascent()
        
        for r in range(self._grid.rows):
            y = self._offset_y + r * self._char_height
            
            for c in range(self._grid.cols):
                cell = self._grid.get_cell(r, c)
                x = self._offset_x + c * self._char_width
                
                # Draw background if it's not the default theme.bg
                bg_color = cell.bg_color if cell.bg_color is not None else theme.bg
                if bg_color != theme.bg:
                    painter.fillRect(x, y, self._char_width, self._char_height, bg_color)
                
                # Draw character
                if cell.char != " ":
                    fg_color = cell.fg_color if cell.fg_color is not None else theme.text
                    if fg_color != current_fg:
                        current_fg = fg_color
                        painter.setPen(current_fg)
                        
                    # Inverse colors don't usually glow to keep readability high.
                    # We can use simple drawText here and let CRTOverlay do the glow bloom.
                    painter.drawText(x, y + baseline, cell.char)
                    
        painter.end()

    # We will forward input events to an active state controller later.
