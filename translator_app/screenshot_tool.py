"""Screenshot tool: fullscreen overlay with region selection."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget

LOGGER = logging.getLogger(__name__)


def normalize_selection_rect(
    start_x: int, start_y: int, end_x: int, end_y: int
) -> tuple[int, int, int, int]:
    """Normalize two corner points into (x, y, width, height) with positive dimensions."""
    x = min(start_x, end_x)
    y = min(start_y, end_y)
    w = abs(end_x - start_x)
    h = abs(end_y - start_y)
    return x, y, w, h


class ScreenshotOverlay(QWidget):
    """Fullscreen transparent overlay for selecting a screen region."""

    captured = pyqtSignal(bytes)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        """Set up fullscreen transparent window."""
        super().__init__()
        self._start_point: Optional[QPoint] = None
        self._end_point: Optional[QPoint] = None
        self._selecting = False

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CrossCursor))

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Draw semi-transparent overlay and selection rectangle."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._start_point and self._end_point:
            x, y, w, h = normalize_selection_rect(
                self._start_point.x(),
                self._start_point.y(),
                self._end_point.x(),
                self._end_point.y(),
            )

            # Clear the selection area to show the actual screen
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(x, y, w, h, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw selection border
            pen = QPen(QColor(62, 43, 31), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(x, y, w, h)

        painter.end()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Record the start point of the selection."""
        if event.button() == Qt.LeftButton:
            self._start_point = event.pos()
            self._end_point = event.pos()
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """Update the selection endpoint as the mouse moves."""
        if self._selecting:
            self._end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """Capture the selected region when the mouse is released."""
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self._end_point = event.pos()

            if self._start_point and self._end_point:
                x, y, w, h = normalize_selection_rect(
                    self._start_point.x(),
                    self._start_point.y(),
                    self._end_point.x(),
                    self._end_point.y(),
                )

                if w < 10 or h < 10:
                    self.cancelled.emit()
                    self.close()
                    return

                screen = QApplication.primaryScreen()
                if screen:
                    # Offset by screen geometry for multi-monitor setups
                    screen_geo = screen.geometry()
                    abs_x = screen_geo.x() + x
                    abs_y = screen_geo.y() + y

                    pixmap = screen.grabWindow(0, abs_x, abs_y, w, h)
                    png_data = self._pixmap_to_png_bytes(pixmap)
                    if png_data:
                        self.captured.emit(png_data)
                    else:
                        self.cancelled.emit()
                else:
                    self.cancelled.emit()

            self.close()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """Cancel on Escape key."""
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Emit cancelled if overlay is closed externally (e.g., Alt+F4)."""
        if not self._selecting:
            # Only emit if not already emitting via mouse/key handlers
            self.cancelled.emit()
        super().closeEvent(event)

    @staticmethod
    def _pixmap_to_png_bytes(pixmap: QPixmap) -> Optional[bytes]:
        """Convert a QPixmap to PNG bytes."""
        from PyQt5.QtCore import QBuffer, QIODevice

        if pixmap.isNull():
            return None

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not pixmap.save(buffer, "PNG"):
            return None
        return bytes(buffer.data())


class ScreenshotTool:
    """High-level API for capturing screenshots."""

    def __init__(self) -> None:
        """Initialize with no active overlay."""
        self._overlay: Optional[ScreenshotOverlay] = None
        self._result: Optional[bytes] = None
        self._completed = False

    def capture(self) -> Optional[bytes]:
        """Show the overlay, wait for user selection, return PNG bytes or None."""
        self._result = None
        self._completed = False

        self._overlay = ScreenshotOverlay()
        self._overlay.captured.connect(self._on_captured)
        self._overlay.cancelled.connect(self._on_cancelled)
        self._overlay.show()

        # Process events until the overlay closes
        app = QApplication.instance()
        if app:
            while not self._completed:
                app.processEvents()

        # Cleanup overlay to prevent memory leak
        if self._overlay is not None:
            self._overlay.captured.disconnect(self._on_captured)
            self._overlay.cancelled.disconnect(self._on_cancelled)
            self._overlay.deleteLater()
            self._overlay = None

        return self._result

    def _on_captured(self, data: bytes) -> None:
        """Store captured image data."""
        self._result = data
        self._completed = True

    def _on_cancelled(self) -> None:
        """Mark capture as cancelled."""
        self._result = None
        self._completed = True