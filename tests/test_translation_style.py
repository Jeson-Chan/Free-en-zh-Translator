"""Tests for translation style helper functions."""

from translator_app.translation_style import (
    DEFAULT_TRANSLATION_STYLE,
    get_style_display_name,
    get_style_instruction,
    normalize_translation_style,
)


def test_normalize_translation_style_returns_supported_style() -> None:
    """Normalize a mixed-case supported style."""
    assert normalize_translation_style(" Business ") == "business"


def test_normalize_translation_style_falls_back_to_default() -> None:
    """Fallback to the default style for unsupported values."""
    assert normalize_translation_style("poetic") == DEFAULT_TRANSLATION_STYLE


def test_get_style_instruction_returns_style_specific_prompt() -> None:
    """Return the expected instruction for literary mode."""
    instruction = get_style_instruction("literary")
    assert "literary tone" in instruction
    assert "stylistic nuance" in instruction


def test_get_style_display_name_uses_title_case() -> None:
    """Format the UI display name for a style."""
    assert get_style_display_name("casual") == "Casual"

