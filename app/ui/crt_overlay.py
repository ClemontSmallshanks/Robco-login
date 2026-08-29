"""CRT visual effects overlay.

Renders scanlines, phosphor glow, screen flicker, noise, and curvature
as a transparent overlay widget painted on top of all other content.
Uses cached QPixmap buffers for performance.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from app.config.defaults import DisplayConfig


class CRTOverlay(QWidget):
    """Transparent overlay providing CRT visual effects."""

    def __init__(self, config: DisplayConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self._config = config
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background: transparent;")

        # Cached pixmaps
        self._scanline_cache: QPixmap | None = None
        self._vignette_cache: QPixmap | None = None

        # Flicker state
        self._flicker_opacity: float = 0.0
        self._heavy_flicker_countdown: int = random.randint(60, 180)

        # Noise state
        self._noise_points: list[tuple[int, int, int]] = []

        # Flicker timer (low frequency to save CPU)
        if config.screen_flicker and config.crt_effects:
            self._flicker_timer = QTimer(self)
            self._flicker_timer.timeout.connect(self._update_flicker)
            self._flicker_timer.start(66)  # ~15fps

        # Noise timer
        if config.noise and config.crt_effects:
            self._noise_timer = QTimer(self)
            self._noise_timer.timeout.connect(self._update_noise)
            self._noise_timer.start(200)

    def _rebuild_scanline_cache(self) -> None:
        """Pre-render scanline pattern to a pixmap."""
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        pen = QPen(QColor(0, 0, 0, 50))
        pen.setWidth(1)
        painter.setPen(pen)
        for y in range(0, h, 3):
            painter.drawLine(0, y, w, y)
        painter.end()
        self._scanline_cache = pix

    def _rebuild_vignette_cache(self) -> None:
        """Pre-render vignette/glow effect."""
        from app.ui.theme import get_active_theme
        theme = get_active_theme()
        
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)

        # Corner darkening (curvature illusion)
        if self._config.curvature:
            gradient = QRadialGradient(w / 2, h / 2, max(w, h) * 0.7)
            gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
            gradient.setColorAt(0.7, QColor(0, 0, 0, 0))
            gradient.setColorAt(1.0, QColor(0, 0, 0, 120))
            painter.fillRect(0, 0, w, h, QBrush(gradient))

        # Phosphor glow
        if self._config.phosphor_glow:
            glow = QRadialGradient(w / 2, h / 2, max(w, h) * 0.75)
            glow_color = QColor(theme.accent)
            glow_color.setAlpha(25)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(0, 0, w, h, QBrush(glow))

        painter.end()
        self._vignette_cache = pix

    def _update_flicker(self) -> None:
        """Update flicker opacity."""
        self._heavy_flicker_countdown -= 1
        if self._heavy_flicker_countdown <= 0:
            self._flicker_opacity = random.uniform(0.03, 0.05)
            self._heavy_flicker_countdown = random.randint(60, 180)
        else:
            self._flicker_opacity = random.uniform(0.01, 0.02)
        self.update()

    def _update_noise(self) -> None:
        """Generate sparse random noise points."""
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        count = max(1, (w * h) // 5000)
        self._noise_points = [
            (random.randint(0, w - 1), random.randint(0, h - 1),
             random.randint(100, 255))
            for _ in range(count)
        ]
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._config.crt_effects:
            if self._config.scanlines:
                self._rebuild_scanline_cache()
            if self._config.phosphor_glow or self._config.curvature:
                self._rebuild_vignette_cache()

    def paintEvent(self, event) -> None:
        if not self._config.crt_effects:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Scanlines
        if self._config.scanlines and self._scanline_cache:
            painter.drawPixmap(0, 0, self._scanline_cache)

        # Vignette / glow
        if self._vignette_cache:
            painter.drawPixmap(0, 0, self._vignette_cache)

        # Screen flicker (darken the whole screen slightly)
        if self._config.screen_flicker and self._flicker_opacity > 0.005:
            alpha = int(self._flicker_opacity * 255)
            painter.fillRect(
                self.rect(),
                QColor(0, 0, 0, min(alpha, 40)),
            )

        # Noise
        if self._config.noise and self._noise_points:
            for x, y, brightness in self._noise_points:
                painter.setPen(QColor(0, brightness, 0, 80))
                painter.drawPoint(x, y)

        painter.end()
