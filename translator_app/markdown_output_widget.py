"""Markdown output widget: source view, rendered preview, copy, and export."""

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

LOGGER = logging.getLogger(__name__)

_MONOSPACE_FONT_STACK = "Consolas, 'Source Code Pro', 'Courier New', monospace"


class MarkdownOutputWidget(QFrame):
    """Widget for displaying Markdown translation results with source/preview toggle."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the markdown output UI."""
        super().__init__(parent)
        self.setObjectName("cardFrame")

        self._markdown_text: str = ""
        self._is_preview_mode = False
        self._markdown_available = True

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
        self._preview_button.clicked.connect(self._on_preview_toggled)
        self._preview_button.setEnabled(False)

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
        self._is_preview_mode = False
        self._text_edit.setPlainText(markdown_text)
        self._copy_button.setEnabled(bool(markdown_text))
        self._preview_button.setEnabled(bool(markdown_text))
        self._preview_button.setText("Preview")

    def get_content(self) -> str:
        """Return the current Markdown source text."""
        return self._markdown_text

    def clear_content(self) -> None:
        """Reset the widget to empty state."""
        self._markdown_text = ""
        self._is_preview_mode = False
        self._text_edit.clear()
        self._copy_button.setEnabled(False)
        self._preview_button.setEnabled(False)
        self._preview_button.setText("Preview")

    def _on_copy_clicked(self) -> None:
        """Copy the Markdown source to the clipboard."""
        if self._markdown_text:
            QApplication.clipboard().setText(self._markdown_text)

    def _on_preview_toggled(self) -> None:
        """Toggle between source view and rendered HTML preview."""
        if self._is_preview_mode:
            self._show_source()
        else:
            self._show_preview()

    def _show_source(self) -> None:
        """Switch to plain Markdown source view."""
        self._is_preview_mode = False
        self._text_edit.setPlainText(self._markdown_text)
        self._preview_button.setText("Preview")
        self._text_edit.setFont(self._create_monospace_font())

    def _show_preview(self) -> None:
        """Render Markdown as HTML and display in the text edit."""
        if not self._markdown_available:
            return

        try:
            import markdown as md

            html = md.markdown(
                self._markdown_text,
                extensions=["tables", "fenced_code"],
            )

            styled_html = (
                '<style>'
                'body { font-family: "Times New Roman", "SimSun", serif; '
                'font-size: 15px; color: #2C1F14; line-height: 1.65; }'
                'h1, h2, h3 { font-family: Georgia, serif; color: #3E2B1F; }'
                'code { background-color: #F0EBE4; padding: 2px 6px; border-radius: 4px; '
                'font-family: Consolas, monospace; font-size: 13px; }'
                'pre { background-color: #F0EBE4; padding: 12px; border-radius: 8px; '
                'overflow-x: auto; }'
                'table { border-collapse: collapse; width: 100%; }'
                'th, td { border: 1px solid #D4CCC4; padding: 8px 12px; text-align: left; }'
                'th { background-color: #F0EBE4; }'
                'blockquote { border-left: 3px solid #D4CCC4; margin-left: 0; '
                'padding-left: 16px; color: #5C4033; }'
                '</style>'
                f'{html}'
            )

            self._is_preview_mode = True
            self._text_edit.setHtml(styled_html)
            self._preview_button.setText("Source")
        except ImportError:
            LOGGER.warning("markdown library not installed; preview unavailable")
            self._markdown_available = False
            self._preview_button.setEnabled(False)
            self._preview_button.setText("Preview (unavailable)")
            self._text_edit.setPlainText(
                "Preview requires the 'markdown' library.\n"
                "Install it: pip install markdown>=3.6"
            )
        except Exception as exc:
            LOGGER.error("Markdown rendering failed: %s", exc)
            self._text_edit.setPlainText(
                f"Preview rendering failed: {exc}\n\n"
                f"--- Source ---\n\n{self._markdown_text}"
            )