"""Typed application data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from translator_app.constants import (
    DEFAULT_API_URL,
    DEFAULT_HOTKEY,
    DEFAULT_IMAGE_MAX_SIZE_MB,
    DEFAULT_MODEL,
    DEFAULT_QWEN_API_URL,
    DEFAULT_QWEN_MODEL,
    DEFAULT_SCREENSHOT_HOTKEY,
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

    qwen_api_key: str = ""
    qwen_api_url: str = field(default_factory=lambda: DEFAULT_QWEN_API_URL)
    qwen_model: str = field(default_factory=lambda: DEFAULT_QWEN_MODEL)
    image_max_size_mb: int = DEFAULT_IMAGE_MAX_SIZE_MB
    screenshot_hotkey: str = DEFAULT_SCREENSHOT_HOTKEY

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
            qwen_api_key=payload.get("qwen_api_key", ""),
            qwen_api_url=payload.get("qwen_api_url", DEFAULT_QWEN_API_URL),
            qwen_model=payload.get("qwen_model", DEFAULT_QWEN_MODEL),
            image_max_size_mb=payload.get("image_max_size_mb", DEFAULT_IMAGE_MAX_SIZE_MB),
            screenshot_hotkey=payload.get("screenshot_hotkey", DEFAULT_SCREENSHOT_HOTKEY),
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
            "qwen_api_key": self.qwen_api_key,
            "qwen_api_url": self.qwen_api_url,
            "qwen_model": self.qwen_model,
            "image_max_size_mb": self.image_max_size_mb,
            "screenshot_hotkey": self.screenshot_hotkey,
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


@dataclass
class ImageTranslationResult:
    """Result of the two-stage image translation pipeline."""

    source_image_path: str
    recognized_text: str
    translated_text: str
    source_language: str
    target_language: str
    recognition_tokens: int
    translation_tokens: int
    timestamp: str
    error: Optional[str] = None
