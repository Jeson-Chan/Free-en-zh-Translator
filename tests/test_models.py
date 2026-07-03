"""Tests for data model extensions."""

from __future__ import annotations

from translator_app.models import AppConfig, HistoryEntry, ImageTranslationResult


def test_app_config_has_qwen_fields_with_defaults() -> None:
    """AppConfig includes Qwen-related fields with sensible defaults."""
    config = AppConfig()

    assert config.qwen_api_key == ""
    assert config.qwen_api_url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert config.qwen_model == "qwen-vl-max"
    assert config.image_max_size_mb == 20
    assert config.screenshot_hotkey == "<ctrl>+<shift>+s"


def test_app_config_from_dict_reads_qwen_fields() -> None:
    """from_dict populates Qwen fields from a raw dictionary."""
    payload = {
        "qwen_api_key": "sk-qwen-test",
        "qwen_api_url": "https://custom.endpoint/v1/chat/completions",
        "qwen_model": "qwen-vl-plus",
        "image_max_size_mb": 10,
        "screenshot_hotkey": "<alt>+s",
    }

    config = AppConfig.from_dict(payload)

    assert config.qwen_api_key == "sk-qwen-test"
    assert config.qwen_api_url == "https://custom.endpoint/v1/chat/completions"
    assert config.qwen_model == "qwen-vl-plus"
    assert config.image_max_size_mb == 10
    assert config.screenshot_hotkey == "<alt>+s"


def test_app_config_from_dict_uses_defaults_for_missing_qwen_fields() -> None:
    """from_dict falls back to defaults when Qwen fields are absent."""
    config = AppConfig.from_dict({})

    assert config.qwen_api_key == ""
    assert config.qwen_model == "qwen-vl-max"


def test_app_config_to_dict_includes_qwen_fields() -> None:
    """to_dict serializes Qwen fields for JSON storage."""
    config = AppConfig(qwen_api_key="sk-test", qwen_model="qwen-vl-plus")

    data = config.to_dict()

    assert data["qwen_api_key"] == "sk-test"
    assert data["qwen_model"] == "qwen-vl-plus"
    assert data["image_max_size_mb"] == 20
    assert data["screenshot_hotkey"] == "<ctrl>+<shift>+s"


def test_image_translation_result_stores_both_stages() -> None:
    """ImageTranslationResult holds recognition and translation output."""
    result = ImageTranslationResult(
        source_image_path="test.png",
        recognized_text="# Heading\nSome text",
        translated_text="# 标题\n一些文本",
        source_language="en",
        target_language="zh",
        recognition_tokens=1500,
        translation_tokens=1200,
        timestamp="2026-07-02T10:00:00",
    )

    assert result.recognized_text == "# Heading\nSome text"
    assert result.translated_text == "# 标题\n一些文本"
    assert result.recognition_tokens == 1500
    assert result.translation_tokens == 1200
    assert result.error is None


def test_image_translation_result_supports_partial_failure() -> None:
    """ImageTranslationResult can carry recognition text with a translation error."""
    result = ImageTranslationResult(
        source_image_path="test.png",
        recognized_text="# Heading",
        translated_text="",
        source_language="en",
        target_language="zh",
        recognition_tokens=500,
        translation_tokens=0,
        timestamp="2026-07-02T10:00:00",
        error="Translation API timeout",
    )

    assert result.recognized_text == "# Heading"
    assert result.translated_text == ""
    assert result.error == "Translation API timeout"


def test_history_entry_defaults_to_text_type() -> None:
    """HistoryEntry defaults to translation_type='text'."""
    entry = HistoryEntry(
        timestamp="2026-01-01T00:00:00",
        source_text="hello",
        translated_text="你好",
        source_language="en",
        target_language="zh",
    )
    assert entry.translation_type == "text"


def test_history_entry_from_dict_handles_missing_translation_type() -> None:
    """Old history entries without translation_type load as 'text'."""
    payload = {
        "timestamp": "2026-01-01T00:00:00",
        "source_text": "hello",
        "translated_text": "你好",
        "source_language": "en",
        "target_language": "zh",
        "style": "academic",
    }
    entry = HistoryEntry.from_dict(payload)
    assert entry.translation_type == "text"


def test_history_entry_to_dict_includes_translation_type() -> None:
    """to_dict serializes translation_type."""
    entry = HistoryEntry(
        timestamp="2026-01-01T00:00:00",
        source_text="hello",
        translated_text="你好",
        source_language="en",
        target_language="zh",
        translation_type="image",
    )
    data = entry.to_dict()
    assert data["translation_type"] == "image"