"""Service layer for translating text and storing history."""

from __future__ import annotations

from datetime import datetime

from translator_app.config_manager import ConfigManager
from translator_app.deepseek_client import DeepSeekClient
from translator_app.exceptions import ConfigurationError
from translator_app.history_manager import HistoryManager
from translator_app.language import detect_language, select_target_language
from translator_app.models import HistoryEntry, TranslationResult
from translator_app.translation_style import normalize_translation_style


class TranslationService:
    """Coordinate config loading, translation, and history persistence."""

    def __init__(
        self,
        config_manager: ConfigManager,
        history_manager: HistoryManager,
    ) -> None:
        """Store persistence dependencies for translation work."""
        self._config_manager = config_manager
        self._history_manager = history_manager

    def translate_text(self, text: str, style: str) -> TranslationResult:
        """Translate text, then persist the result in recent history."""
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Please enter text to translate.")

        config = self._config_manager.load_config()
        if not config.api_key:
            raise ConfigurationError("DeepSeek API key is missing. Open Settings first.")

        normalized_style = normalize_translation_style(style)
        source_language = detect_language(cleaned_text)
        target_language = select_target_language(source_language)
        client = DeepSeekClient(config)
        translated_text = client.translate(
            text=cleaned_text,
            source_language=source_language,
            target_language=target_language,
            style=normalized_style,
        )

        result = TranslationResult(
            source_text=cleaned_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            model=config.model,
            style=normalized_style,
        )
        history_entry = HistoryEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            source_text=result.source_text,
            translated_text=result.translated_text,
            source_language=result.source_language,
            target_language=result.target_language,
            style=result.style,
        )
        self._history_manager.add_entry(history_entry)
        return result
