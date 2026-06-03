"""Application entry point for the floating translator."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from translator_app.config_manager import ConfigManager
from translator_app.exceptions import ConfigurationError
from translator_app.floating_window import FloatingTranslatorWindow
from translator_app.history_manager import HistoryManager
from translator_app.logging_config import configure_logging
from translator_app.models import AppConfig
from translator_app.settings_dialog import SettingsDialog
from translator_app.translation_service import TranslationService

LOGGER = logging.getLogger(__name__)


def ensure_configuration(
    config_manager: ConfigManager,
) -> bool:
    """Ensure a usable config exists before the main window is shown."""
    try:
        current_config = config_manager.load_config()
    except ConfigurationError as exc:
        QMessageBox.warning(None, "Config Error", str(exc))
        current_config = AppConfig()

    if current_config.api_key:
        return True

    dialog = SettingsDialog(current_config)
    if dialog.exec_() != QDialog.Accepted:
        return False

    try:
        config_manager.save_config(dialog.build_config())
    except ConfigurationError as exc:
        QMessageBox.critical(None, "Save Failed", str(exc))
        return False

    return True


def main() -> int:
    """Start the PyQt desktop application."""
    root_path = Path(__file__).resolve().parent
    configure_logging(root_path)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    LOGGER.info("Starting Academic Floating Translator")
    config_manager = ConfigManager(root_path)
    history_manager = HistoryManager(root_path)

    if not ensure_configuration(config_manager):
        LOGGER.info("Application closed before configuration was completed.")
        return 0

    service = TranslationService(config_manager, history_manager)
    window = FloatingTranslatorWindow(service, config_manager, history_manager)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
