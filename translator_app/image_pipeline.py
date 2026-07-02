"""Two-stage image translation pipeline: recognition → translation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Optional

from translator_app.exceptions import DeepSeekAPIError, QwenAPIError
from translator_app.image_recognition_service import ImageRecognitionService
from translator_app.image_translation_service import ImageTranslationService
from translator_app.models import ImageTranslationResult

LOGGER = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, int], None]
_TOTAL_STAGES = 2


class ImageTranslationPipeline:
    """Orchestrate recognition and translation as a serial two-stage pipeline."""

    def __init__(
        self,
        recognition_service: ImageRecognitionService,
        translation_service: ImageTranslationService,
    ) -> None:
        """Store service dependencies."""
        self._recognition_service = recognition_service
        self._translation_service = translation_service

    def execute(
        self,
        image_base64: str,
        source_image_path: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ImageTranslationResult:
        """Run the full pipeline and return a combined result.

        If recognition fails, returns an error result with no translation.
        If translation fails, returns the recognition text with an error message.
        Unexpected exceptions are caught and returned as structured error results.
        """
        timestamp = datetime.now().isoformat(timespec="seconds")

        try:
            return self._execute_stages(
                image_base64, source_image_path, on_progress, timestamp
            )
        except Exception as exc:
            LOGGER.exception("Unexpected pipeline error: %s", exc)
            return ImageTranslationResult(
                source_image_path=source_image_path,
                recognized_text="",
                translated_text="",
                source_language="unknown",
                target_language="unknown",
                recognition_tokens=0,
                translation_tokens=0,
                timestamp=timestamp,
                error=f"Pipeline error: {exc}",
            )

    def _execute_stages(
        self,
        image_base64: str,
        source_image_path: str,
        on_progress: Optional[ProgressCallback],
        timestamp: str,
    ) -> ImageTranslationResult:
        """Execute the recognition and translation stages."""
        # Stage 1: Recognition
        if on_progress:
            on_progress("Recognizing image content...", 1, _TOTAL_STAGES)

        try:
            recognized_text = self._recognition_service.recognize(image_base64)
        except QwenAPIError as exc:
            LOGGER.error("Recognition failed: %s", exc)
            return ImageTranslationResult(
                source_image_path=source_image_path,
                recognized_text="",
                translated_text="",
                source_language="unknown",
                target_language="unknown",
                recognition_tokens=0,
                translation_tokens=0,
                timestamp=timestamp,
                error=f"Image recognition failed: {exc}",
            )

        # Stage 2: Translation
        if on_progress:
            on_progress("Translating content...", 2, _TOTAL_STAGES)

        try:
            translated_text = self._translation_service.translate(recognized_text)
        except DeepSeekAPIError as exc:
            LOGGER.error("Translation failed: %s", exc)
            return ImageTranslationResult(
                source_image_path=source_image_path,
                recognized_text=recognized_text,
                translated_text="",
                source_language="unknown",
                target_language="unknown",
                recognition_tokens=0,
                translation_tokens=0,
                timestamp=timestamp,
                error=f"Image translation failed: {exc}",
            )

        LOGGER.info(
            "Pipeline complete: %d chars recognized -> %d chars translated",
            len(recognized_text),
            len(translated_text),
        )

        return ImageTranslationResult(
            source_image_path=source_image_path,
            recognized_text=recognized_text,
            translated_text=translated_text,
            source_language="en",
            target_language="zh",
            recognition_tokens=0,
            translation_tokens=0,
            timestamp=timestamp,
        )