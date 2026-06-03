"""Floating translator window implementation."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QCloseEvent,
    QIcon,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from translator_app.config_manager import ConfigManager
from translator_app.exceptions import ConfigurationError, HistoryError, HotkeyError
from translator_app.history_manager import HistoryManager
from translator_app.hotkey_manager import GlobalHotkeyManager
from translator_app.language import describe_language
from translator_app.models import AppConfig, HistoryEntry, TranslationResult
from translator_app.settings_dialog import SettingsDialog
from translator_app.translation_service import TranslationService
from translator_app.translation_style import (
    AVAILABLE_TRANSLATION_STYLES,
    DEFAULT_TRANSLATION_STYLE,
    get_style_display_name,
)
from translator_app.worker import TranslationWorker

LOGGER = logging.getLogger(__name__)

TEXT_FONT_STACK = "'Times New Roman', 'SimSun', 'Songti SC'"
ICON_COLOR = "#5C3D2B"
ICON_ACTIVE_COLOR = "#2C1F14"


def create_line_icon(name: str, color: str) -> QIcon:
    """Create a lightweight custom line icon that matches the app style."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if name == "paste":
        painter.drawRoundedRect(6, 7, 12, 13, 3, 3)
        painter.drawRoundedRect(9, 4, 6, 4, 2, 2)
        painter.drawLine(9, 11, 15, 11)
        painter.drawLine(9, 15, 15, 15)
    elif name == "copy":
        painter.drawRoundedRect(8, 6, 10, 12, 2, 2)
        painter.drawRoundedRect(5, 9, 10, 12, 2, 2)
    elif name == "clear":
        painter.drawLine(7, 7, 17, 17)
        painter.drawLine(17, 7, 7, 17)
    elif name == "swap":
        painter.drawLine(6, 9, 16, 9)
        painter.drawLine(13, 6, 16, 9)
        painter.drawLine(13, 12, 16, 9)
        painter.drawLine(18, 15, 8, 15)
        painter.drawLine(11, 12, 8, 15)
        painter.drawLine(11, 18, 8, 15)
    elif name == "translate":
        path = QPainterPath()
        path.moveTo(6, 17)
        path.lineTo(10, 8)
        path.lineTo(14, 17)
        painter.drawPath(path)
        painter.drawLine(8, 13, 12, 13)
        painter.drawLine(16, 7, 19, 7)
        painter.drawLine(18, 6, 18, 17)
        painter.drawLine(14, 11, 20, 17)
    elif name == "history":
        painter.drawEllipse(5, 5, 14, 14)
        painter.drawLine(12, 8, 12, 12)
        painter.drawLine(12, 12, 15, 14)
    elif name == "settings":
        painter.drawEllipse(8, 8, 8, 8)
        painter.drawLine(12, 3, 12, 6)
        painter.drawLine(12, 18, 12, 21)
        painter.drawLine(3, 12, 6, 12)
        painter.drawLine(18, 12, 21, 12)
        painter.drawLine(5, 5, 7, 7)
        painter.drawLine(17, 17, 19, 19)
        painter.drawLine(17, 7, 19, 5)
        painter.drawLine(5, 19, 7, 17)
    elif name == "home":
        path = QPainterPath()
        path.moveTo(5, 11)
        path.lineTo(12, 5)
        path.lineTo(19, 11)
        path.lineTo(17, 11)
        path.lineTo(17, 18)
        path.lineTo(7, 18)
        path.lineTo(7, 11)
        path.closeSubpath()
        painter.drawPath(path)
    else:
        painter.drawEllipse(7, 7, 10, 10)

    painter.end()
    return QIcon(pixmap)


