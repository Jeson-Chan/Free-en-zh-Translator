"""Typed application data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from translator_app.constants import (
    DEFAULT_API_URL,
    DEFAULT_HOTKEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
)
from translator_app.translation_style import DEFAULT_TRANSLATION_STYLE


@dataclass(slots=True)
class AppConfig:
    """Runtime configuration for the application."""

    api_key: str = ""
    api_url: str = DEFAULT_API_URL
    model: str = DEFAULT_MODEL
    hotkey: str = DEFAULT_HOTKEY
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    temperature: float = DEFAULT_TEMPERATURE

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        """Build a config object from a raw dictionary."""
        return cls(
            api_key=str(payload.get("api_key", "")).strip(),
            api_url=str(payload.get("api_url", DEFAULT_API_URL)).strip(),
            model=str(payload.get("model", DEFAULT_MODEL)).strip(),
            hotkey=str(payload.get("hotkey", DEFAULT_HOTKEY)).strip(),
            timeout_seconds=int(payload.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
            temperature=float(payload.get("temperature", DEFAULT_TEMPERATURE)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize config data for JSON storage."""
        return {
            "api_key": self.api_key,
            "api_url": self.api_url,
            "model": self.model,
            "hotkey": self.hotkey,
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
        }


@dataclass(slots=True)
class HistoryEntry:
    """A single translation history item."""

    timestamp: str
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    style: str = DEFAULT_TRANSLATION_STYLE

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HistoryEntry":
        """Build a history entry from persisted JSON data."""
        return cls(
            timestamp=str(payload["timestamp"]),
            source_text=str(payload["source_text"]),
            translated_text=str(payload["translated_text"]),
            source_language=str(payload["source_language"]),
            target_language=str(payload["target_language"]),
            style=str(payload.get("style", DEFAULT_TRANSLATION_STYLE)),
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize history entry data for JSON storage."""
        return {
            "timestamp": self.timestamp,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "style": self.style,
        }


@dataclass(slots=True)
class TranslationResult:
    """Translation result returned to the UI."""

    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    model: str
    style: str
