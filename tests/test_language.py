"""Tests for pure language helper functions."""

from translator_app.language import (
    describe_language,
    detect_language,
    select_target_language,
)


def test_detect_language_returns_chinese_for_cjk_text() -> None:
    """Detect Chinese when CJK characters are present."""
    assert detect_language("这是学术论文中的术语。") == "zh"


def test_detect_language_returns_english_for_latin_text() -> None:
    """Detect English when Latin characters are present."""
    assert detect_language("This paragraph contains technical terminology.") == "en"


def test_detect_language_returns_unknown_for_symbols_only() -> None:
    """Return unknown when no supported script is found."""
    assert detect_language("12345 !@#$%") == "unknown"


def test_select_target_language_flips_between_chinese_and_english() -> None:
    """Select the opposite output language."""
    assert select_target_language("zh") == "en"
    assert select_target_language("en") == "zh"
    assert select_target_language("unknown") == "zh"


def test_describe_language_returns_human_readable_labels() -> None:
    """Map language codes to readable labels."""
    assert describe_language("zh") == "Chinese"
    assert describe_language("en") == "English"
    assert describe_language("unknown") == "Unknown"