class DraggableHeaderFrame(QFrame):
    """Simple draggable header for the frameless floating window."""

    def __init__(self, parent_window: QWidget) -> None:
        """Store the parent window that should move during drag."""
        super().__init__(parent_window)
        self._parent_window = parent_window
        self._drag_offset: Optional[QPoint] = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start dragging when the left mouse button is pressed."""
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self._parent_window.frameGeometry().topLeft()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move the parent window while dragging."""
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._parent_window.move(event.globalPos() - self._drag_offset)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Stop dragging once the mouse button is released."""
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class ClickToCopyTextEdit(QTextEdit):
    """Read-only result box that copies its contents on click."""

    copied = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Copy the current result to the clipboard when clicked."""
        if self.toPlainText().strip():
            QApplication.clipboard().setText(self.toPlainText())
            self.copied.emit()

        super().mousePressEvent(event)


def _make_copy_button(text: str) -> QPushButton:
    """Create a Copy button that copies *text* to the clipboard."""
    button = QPushButton("Copy")
    button.setObjectName("historyActionButton")

    def on_clicked():
        QApplication.clipboard().setText(text)
        button.setText("Copied!")
        QTimer.singleShot(1500, lambda: button.setText("Copy"))

    button.clicked.connect(on_clicked)
    return button


class HistoryCard(QFrame):
    """A card widget for one translation history entry."""

    def __init__(self, entry: HistoryEntry, parent: QWidget | None = None) -> None:
        """Render one history item using the themed popup style."""
        super().__init__(parent)
        self.setObjectName("historyCard")

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(18, 16, 18, 16)
        outer_layout.setSpacing(10)

        top_row = QHBoxLayout()
        style_pill = QLabel(get_style_display_name(entry.style))
        style_pill.setObjectName("historyPill")

        timestamp_label = QLabel(entry.timestamp)
        timestamp_label.setObjectName("historyMeta")
        timestamp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top_row.addWidget(style_pill)
        top_row.addStretch()
        top_row.addWidget(timestamp_label)

        direction_label = QLabel(
            f"{describe_language(entry.source_language)} -> {describe_language(entry.target_language)}"
        )
        direction_label.setObjectName("historyDirection")

        source_row = QHBoxLayout()
        source_title = QLabel("SOURCE")
        source_title.setObjectName("historySection")
        source_row.addWidget(source_title)
        source_row.addStretch()
        source_row.addWidget(_make_copy_button(entry.source_text))

        source_label = QLabel(entry.source_text)
        source_label.setObjectName("historySourceText")
        source_label.setWordWrap(True)

        translated_row = QHBoxLayout()
        translated_title = QLabel("TRANSLATION")
        translated_title.setObjectName("historySection")
        translated_row.addWidget(translated_title)
        translated_row.addStretch()
        translated_row.addWidget(_make_copy_button(entry.translated_text))

        translated_label = QLabel(entry.translated_text)
        translated_label.setObjectName("historyTranslatedText")
        translated_label.setWordWrap(True)

        outer_layout.addLayout(top_row)
        outer_layout.addWidget(direction_label)
        outer_layout.addLayout(source_row)
        outer_layout.addWidget(source_label)
        outer_layout.addLayout(translated_row)
        outer_layout.addWidget(translated_label)
        self.setLayout(outer_layout)


