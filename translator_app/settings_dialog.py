"""Settings dialog for editing API and hotkey configuration."""

from __future__ import annotations

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation
from PyQt5.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from translator_app.models import AppConfig


class SettingsDialog(QDialog):
    """Collect configuration values from the user."""

    def __init__(self, config: AppConfig, parent: QDialog | None = None) -> None:
        """Build the form using the current config values."""
        super().__init__(parent)
        self._fade_effect = QGraphicsOpacityEffect(self)
        self._fade_animation = QPropertyAnimation(self._fade_effect, b"opacity")

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(560, 700)
        self.setMinimumSize(500, 620)
        self.setGraphicsEffect(self._fade_effect)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #E8E2D9;
                color: #2C1F14;
            }
            QLabel#dialogTitle {
                color: #2C1F14;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#dialogSubtitle {
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
            }
            QFrame#settingsCard {
                background-color: #F0EBE4;
                border: 1px solid #D4CCC4;
                border-radius: 28px;
            }
            QLabel#cardTitle {
                color: #5C4033;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#cardHint {
                color: #8C7B6E;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 12px;
            }
            QLabel#fieldLabel {
                color: #5C4033;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                font-weight: 600;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #FBF8F3;
                border: 1px solid #D4CCC4;
                border-radius: 14px;
                color: #2C1F14;
                padding: 10px 12px;
                font-family: 'Times New Roman', 'SimSun', 'Songti SC';
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton#primaryButton {
                background-color: #3E2B1F;
                border: none;
                border-radius: 18px;
                color: #F0EBE4;
                min-width: 110px;
                padding: 12px 18px;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover {
                background-color: #4A3425;
            }
            QPushButton#secondaryButton {
                background-color: #D4CCC4;
                border: none;
                border-radius: 18px;
                color: #5C3D2B;
                min-width: 110px;
                padding: 12px 18px;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#secondaryButton:hover {
                background-color: #C8BFB7;
            }
            """
        )

        self._api_key_input = QLineEdit(config.api_key)
        self._api_key_input.setEchoMode(QLineEdit.Password)
        self._api_key_input.setPlaceholderText("Paste your DeepSeek API key")

        self._api_url_input = QLineEdit(config.api_url)
        self._model_input = QLineEdit(config.model)
        self._hotkey_input = QLineEdit(config.hotkey)

        self._timeout_input = QSpinBox()
        self._timeout_input.setRange(5, 180)
        self._timeout_input.setValue(config.timeout_seconds)

        self._temperature_input = QDoubleSpinBox()
        self._temperature_input.setRange(0.0, 2.0)
        self._temperature_input.setDecimals(2)
        self._temperature_input.setSingleStep(0.1)
        self._temperature_input.setValue(config.temperature)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the popup layout using card sections."""
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(24, 22, 24, 22)
        root_layout.setSpacing(18)

        title_label = QLabel("settings")
        title_label.setObjectName("dialogTitle")

        subtitle_label = QLabel(
            "Manage your DeepSeek connection, default model, response timing, and hotkey behavior."
        )
        subtitle_label.setObjectName("dialogSubtitle")
        subtitle_label.setWordWrap(True)

        root_layout.addWidget(title_label)
        root_layout.addWidget(subtitle_label)
        root_layout.addWidget(
            self._build_card(
                "Connectivity",
                "Keep your API endpoint and access key in sync with your DeepSeek account.",
                (
                    ("API Key", self._api_key_input),
                    ("API URL", self._api_url_input),
                    ("Model", self._model_input),
                ),
            )
        )
        root_layout.addWidget(
            self._build_card(
                "Experience",
                "Tune response speed, generation temperature, and the global shortcut for showing the app.",
                (
                    ("Hotkey", self._hotkey_input),
                    ("Timeout (s)", self._timeout_input),
                    ("Temperature", self._temperature_input),
                ),
            )
        )

        footer = QWidget()
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Save")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._validate_before_accept)

        footer_layout.addWidget(cancel_button)
        footer_layout.addWidget(save_button)
        footer.setLayout(footer_layout)

        root_layout.addStretch()
        root_layout.addWidget(footer)
        self.setLayout(root_layout)

    def _build_card(
        self,
        title: str,
        hint: str,
        fields: tuple[tuple[str, QWidget], ...],
    ) -> QFrame:
        """Build one grouped settings card."""
        card = QFrame()
        card.setObjectName("settingsCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")

        hint_label = QLabel(hint)
        hint_label.setObjectName("cardHint")
        hint_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 8, 0, 0)
        form_layout.setSpacing(12)
        form_layout.setHorizontalSpacing(16)

        for label_text, field in fields:
            label = QLabel(label_text)
            label.setObjectName("fieldLabel")
            form_layout.addRow(label, field)

        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        layout.addLayout(form_layout)
        card.setLayout(layout)
        return card

    def build_config(self) -> AppConfig:
        """Return a config object from the form inputs."""
        return AppConfig(
            api_key=self._api_key_input.text().strip(),
            api_url=self._api_url_input.text().strip(),
            model=self._model_input.text().strip(),
            hotkey=self._hotkey_input.text().strip(),
            timeout_seconds=self._timeout_input.value(),
            temperature=self._temperature_input.value(),
        )

    def _validate_before_accept(self) -> None:
        """Validate required fields before closing the dialog."""
        if not self._api_key_input.text().strip():
            QMessageBox.warning(self, "Missing API Key", "DeepSeek API key is required.")
            return

        if not self._model_input.text().strip():
            QMessageBox.warning(self, "Missing Model", "Model name is required.")
            return

        if not self._api_url_input.text().strip():
            QMessageBox.warning(self, "Missing API URL", "API URL is required.")
            return

        if not self._hotkey_input.text().strip():
            QMessageBox.warning(self, "Missing Hotkey", "Hotkey is required.")
            return

        self.accept()

    def showEvent(self, event) -> None:  # type: ignore[override]
        """Fade in the dialog when it is shown."""
        self._fade_animation.stop()
        self._fade_effect.setOpacity(0.0)
        self._fade_animation.setDuration(180)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_animation.start()
        super().showEvent(event)
