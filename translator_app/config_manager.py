"""Configuration loading and saving utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path

from translator_app.constants import CONFIG_FILE_NAME
from translator_app.exceptions import ConfigurationError
from translator_app.models import AppConfig


class ConfigManager:
    """Manage persistent application configuration.

    API key resolution priority (highest first):
      1. api_key field in config.json
      2. DEEPSEEK_API_KEY environment variable
      3. .env file in the project root (DEEPSEEK_API_KEY=...)

    Qwen API key resolution priority (highest first):
      1. qwen_api_key field in config.json
      2. QWEN_API_KEY environment variable
      3. .env file in the project root (QWEN_API_KEY=...)
    """

    def __init__(self, root_path: Path) -> None:
        """Store the project root used for configuration files."""
        self._root_path = root_path
        self._config_path = root_path / CONFIG_FILE_NAME

    @property
    def config_path(self) -> Path:
        """Expose the absolute config file path."""
        return self._config_path

    def config_exists(self) -> bool:
        """Return whether the config file currently exists."""
        return self._config_path.exists()

    def load_config(self) -> AppConfig:
        """Load app configuration from disk or return defaults.

        Falls back through environment variable and .env file when no
        API key is found in the config file.
        """
        if not self._config_path.exists():
            return self._apply_env_fallback(AppConfig())

        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Invalid JSON in config file: {self._config_path}"
            ) from exc
        except OSError as exc:
            raise ConfigurationError(
                f"Could not read config file: {self._config_path}"
            ) from exc

        if not isinstance(payload, dict):
            raise ConfigurationError("Config file must contain a JSON object.")

        return self._apply_env_fallback(AppConfig.from_dict(payload))

    # ------------------------------------------------------------------
    # API key resolution helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_dotenv(dotenv_path: Path) -> dict[str, str]:
        """Parse a .env file into a flat dict (no quoting, no expansion)."""
        result: dict[str, str] = {}
        try:
            text = dotenv_path.read_text(encoding="utf-8-sig")
        except OSError:
            return result

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key:
                result[key] = value.strip()
        return result

    def _apply_env_fallback(self, config: AppConfig) -> AppConfig:
        """Fill API keys from environment or .env file if missing."""
        # DeepSeek API key fallback (3-layer)
        if not config.api_key:
            env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if env_key:
                config.api_key = env_key
            else:
                dotenv_path = self._root_path / ".env"
                dotenv_vars = self._read_dotenv(dotenv_path)
                dotenv_key = dotenv_vars.get("DEEPSEEK_API_KEY", "").strip()
                if dotenv_key:
                    config.api_key = dotenv_key

        # Qwen API key fallback (3-layer) -- always evaluated
        self._apply_qwen_env_fallback(config)
        return config

    def _apply_qwen_env_fallback(self, config: AppConfig) -> None:
        """Fill the Qwen API key from environment or .env file if missing."""
        if config.qwen_api_key:
            return

        env_key = os.environ.get("QWEN_API_KEY", "").strip()
        if env_key:
            config.qwen_api_key = env_key
            return

        dotenv_path = self._root_path / ".env"
        dotenv_vars = self._read_dotenv(dotenv_path)
        dotenv_key = dotenv_vars.get("QWEN_API_KEY", "").strip()
        if dotenv_key:
            config.qwen_api_key = dotenv_key

    def save_config(self, config: AppConfig) -> None:
        """Persist app configuration to disk."""
        try:
            self._config_path.write_text(
                json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigurationError(
                f"Could not write config file: {self._config_path}"
            ) from exc