class HistoryDialog(QDialog):
    """Display recent translation history in a card layout."""

    def __init__(
        self,
        entries: list[HistoryEntry],
        history_manager: HistoryManager,
        parent: QWidget | None = None,
    ) -> None:
        """Render the recent history using themed cards."""
        super().__init__(parent)
        self._entries = entries
        self._history_manager = history_manager
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.setWindowTitle("History")
        self.resize(620, 680)
        self.setMinimumSize(520, 520)
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: #E8E2D9;
            }}
            QLabel#dialogTitle {{
                color: #2C1F14;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 28px;
                font-weight: 700;
            }}
            QLabel#dialogSubtitle {{
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
            }}
            QPushButton#historyActionButton {{
                background-color: #D4CCC4;
                border: none;
                border-radius: 18px;
                color: #5C3D2B;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 16px;
            }}
            QPushButton#historyActionButton:hover {{
                background-color: #C9C0B7;
            }}
            QFrame#historyCard {{
                background-color: #F0EBE4;
                border: 1px solid #D4CCC4;
                border-radius: 28px;
            }}
            QLabel#historyPill {{
                background-color: #D4CCC4;
                border-radius: 15px;
                color: #5C3D2B;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 12px;
                font-weight: 600;
                padding: 5px 12px;
            }}
            QLabel#historyMeta, QLabel#historyDirection {{
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 12px;
            }}
            QLabel#historySection {{
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 11px;
                font-weight: 700;
                padding-top: 2px;
            }}
            QLabel#historySourceText, QLabel#historyTranslatedText {{
                color: #2C1F14;
                font-family: {TEXT_FONT_STACK};
                font-size: 15px;
                line-height: 1.6;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            """
        )

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(24, 22, 24, 22)
        root_layout.setSpacing(18)

        title_label = QLabel("history")
        title_label.setObjectName("dialogTitle")
        subtitle_label = QLabel("Review your recent translations, styles, and direction changes.")
        subtitle_label.setObjectName("dialogSubtitle")

        title_row = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(4)
        title_block.addWidget(title_label)
        title_block.addWidget(subtitle_label)

        clear_history_button = QPushButton("Clear History")
        clear_history_button.setObjectName("historyActionButton")
        clear_history_button.setIcon(create_line_icon("clear", ICON_COLOR))
        clear_history_button.setIconSize(QSize(16, 16))
        clear_history_button.clicked.connect(self._clear_history)

        title_row.addLayout(title_block)
        title_row.addStretch()
        title_row.addWidget(clear_history_button)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(14)
        self._content_widget.setLayout(self._content_layout)
        self._scroll_area.setWidget(self._content_widget)
        self._empty_label = QLabel("No translations have been saved yet.")
        self._empty_label.setObjectName("dialogSubtitle")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.hide()
        self._rebuild_entries()

        root_layout.addLayout(title_row)
        root_layout.addWidget(self._empty_label)
        root_layout.addWidget(self._scroll_area, stretch=1)
        self.setLayout(root_layout)

    def showEvent(self, event) -> None:  # type: ignore[override]
        """Fade in the popup when it is shown."""
        self.setWindowOpacity(0.0)
        self._fade_animation.stop()
        self._fade_animation.setDuration(180)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_animation.start()
        super().showEvent(event)

    def _rebuild_entries(self) -> None:
        """Refresh the card list from the current entry snapshot."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._entries:
            self._empty_label.show()
            self._scroll_area.hide()
            return

        self._empty_label.hide()
        self._scroll_area.show()
        for entry in self._entries:
            self._content_layout.addWidget(HistoryCard(entry))
        self._content_layout.addStretch()

    def _clear_history(self) -> None:
        """Clear persisted history and refresh the popup content."""
        try:
            self._history_manager.clear_entries()
        except HistoryError as exc:
            QMessageBox.warning(self, "History Error", str(exc))
            return

        self._entries = []
        self._rebuild_entries()


