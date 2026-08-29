"""Tweaks State: terminal configuration interface."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent

from app.ui.states.base import TerminalState
from app.ui.theme import get_active_theme, set_active_scheme
from app.config.settings import save_config


class TweaksState(TerminalState):
    """Terminal configuration panel."""

    def __init__(self, config, parent):
        super().__init__(config, parent)
        self._current = 0
        self._items = [
            "DISPLAY SCHEME",
            "SCANLINES",
            "PHOSPHOR GLOW",
            "CRT NOISE",
            "BOOT SEQUENCE",
            "RETURN",
        ]
        self._schemes = ["GREEN", "AMBER", "BLUE"]
        self._start_row = 4
        self._start_col = 4
        
        self._blink_state = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)

    def enter(self, grid) -> None:
        super().enter(grid)
        self._current = 0
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
        # Items are drawn starting at row = self._start_row + 2, skipping 1 empty line (+= 2)
        item_start_row = self._start_row + 2
        
        # Check if mouse is on a row corresponding to an item
        offset = row - item_start_row
        if offset >= 0 and offset % 2 == 0:
            idx = offset // 2
            if 0 <= idx < len(self._items):
                if self._current != idx:
                    self._current = idx
                    self.render()
                return True
        return False

    def mousePressEvent(self, event, row: int, col: int) -> bool:
        item_start_row = self._start_row + 2
        offset = row - item_start_row
        if offset >= 0 and offset % 2 == 0:
            idx = offset // 2
            if 0 <= idx < len(self._items):
                self._current = idx
                self._toggle_setting(1)
                return True
        return False

    def keyPressEvent(self, event: QKeyEvent) -> bool:
        key = event.key()

        if key == Qt.Key.Key_Escape:
            self._save_and_return()
            return True

        if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self._current = (self._current - 1) % len(self._items)
            self.render()
            return True
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self._current = (self._current + 1) % len(self._items)
            self.render()
            return True
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self._toggle_setting(-1)
            return True
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._toggle_setting(1)
            return True
            
        return False

    def _save_and_return(self) -> None:
        from pathlib import Path
        config_path = Path(__file__).resolve().parent.parent.parent.parent / "config.toml"
        if not config_path.parent.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
        save_config(config_path, self.config)
        
        if hasattr(self.parent(), "_on_return_to_menu"):
            self.parent()._on_return_to_menu()

    def _toggle_setting(self, direction: int) -> None:
        item = self._items[self._current]
        d_cfg = self.config.display

        if item == "DISPLAY SCHEME":
            idx = self._schemes.index(d_cfg.scheme.upper())
            idx = (idx + direction) % len(self._schemes)
            d_cfg.scheme = self._schemes[idx].lower()
            set_active_scheme(d_cfg.scheme)
            
            # Since theme affects everything, force a full window update if we can
            if hasattr(self.parent(), "_renderer"):
                self.parent()._renderer.update()
        elif item == "SCANLINES":
            d_cfg.scanlines = not d_cfg.scanlines
            if hasattr(self.parent(), "_crt"):
                self.parent()._crt._rebuild_scanline_cache()
        elif item == "PHOSPHOR GLOW":
            d_cfg.phosphor_glow = not d_cfg.phosphor_glow
            if hasattr(self.parent(), "_crt"):
                self.parent()._crt._rebuild_vignette_cache()
        elif item == "CRT NOISE":
            d_cfg.noise = not d_cfg.noise
        elif item == "BOOT SEQUENCE":
            self.config.boot.show_animation = not self.config.boot.show_animation
        elif item == "RETURN":
            if direction > 0:  # Only Enter/Right triggers return
                self._save_and_return()

        self.render()

    def _draw_state(self) -> None:
        theme = get_active_theme()
        row = self._start_row
        col = self._start_col

        self.grid.write_string("ROBCO INDUSTRIES - TERMINAL TWEAKS", row, col, fg=theme.text)
        row += 2

        d_cfg = self.config.display
        b_cfg = self.config.boot
        
        values = [
            f"[{d_cfg.scheme.upper()}]",
            "[ON]" if d_cfg.scanlines else "[OFF]",
            "[ON]" if d_cfg.phosphor_glow else "[OFF]",
            "[ON]" if d_cfg.noise else "[OFF]",
            "[ON]" if b_cfg.show_animation else "[OFF]",
            "",
        ]

        for i, (item, val) in enumerate(zip(self._items, values)):
            # Pad item name so values align
            display_text = f"{item:<25} {val}"
            
            if i == self._current:
                # Active selection logic:
                # Normally, we'd inverse video. We can do that by drawing spaces as inverse, 
                # but it's simpler to just write it with > cursor
                self.grid.write_string(">> " + display_text.strip(), row, col, fg=theme.accent)
            else:
                self.grid.write_string("   " + display_text, row, col, fg=theme.dim)
            row += 2

        row += 2
        self.grid.write_string("[USE ARROW KEYS TO NAVIGATE AND TOGGLE]", row, col, fg=theme.dim)
        row += 2
        
        self.grid.write_string(">", row, col, fg=theme.text)
        if self._blink_state:
            self.grid.write_string("█", row, col + 2, fg=theme.text)
