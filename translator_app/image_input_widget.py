"""Image input widget: upload, screenshot, preview, and drag-drop."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from translator_app.image_preprocessor import (
    SUPPORTED_FORMATS,
    preprocess_image,
    preprocess_image_from_bytes,
)
from translator_app.screenshot_tool import ScreenshotTool

LOGGER = logging.getLogger(__name__)


class ImageInputWidget(QFrame):
    """Widget for loading images via file upload, screenshot, or drag-and-drop."""

    image_loaded = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the image input UI."""
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setAcceptDrops(True)

        self._image_base64: Optional[str] = None
        self._image_path: str = ""
        self._screenshot_tool = ScreenshotTool()

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the widget layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        # Header row
        header_row = QHBoxLayout()
        section_label = QLabel("SOURCE IMAGE")
        section_label.setObjectName("sectionLabel")

        self._upload_button = QPushButton("Upload")
        self._upload_button.setObjectName("secondaryButton")
        self._upload_button.clicked.connect(self._on_upload_clicked)

        self._capture_button = QPushButton("Capture")
        self._capture_button.setObjectName("secondaryButton")
        self._capture_button.clicked.connect(self._on_capture_clicked)

        header_row.addWidget(section_label)
        header_row.addStretch()
        header_row.addWidget(self._upload_button)
        header_row.addWidget(self._capture_button)

        # Preview area
        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumHeight(180)
        self._preview_label.setStyleSheet(
            "QLabel { color: #8C7B6E; font-size: 14px; border: 2px dashed #D4CCC4; "
            "border-radius: 16px; padding: 20px; }"
        )
        self._preview_label.setText("Drag image here or click Upload")

        # File info
        self._file_info_label = QLabel()
        self._file_info_label.setObjectName("sectionLabel")
        self._file_info_label.setAlignment(Qt.AlignLeft)

        layout.addLayout(header_row)
        layout.addWidget(self._preview_label, stretch=1)
        layout.addWidget(self._file_info_label)
        self.setLayout(layout)

    def _on_upload_clicked(self) -> None:
        """Open file dialog and load the selected image."""
        extensions = " ".join(f"*.{fmt}" for fmt in sorted(SUPPORTED_FORMATS))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            f"Images ({extensions})",
        )
        if not file_path:
            return

        self._load_from_file(file_path)

    def _on_capture_clicked(self) -> None:
        """Minimize main window, take screenshot, then restore."""
        main_window = self.window()
        if main_window is None:
            return
        was_visible = main_window.isVisible()
        if was_visible:
            main_window.hide()

        # Small delay to let the window hide
        QApplication.processEvents()

        png_data = self._screenshot_tool.capture()

        if was_visible:
            main_window.show()

        if png_data is None:
            return

        self._load_from_bytes(png_data, ".png", source="screenshot")

    def _load_from_file(self, file_path: str) -> None:
        """Load and preprocess an image from a file path."""
        try:
            self._image_base64 = preprocess_image(file_path)
            self._image_path = file_path
            self._update_preview_from_file(file_path)
            self.image_loaded.emit(self._image_base64)
        except Exception as exc:
            LOGGER.error("Failed to load image: %s", exc)
            self._preview_label.setText(f"Error: {exc}")
            self._image_base64 = None
            self._image_path = ""

    def _load_from_bytes(self, data: bytes, extension: str, source: str = "") -> None:
        """Load and preprocess an image from raw bytes."""
        try:
            self._image_base64 = preprocess_image_from_bytes(data, extension)
            self._image_path = source
            self._update_preview_from_bytes(data)
            self.image_loaded.emit(self._image_base64)
        except Exception as exc:
            LOGGER.error("Failed to load image from bytes: %s", exc)
            self._preview_label.setText(f"Error: {exc}")
            self._image_base64 = None
            self._image_path = ""

    def _update_preview_from_file(self, file_path: str) -> None:
        """Show a thumbnail preview of the loaded file."""
        pixmap = QPixmap(file_path)
        self._show_thumbnail(pixmap, Path(file_path).name, pixmap.width(), pixmap.height())

    def _update_preview_from_bytes(self, data: bytes) -> None:
        """Show a thumbnail preview from raw image bytes."""
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self._show_thumbnail(pixmap, "Screenshot", pixmap.width(), pixmap.height())

    def _show_thumbnail(self, pixmap: QPixmap, name: str, width: int, height: int) -> None:
        """Display a scaled thumbnail and file info."""
        if pixmap.isNull():
            return

        max_preview = QSize(400, 250)
        scaled = pixmap.scaled(max_preview, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_label.setPixmap(scaled)
        self._preview_label.setStyleSheet(
            "QLabel { border: 1px solid #D4CCC4; border-radius: 16px; padding: 8px; }"
        )
        self._file_info_label.setText(f"📄 {name}  {width}×{height}")

    def get_image_base64(self) -> Optional[str]:
        """Return the currently loaded image as base64, or None."""
        return self._image_base64

    def clear_image(self) -> None:
        """Reset the widget to its empty state."""
        self._image_base64 = None
        self._image_path = ""
        self._preview_label.clear()
        self._preview_label.setText("Drag image here or click Upload")
        self._preview_label.setStyleSheet(
            "QLabel { color: #8C7B6E; font-size: 14px; border: 2px dashed #D4CCC4; "
            "border-radius: 16px; padding: 20px; }"
        )
        self._file_info_label.setText("")

    # Drag-and-drop support

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag events that contain image file URLs."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = Path(path).suffix.lower().lstrip(".")
                if ext in SUPPORTED_FORMATS:
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent) -> None:
        """Load the first supported image file from the drop."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = Path(path).suffix.lower().lstrip(".")
            if ext in SUPPORTED_FORMATS:
                self._load_from_file(path)
                return