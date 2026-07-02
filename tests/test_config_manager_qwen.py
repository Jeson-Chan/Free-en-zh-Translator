"""Tests for Qwen API key environment variable fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path

from translator_app.config_manager import ConfigManager
from translator_app.models import AppConfig


def test_qwen_api_key_from_config_file(tmp_path: Path) -> None:
    """Load qwen_api_key from config.json when present."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": "sk-qwen-from-file"}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-qwen-from-file"


def test_qwen_api_key_from_env_var(tmp_path: Path, monkeypatch) -> None:
    """Fall back to QWEN_API_KEY environment variable when config value is empty."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": ""}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-from-env")

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-qwen-from-env"


def test_qwen_api_key_from_dotenv(tmp_path: Path, monkeypatch) -> None:
    """Fall back to .env file when both config and env var are empty."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": ""}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    (tmp_path / ".env").write_text("QWEN_API_KEY=sk-qwen-from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-qwen-from-dotenv"


def test_qwen_api_key_config_takes_priority_over_env(tmp_path: Path, monkeypatch) -> None:
    """config.json qwen_api_key wins over QWEN_API_KEY env var."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": "sk-from-config"}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("QWEN_API_KEY", "sk-from-env")

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-from-config"


def test_save_config_persists_qwen_fields(tmp_path: Path) -> None:
    """save_config writes Qwen fields to disk."""
    manager = ConfigManager(tmp_path)
    config = AppConfig(api_key="sk-test", qwen_api_key="sk-qwen", qwen_model="qwen-vl-plus")

    manager.save_config(config)

    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["qwen_api_key"] == "sk-qwen"
    assert saved["qwen_model"] == "qwen-vl-plus"