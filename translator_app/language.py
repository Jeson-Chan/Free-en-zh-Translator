"""Pure helpers for language detection and direction selection."""

from __future__ import annotations

import re

_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_LATIN_PATTERN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Detect whether the text is primarily Chinese or English."""
    if _CJK_PATTERN.search(text):
        return "zh"
    if _LATIN_PATTERN.search(text):
        return "en"
    return "unknown"


def select_target_language(source_language: str) -> str:
    """Choose the opposite translation target language."""
    if source_language == "zh":
        return "en"
    return "zh"


def describe_language(language_code: str) -> str:
    """Return a human-readable language label for the UI."""
    if language_code == "zh":
        return "Chinese"
    if language_code == "en":
        return "English"
    return "Unknown"

