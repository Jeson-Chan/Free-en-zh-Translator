"""Background worker thread for image translation pipeline."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from translator_app.exceptions import (
    ConfigurationError,
    ImageProcessingError,
    QwenAPIError,
)
from translator_app.image_pipeline import ImageTranslationPipeline
from translator_app.models import ImageTranslationResult


class ImageTranslationWorker(QThread):
    """Run image translation pipeline off the main UI thread."""

    progress = pyqtSignal(str, int, int)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        pipeline: ImageTranslationPipeline,
        image_base64: str,
        source_image_path: str,
    ) -> None:
        """Store pipeline dependency and input data."""
        super().__init__()
        self._pipeline = pipeline
        self._image_base64 = image_base64
        self._source_image_path = source_image_path

    def run(self) -> None:
        """Execute the pipeline and emit the corresponding signal."""
        try:
            result: ImageTranslationResult = self._pipeline.execute(
                image_base64=self._image_base64,
                source_image_path=self._source_image_path,
                on_progress=self._on_progress,
            )
        except (ConfigurationError, QwenAPIError, ImageProcessingError, ValueError) as exc:
            self.failed.emit(str(exc))
            return

        if result.error:
            # Partial failure: recognition succeeded but translation failed
            self.succeeded.emit(result)
        else:
            self.succeeded.emit(result)

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Forward pipeline progress to the UI thread."""
        self.progress.emit(message, current, total)