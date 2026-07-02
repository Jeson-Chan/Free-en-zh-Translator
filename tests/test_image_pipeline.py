"""Tests for image translation pipeline orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

from translator_app.exceptions import DeepSeekAPIError, QwenAPIError
from translator_app.image_pipeline import ImageTranslationPipeline
from translator_app.models import ImageTranslationResult


def _make_pipeline(
    recognize_return: str = "# Heading\nSome text",
    translate_return: str = "# 标题\n一些文本",
) -> tuple[ImageTranslationPipeline, MagicMock, MagicMock]:
    """Build a pipeline with mocked services."""
    recognition_service = MagicMock()
    recognition_service.recognize.return_value = recognize_return

    translation_service = MagicMock()
    translation_service.translate.return_value = translate_return

    pipeline = ImageTranslationPipeline(
        recognition_service=recognition_service,
        translation_service=translation_service,
    )
    return pipeline, recognition_service, translation_service


def test_pipeline_runs_both_stages() -> None:
    """Pipeline calls recognize then translate and returns combined result."""
    pipeline, rec_svc, trans_svc = _make_pipeline()

    result = pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
    )

    assert isinstance(result, ImageTranslationResult)
    assert result.recognized_text == "# Heading\nSome text"
    assert result.translated_text == "# 标题\n一些文本"
    assert result.source_image_path == "test.png"
    assert result.error is None
    rec_svc.recognize.assert_called_once_with("base64data")
    trans_svc.translate.assert_called_once_with("# Heading\nSome text")


def test_pipeline_emits_progress_callbacks() -> None:
    """Pipeline calls on_progress for each stage."""
    pipeline, _, _ = _make_pipeline()
    progress_calls: list[tuple[str, int, int]] = []

    def on_progress(message: str, current: int, total: int) -> None:
        progress_calls.append((message, current, total))

    pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
        on_progress=on_progress,
    )

    assert len(progress_calls) == 2
    assert progress_calls[0][1] == 1  # stage 1
    assert progress_calls[1][1] == 2  # stage 2
    assert progress_calls[0][2] == 2  # total stages


def test_pipeline_recognition_failure_returns_error() -> None:
    """If recognition fails, pipeline returns result with error and empty translation."""
    recognition_service = MagicMock()
    recognition_service.recognize.side_effect = QwenAPIError("API timeout")

    translation_service = MagicMock()

    pipeline = ImageTranslationPipeline(
        recognition_service=recognition_service,
        translation_service=translation_service,
    )

    result = pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
    )

    assert result.error is not None
    assert "API timeout" in result.error
    assert result.recognized_text == ""
    assert result.translated_text == ""
    translation_service.translate.assert_not_called()


def test_pipeline_translation_failure_preserves_recognition() -> None:
    """If translation fails, pipeline returns recognition text with error."""
    pipeline, _, trans_svc = _make_pipeline()
    trans_svc.translate.side_effect = DeepSeekAPIError("Translation timeout")

    result = pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
    )

    assert result.recognized_text == "# Heading\nSome text"
    assert result.translated_text == ""
    assert result.error is not None
    assert "Translation timeout" in result.error