"""Markdown output widget: source view, preview window, copy, and export."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from translator_app.preview_window import (
    MarkdownPreviewWindow,
    _WEBENGINE_AVAILABLE,
)

LOGGER = logging.getLogger(__name__)

_MONOSPACE_FONT_STACK = "Consolas, 'Source Code Pro', 'Courier New', monospace"


class MarkdownOutputWidget(QFrame):
    """Widget for displaying Markdown translation results with a preview window."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the markdown output UI."""
        super().__init__(parent)
        self.setObjectName("cardFrame")

        self._markdown_text: str = ""
        self._preview_window: Optional[MarkdownPreviewWindow] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the widget layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        # Header row
        header_row = QHBoxLayout()
        section_label = QLabel("TRANSLATED (MARKDOWN)")
        section_label.setObjectName("sectionLabel")

        self._copy_button = QPushButton("Copy")
        self._copy_button.setObjectName("secondaryButton")
        self._copy_button.clicked.connect(self._on_copy_clicked)
        self._copy_button.setEnabled(False)

        self._preview_button = QPushButton("Preview")
        self._preview_button.setObjectName("secondaryButton")
        self._preview_button.clicked.connect(self._on_preview_clicked)
        self._preview_button.setEnabled(False)
        if not _WEBENGINE_AVAILABLE:
            self._preview_button.setEnabled(False)
            self._preview_button.setToolTip(
                "Install PyQtWebEngine for Markdown preview"
            )

        header_row.addWidget(section_label)
        header_row.addStretch()
        header_row.addWidget(self._copy_button)
        header_row.addWidget(self._preview_button)

        # Source text area (monospace, read-only)
        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("resultBox")
        self._text_edit.setReadOnly(True)
        self._text_edit.setAcceptRichText(True)
        self._text_edit.setPlaceholderText("Translation result appears here.")

        self._text_edit.setFont(self._create_monospace_font())

        layout.addLayout(header_row)
        layout.addWidget(self._text_edit, stretch=1)
        self.setLayout(layout)

    @staticmethod
    def _create_monospace_font() -> QFont:
        """Create a monospace font for source display."""
        font = QFont("monospace")
        font.setPointSize(13)
        font.setStyleHint(QFont.Monospace)
        return font

    def set_content(self, markdown_text: str) -> None:
        """Display the given Markdown in source mode."""
        self._markdown_text = markdown_text
        self._text_edit.setPlainText(markdown_text)
        self._copy_button.setEnabled(bool(markdown_text))
        self._preview_button.setEnabled(bool(markdown_text))
        # Live update preview window if open
        if self._preview_window is not None and self._preview_window.isVisible():
            self._preview_window.set_content(markdown_text)

    def get_content(self) -> str:
        """Return the current Markdown source text."""
        return self._markdown_text

    def clear_content(self) -> None:
        """Reset the widget to empty state."""
        self._markdown_text = ""
        self._text_edit.clear()
        self._copy_button.setEnabled(False)
        self._preview_button.setEnabled(False)
        # Hide preview window if open
        if self._preview_window is not None:
            self._preview_window.hide()

    def _on_copy_clicked(self) -> None:
        """Copy the Markdown source to the clipboard."""
        if self._markdown_text:
            QApplication.clipboard().setText(self._markdown_text)

    def _on_preview_clicked(self) -> None:
        """Open the Markdown preview window."""
        if not self._markdown_text:
            return
        if not _WEBENGINE_AVAILABLE:
            self._show_webengine_warning()
            return
        if self._preview_window is None:
            self._preview_window = MarkdownPreviewWindow(self.window())
        self._preview_window.set_content(self._markdown_text)
        self._preview_window.show()
        self._preview_window.raise_()
        self._preview_window.activateWindow()

    @staticmethod
    def _show_webengine_warning() -> None:
        """Show a message box explaining the PyQtWebEngine dependency."""
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.information(
            None,
            "Preview Unavailable",
            "The Markdown preview requires PyQtWebEngine.\n\n"
            "Install it with:\n"
            "  pip install PyQtWebEngine>=5.15,<6",
        )
