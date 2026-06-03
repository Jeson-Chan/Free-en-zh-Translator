"""Application-specific exception types."""


class TranslatorAppError(Exception):
    """Base exception for the translator application."""


class ConfigurationError(TranslatorAppError):
    """Raised when configuration is missing or invalid."""


class DeepSeekAPIError(TranslatorAppError):
    """Raised when the DeepSeek API request fails."""


class HistoryError(TranslatorAppError):
    """Raised when translation history cannot be loaded or saved."""


class HotkeyError(TranslatorAppError):
    """Raised when the global hotkey listener cannot be started."""

