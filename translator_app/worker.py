"""Background worker thread for translation requests."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from translator_app.exceptions import (
    ConfigurationError,
    DeepSeekAPIError,
    HistoryError,
)
from translator_app.models import TranslationResult
from translator_app.translation_service import TranslationService


class TranslationWorker(QThread):
    """Run translation work off the main UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, service: TranslationService, text: str, style: str) -> None:
        """Store the service dependency, input text, and style."""
        super().__init__()
        self._service = service
        self._text = text
        self._style = style

    def run(self) -> None:
        """Execute translation and emit the corresponding signal."""
        try:
            result: TranslationResult = self._service.translate_text(
                self._text,
                self._style,
            )
        except (
            ConfigurationError,
            DeepSeekAPIError,
            HistoryError,
            ValueError,
        ) as exc:
            self.failed.emit(str(exc))
            return

        self.succeeded.emit(result)