class FloatingTranslatorWindow(QWidget):
    """Main floating translator UI."""

    def __init__(
        self,
        service: TranslationService,
        config_manager: ConfigManager,
        history_manager: HistoryManager,
    ) -> None:
        """Create the floating window and supporting helpers."""
        super().__init__()
        self._service = service
        self._config_manager = config_manager
        self._history_manager = history_manager
        self._worker: Optional[TranslationWorker] = None
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._hotkey_manager: Optional[GlobalHotkeyManager] = None
        self._active_style = DEFAULT_TRANSLATION_STYLE
        self._mode_buttons: dict[str, QPushButton] = {}
        self._nav_buttons: dict[str, QToolButton] = {}

        self._input_box = QTextEdit()
        self._result_box = ClickToCopyTextEdit()
        self._translate_button = QPushButton("Translate")
        self._copy_button = QPushButton("Copy")
        self._status_label = QLabel()
        self._status_effect = QGraphicsOpacityEffect(self._status_label)
        self._status_animation = QPropertyAnimation(self._status_effect, b"opacity")
        self._result_card = QFrame()
        self._result_effect = QGraphicsOpacityEffect(self._result_card)
        self._result_animation = QPropertyAnimation(self._result_effect, b"opacity")
        self._visibility_animation_group = QParallelAnimationGroup(self)
        self._visibility_opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self._visibility_position_animation = QPropertyAnimation(self, b"pos")
        self._visibility_animation_group.addAnimation(self._visibility_opacity_animation)
        self._visibility_animation_group.addAnimation(self._visibility_position_animation)
        self._visibility_animation_group.finished.connect(self._handle_visibility_animation_finished)
        self._is_hiding_after_animation = False
        self._restored_position = QPoint()
        self._nav_icon_names: dict[str, str] = {}

        self._configure_window()
        self._build_ui()
        self._create_tray_icon()
        self._position_bottom_right()
        self._register_hotkey(self._config_manager.load_config())
        self._set_active_style(self._active_style)
        self._show_status("Ready", is_error=False)

    def _configure_window(self) -> None:
        """Apply floating tool window settings and global stylesheet."""
        self.setWindowTitle("translator")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setObjectName("mainWindow")
        self.resize(580, 860)
        self.setMinimumSize(520, 720)
        self.setStyleSheet(
            f"""
            QWidget#mainWindow {{
                background-color: #E8E2D9;
                border: 1px solid #B79F90;
                border-radius: 24px;
            }}
            QFrame#headerFrame {{
                background: transparent;
                border: none;
            }}
            QLabel#titleLabel {{
                color: #2C1F14;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 29px;
                font-weight: 700;
            }}
            QLabel#subtitleLabel {{
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 12px;
            }}
            QPushButton#modeButton {{
                background-color: #D4CCC4;
                border: none;
                border-radius: 21px;
                color: #5C4033;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                padding: 11px 18px;
            }}
            QPushButton#modeButton[modeSelected="true"] {{
                background-color: #3E2B1F;
                color: #F0EBE4;
                font-weight: 600;
            }}
            QFrame#cardFrame {{
                background-color: #F0EBE4;
                border: 1px solid #D4CCC4;
                border-radius: 30px;
            }}
            QLabel#sectionLabel {{
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 12px;
                font-weight: 700;
            }}
            QTextEdit#sourceBox, QTextEdit#resultBox {{
                background: transparent;
                border: none;
                color: #2C1F14;
                font-family: {TEXT_FONT_STACK};
                font-size: 16px;
                line-height: 1.65;
                padding: 6px 4px 4px 4px;
            }}
            QTextEdit#sourceBox:focus, QTextEdit#resultBox:focus {{
                border: none;
            }}
            QPushButton#secondaryButton, QPushButton#swapButton {{
                background-color: #D4CCC4;
                border: none;
                border-radius: 22px;
                color: #5C3D2B;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
                padding: 11px 18px;
            }}
            QPushButton#secondaryButton:hover, QPushButton#swapButton:hover {{
                background-color: #C9C0B7;
            }}
            QPushButton#primaryButton {{
                background-color: #3E2B1F;
                border: none;
                border-radius: 24px;
                color: #F0EBE4;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 18px;
                font-weight: 600;
                padding: 18px 16px;
            }}
            QPushButton#primaryButton:disabled {{
                background-color: #B8AFA6;
                color: #F0EBE4;
            }}
            QLabel#statusToast {{
                background-color: #3E2B1F;
                border-radius: 18px;
                color: #F0EBE4;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 14px;
            }}
            QLabel#statusToast[error="true"] {{
                background-color: #7E5647;
            }}
            QFrame#navFrame {{
                background-color: #F0EBE4;
                border: 1px solid #D4CCC4;
                border-radius: 28px;
            }}
            QToolButton#navButton {{
                background: transparent;
                border: none;
                border-radius: 20px;
                color: #8C7B6E;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 11px;
                padding: 8px 10px;
            }}
            QToolButton#navButton[navActive="true"] {{
                background-color: #D4CCC4;
                color: #2C1F14;
                font-weight: 600;
            }}
            QSizeGrip {{
                width: 18px;
                height: 18px;
            }}
            """
        )

    def _build_ui(self) -> None:
        """Build the floating window layout."""
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(24, 22, 20, 18)
        root_layout.setSpacing(18)

        header = DraggableHeaderFrame(self)
        header.setObjectName("headerFrame")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(14)

        title_label = QLabel("translator")
        title_label.setObjectName("titleLabel")
        subtitle_label = QLabel("Translate with refined styles and quick reverse direction.")
        subtitle_label.setObjectName("subtitleLabel")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(10)
        for style in AVAILABLE_TRANSLATION_STYLES:
            button = QPushButton(get_style_display_name(style))
            button.setObjectName("modeButton")
            button.clicked.connect(lambda checked=False, value=style: self._set_active_style(value))
            mode_layout.addWidget(button)
            self._mode_buttons[style] = button
        header_layout.addLayout(mode_layout)
        header.setLayout(header_layout)

        input_card = self._build_input_card()

        swap_row = QHBoxLayout()
        swap_row.setContentsMargins(0, 0, 0, 0)
        swap_row.addStretch()
        swap_button = QPushButton("Swap")
        swap_button.setObjectName("swapButton")
        swap_button.setIcon(create_line_icon("swap", ICON_COLOR))
        swap_button.setIconSize(QSize(16, 16))
        swap_button.clicked.connect(self._swap_translation_direction)
        swap_row.addWidget(swap_button)
        swap_row.addStretch()

        self._translate_button.setObjectName("primaryButton")
        self._translate_button.clicked.connect(self._start_translation)

        result_card = self._build_result_card()

        self._status_label.setObjectName("statusToast")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setGraphicsEffect(self._status_effect)
        self._status_effect.setOpacity(1.0)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(12)
        footer_row.addWidget(self._build_bottom_nav(), stretch=1)

        size_grip = QSizeGrip(self)
        footer_row.addWidget(size_grip, alignment=Qt.AlignRight | Qt.AlignBottom)

        root_layout.addWidget(header)
        root_layout.addWidget(input_card, stretch=1)
        root_layout.addLayout(swap_row)
        root_layout.addWidget(self._translate_button)
        root_layout.addWidget(result_card, stretch=1)
        root_layout.addWidget(self._status_label)
        root_layout.addLayout(footer_row)
        self.setLayout(root_layout)

    def _build_input_card(self) -> QFrame:
        """Build the styled input card."""
        card = QFrame()
        card.setObjectName("cardFrame")
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        section_label = QLabel("SOURCE TEXT")
        section_label.setObjectName("sectionLabel")

        clear_button = QPushButton("Clear")
        clear_button.setObjectName("secondaryButton")
        clear_button.setIcon(create_line_icon("clear", ICON_COLOR))
        clear_button.setIconSize(QSize(16, 16))
        clear_button.clicked.connect(self._clear_input_box)

        paste_button = QPushButton("Paste")
        paste_button.setObjectName("secondaryButton")
        paste_button.setIcon(create_line_icon("paste", ICON_COLOR))
        paste_button.setIconSize(QSize(16, 16))
        paste_button.clicked.connect(self._paste_clipboard)

        header_row.addWidget(section_label)
        header_row.addStretch()
        header_row.addWidget(clear_button)
        header_row.addWidget(paste_button)

        self._input_box.setObjectName("sourceBox")
        self._input_box.setAcceptRichText(False)
        self._input_box.setPlaceholderText("Paste English or Chinese text here...")

        layout.addLayout(header_row)
        layout.addWidget(self._input_box, stretch=1)
        card.setLayout(layout)
        return card

    def _build_result_card(self) -> QFrame:
        """Build the styled result card."""
        self._result_card.setObjectName("cardFrame")
        self._result_card.setGraphicsEffect(self._result_effect)
        self._result_effect.setOpacity(1.0)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        section_label = QLabel("TRANSLATED TEXT")
        section_label.setObjectName("sectionLabel")

        self._copy_button.setObjectName("secondaryButton")
        self._copy_button.setIcon(create_line_icon("copy", ICON_COLOR))
        self._copy_button.setIconSize(QSize(16, 16))
        self._copy_button.clicked.connect(self._copy_result)
        self._copy_button.setEnabled(False)

        header_row.addWidget(section_label)
        header_row.addStretch()
        header_row.addWidget(self._copy_button)

        self._result_box.setObjectName("resultBox")
        self._result_box.setAcceptRichText(False)
        self._result_box.setReadOnly(True)
        self._result_box.setPlaceholderText("Translation result appears here. Tap to copy.")
        self._result_box.copied.connect(self._handle_result_copied)

        layout.addLayout(header_row)
        layout.addWidget(self._result_box, stretch=1)
        self._result_card.setLayout(layout)
        return self._result_card

    def _build_bottom_nav(self) -> QFrame:
        """Build the bottom navigation bar inspired by the reference UI."""
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        button_specs = (
            ("translate", "Translate", "home", None),
            ("history", "History", "history", self._show_history),
            ("settings", "Settings", "settings", self._show_settings),
        )

        for key, label, icon_name, callback in button_specs:
            button = QToolButton()
            button.setObjectName("navButton")
            button.setText(label)
            button.setIcon(create_line_icon(icon_name, ICON_COLOR))
            button.setIconSize(QSize(18, 18))
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            if callback is not None:
                button.clicked.connect(callback)
            self._nav_buttons[key] = button
            self._nav_icon_names[key] = icon_name
            layout.addWidget(button)

        nav_frame.setLayout(layout)
        self._set_active_nav("translate")
        return nav_frame

    def _set_active_nav(self, key: str) -> None:
        """Highlight the currently active bottom navigation item."""
        for nav_key, button in self._nav_buttons.items():
            is_active = nav_key == key
            button.setProperty("navActive", is_active)
            icon_color = ICON_ACTIVE_COLOR if is_active else ICON_COLOR
            button.setIcon(create_line_icon(self._nav_icon_names[nav_key], icon_color))
            button.style().unpolish(button)
            button.style().polish(button)

    def _create_tray_icon(self) -> None:
        """Create the system tray icon and its actions."""
        tray_icon = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        menu = QMenu(self)

        toggle_action = QAction("Show / Hide", self)
        toggle_action.triggered.connect(self.toggle_visibility)
        menu.addAction(toggle_action)

        history_action = QAction("History", self)
        history_action.triggered.connect(self._show_history)
        menu.addAction(history_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        tray_icon.setToolTip("translator")
        tray_icon.setContextMenu(menu)
        tray_icon.activated.connect(self._handle_tray_activation)
        tray_icon.show()

        self._tray_icon = tray_icon

    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Toggle the window when the tray icon is clicked."""
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visibility()

    def _position_bottom_right(self) -> None:
        """Place the floating window near the bottom-right corner."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        available_geometry = screen.availableGeometry()
        x_position = available_geometry.right() - self.width() - 24
        y_position = available_geometry.bottom() - self.height() - 24
        self.move(x_position, y_position)
        self._restored_position = self.pos()

    def _register_hotkey(self, config: AppConfig) -> None:
        """Register the configured global hotkey."""
        self._stop_hotkey()
        self._hotkey_manager = GlobalHotkeyManager(config.hotkey)
        self._hotkey_manager.activated.connect(self.toggle_visibility)

        try:
            self._hotkey_manager.start()
        except HotkeyError as exc:
            LOGGER.warning("Global hotkey failed to start: %s", exc)
            self._show_status(str(exc), is_error=True)
            QMessageBox.warning(
                self,
                "Hotkey Warning",
                f"{exc}\nThe tray icon still lets you show or hide the window.",
            )

    def _stop_hotkey(self) -> None:
        """Stop the current global hotkey listener if one exists."""
        if self._hotkey_manager is not None:
            self._hotkey_manager.stop()
            self._hotkey_manager = None

    def _set_active_style(self, style: str) -> None:
        """Update the selected translation style in the UI."""
        self._active_style = style
        for style_name, button in self._mode_buttons.items():
            button.setProperty("modeSelected", style_name == style)
            button.style().unpolish(button)
            button.style().polish(button)

        self._show_status(
            f"{get_style_display_name(style)} style selected.",
            is_error=False,
        )

    def _paste_clipboard(self) -> None:
        """Paste plain text from the system clipboard into the input area."""
        clipboard_text = QApplication.clipboard().text().strip()
        if not clipboard_text:
            self._show_status("No text found in the clipboard.", is_error=True)
            return

        self._input_box.setPlainText(clipboard_text)
        self._show_status("Clipboard content pasted.", is_error=False)

    def _clear_input_box(self) -> None:
        """Clear only the source input area."""
        self._input_box.clear()
        self._show_status("Input text cleared.", is_error=False)

    def _copy_result(self) -> None:
        """Copy the current result text using the copy button."""
        result_text = self._result_box.toPlainText().strip()
        if not result_text:
            self._show_status("No translated text to copy yet.", is_error=True)
            return

        QApplication.clipboard().setText(result_text)
        self._handle_result_copied()

    def _swap_translation_direction(self) -> None:
        """Swap source and translated text to prepare the reverse translation."""
        source_text = self._input_box.toPlainText().strip()
        translated_text = self._result_box.toPlainText().strip()

        if not translated_text:
            self._show_status(
                "Translate once before using Swap to reverse the direction.",
                is_error=True,
            )
            return

        self._input_box.setPlainText(translated_text)
        self._result_box.setPlainText(source_text)
        self._copy_button.setEnabled(bool(source_text))
        self._show_status(
            "Source and result swapped. Translate again for the reverse direction.",
            is_error=False,
        )

    def _start_translation(self) -> None:
        """Start a background translation job for the current input."""
        text = self._input_box.toPlainText().strip()
        if not text:
            self._show_status("Please enter or paste text first.", is_error=True)
            return

        if self._worker is not None and self._worker.isRunning():
            self._show_status("Please wait for the current translation to finish.", is_error=True)
            return

        self._translate_button.setEnabled(False)
        self._show_status("Translating...", is_error=False)
        self._worker = TranslationWorker(self._service, text, self._active_style)
        self._worker.succeeded.connect(self._handle_translation_success)
        self._worker.failed.connect(self._handle_translation_failure)
        self._worker.finished.connect(self._finish_translation)
        self._worker.start()

    def _handle_translation_success(self, result: TranslationResult) -> None:
        """Update the UI with a completed translation."""
        self._result_box.setPlainText(result.translated_text)
        self._copy_button.setEnabled(True)
        self._animate_result_card()
        source_label = describe_language(result.source_language)
        target_label = describe_language(result.target_language)
        style_label = get_style_display_name(result.style)
        self._show_status(
            f"{style_label} translation ready: {source_label} -> {target_label}. Tap the result to copy.",
            is_error=False,
        )

    def _handle_translation_failure(self, error_message: str) -> None:
        """Show a user-friendly message for translation failures."""
        self._show_status(error_message, is_error=True)

    def _finish_translation(self) -> None:
        """Reset UI state after the worker finishes."""
        self._translate_button.setEnabled(True)

    def _handle_result_copied(self) -> None:
        """Notify the user when the result text is copied."""
        self._show_status("Translation copied to the clipboard.", is_error=False)

    def _show_settings(self) -> None:
        """Open the settings dialog and persist changes."""
        self._set_active_nav("settings")
        try:
            current_config = self._config_manager.load_config()
        except ConfigurationError as exc:
            QMessageBox.warning(self, "Config Error", str(exc))
            current_config = AppConfig()

        dialog = SettingsDialog(current_config, self)
        if dialog.exec_() != QDialog.Accepted:
            self._set_active_nav("translate")
            return

        try:
            new_config = dialog.build_config()
            self._config_manager.save_config(new_config)
            self._register_hotkey(new_config)
        except ConfigurationError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_active_nav("translate")
            return

        self._show_status("Settings saved.", is_error=False)
        self._set_active_nav("translate")

    def _show_history(self) -> None:
        """Display the most recent translations in a dialog."""
        self._set_active_nav("history")
        try:
            entries = self._history_manager.load_entries()
        except HistoryError as exc:
            QMessageBox.warning(self, "History Error", str(exc))
            self._set_active_nav("translate")
            return

        if not entries:
            self._show_status("No translations have been saved yet.", is_error=True)
            self._set_active_nav("translate")
            return

        HistoryDialog(entries, self._history_manager, self).exec_()
        self._set_active_nav("translate")

    def _show_status(self, message: str, is_error: bool) -> None:
        """Show the latest status message using the themed status pill."""
        self._status_label.setText(message)
        self._status_label.setProperty("error", is_error)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        self._status_animation.stop()
        self._status_effect.setOpacity(0.0)
        self._status_animation.setDuration(180)
        self._status_animation.setStartValue(0.0)
        self._status_animation.setEndValue(1.0)
        self._status_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._status_animation.start()

    def _animate_result_card(self) -> None:
        """Run a subtle fade-in animation for the result card after translation."""
        self._result_animation.stop()
        self._result_effect.setOpacity(0.35)
        self._result_animation.setDuration(220)
        self._result_animation.setStartValue(0.35)
        self._result_animation.setEndValue(1.0)
        self._result_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._result_animation.start()

    def _start_visibility_animation(
        self,
        start_pos: QPoint,
        end_pos: QPoint,
        start_opacity: float,
        end_opacity: float,
        hide_when_finished: bool,
    ) -> None:
        """Animate the floating window position and opacity together."""
        self._visibility_animation_group.stop()
        self._is_hiding_after_animation = hide_when_finished

        self._visibility_position_animation.setDuration(170)
        self._visibility_position_animation.setStartValue(start_pos)
        self._visibility_position_animation.setEndValue(end_pos)
        self._visibility_position_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._visibility_opacity_animation.setDuration(170)
        self._visibility_opacity_animation.setStartValue(start_opacity)
        self._visibility_opacity_animation.setEndValue(end_opacity)
        self._visibility_opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._visibility_animation_group.start()

    def _handle_visibility_animation_finished(self) -> None:
        """Finalize widget state once the visibility animation ends."""
        if self._is_hiding_after_animation:
            self.hide()
            self.move(self._restored_position)
            self.setWindowOpacity(1.0)
            self._is_hiding_after_animation = False
            return

        self.setWindowOpacity(1.0)
        self.move(self._restored_position)

    def _animate_show_window(self) -> None:
        """Fade and lift the window into view."""
        target_position = self._restored_position if not self._restored_position.isNull() else self.pos()
        start_position = target_position + QPoint(0, 18)

        self.move(start_position)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self._start_visibility_animation(
            start_pos=start_position,
            end_pos=target_position,
            start_opacity=0.0,
            end_opacity=1.0,
            hide_when_finished=False,
        )

    def _animate_hide_window(self) -> None:
        """Fade and lower the window before hiding it."""
        self._restored_position = self.pos()
        end_position = self.pos() + QPoint(0, 18)
        self._start_visibility_animation(
            start_pos=self.pos(),
            end_pos=end_position,
            start_opacity=self.windowOpacity(),
            end_opacity=0.0,
            hide_when_finished=True,
        )

    def toggle_visibility(self) -> None:
        """Show or hide the floating window."""
        if self.isVisible() and not self._is_hiding_after_animation:
            self._animate_hide_window()
            return

        self._animate_show_window()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up long-lived helpers when the application exits."""
        self._stop_hotkey()
        if self._tray_icon is not None:
            self._tray_icon.hide()

        super().closeEvent(event)
