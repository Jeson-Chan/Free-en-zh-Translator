"""Helpers for translation style selection."""

from __future__ import annotations

from typing import Literal

TranslationStyle = Literal["academic", "casual", "business", "literary"]

DEFAULT_TRANSLATION_STYLE: TranslationStyle = "academic"
AVAILABLE_TRANSLATION_STYLES: tuple[TranslationStyle, ...] = (
    "academic",
    "casual",
    "business",
    "literary",
)

_STYLE_INSTRUCTIONS: dict[TranslationStyle, str] = {
    "academic": (
        "Use an academic tone. Preserve technical terminology, formal phrasing, "
        "and the structure expected in research or professional writing."
    ),
    "casual": (
        "Use a natural and conversational tone. Keep the meaning accurate, but make "
        "the result easy to read in everyday language."
    ),
    "business": (
        "Use a professional business tone. Keep the wording concise, clear, and "
        "appropriate for workplace or client communication."
    ),
    "literary": (
        "Use a polished literary tone. Preserve imagery, rhythm, and stylistic nuance "
        "while keeping the meaning faithful to the source."
    ),
}


def normalize_translation_style(style: str) -> TranslationStyle:
    """Normalize a user-provided style string to a supported style."""
    normalized_style = style.strip().lower()
    if normalized_style in AVAILABLE_TRANSLATION_STYLES:
        return normalized_style
    return DEFAULT_TRANSLATION_STYLE


def get_style_instruction(style: str) -> str:
    """Return the translation instruction for the selected style."""
    normalized_style = normalize_translation_style(style)
    return _STYLE_INSTRUCTIONS[normalized_style]


def get_style_display_name(style: str) -> str:
    """Return the title-cased display name for a style."""
    return normalize_translation_style(style).title()

