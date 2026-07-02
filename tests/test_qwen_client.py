"""Tests for Qwen VL API client (Node 1: image recognition only)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from translator_app.exceptions import ConfigurationError, QwenAPIError
from translator_app.models import AppConfig
from translator_app.qwen_client import QwenClient


def _make_config(**overrides) -> AppConfig:
    """Build a test config with optional overrides."""
    defaults = {
        "qwen_api_key": "sk-qwen-test",
        "qwen_api_url": "https://dashscope.test/v1/chat/completions",
        "qwen_model": "qwen-vl-max",
        "timeout_seconds": 30,
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


def test_recognize_image_builds_multimodal_payload() -> None:
    """recognize_image sends image_url + text content parts."""
    client = QwenClient(_make_config())

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "# Recognized text"}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("translator_app.qwen_client.requests.post", return_value=mock_response) as mock_post:
        result = client.recognize_image(
            image_base64="iVBORw0KGgo=",
            system_prompt="You are an OCR assistant.",
            user_prompt="Recognize this image.",
        )

        assert result == "# Recognized text"
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        user_message = payload["messages"][1]
        assert user_message["role"] == "user"
        content_parts = user_message["content"]
        assert len(content_parts) == 2
        assert content_parts[0]["type"] == "image_url"
        assert "iVBORw0KGgo=" in content_parts[0]["image_url"]["url"]
        assert content_parts[1]["type"] == "text"


def test_recognize_image_uses_correct_model_and_temperature() -> None:
    """API payload uses the configured model and low temperature for recognition."""
    client = QwenClient(_make_config(qwen_model="qwen-vl-plus"))

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "text"}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("translator_app.qwen_client.requests.post", return_value=mock_response) as mock_post:
        client.recognize_image("base64data", "sys", "usr")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "qwen-vl-plus"
        assert payload["temperature"] == 0.1
        assert payload["stream"] is False


def test_missing_api_key_raises_configuration_error() -> None:
    """recognize_image raises ConfigurationError when qwen_api_key is empty."""
    client = QwenClient(_make_config(qwen_api_key=""))

    try:
        client.recognize_image("data", "sys", "usr")
    except ConfigurationError as exc:
        assert "Qwen" in str(exc)
    else:
        raise AssertionError("Expected ConfigurationError")


def test_http_401_raises_friendly_qwen_error() -> None:
    """401 responses produce a user-friendly QwenAPIError."""
    client = QwenClient(_make_config())

    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": {"message": "Invalid API-key"}}
    mock_response.text = '{"error":{"message":"Invalid API-key"}}'
    mock_response.reason = "Unauthorized"
    http_error = requests.HTTPError("401 Client Error", response=mock_response)
    mock_response.raise_for_status.side_effect = http_error

    with patch("translator_app.qwen_client.requests.post", return_value=mock_response):
        try:
            client.recognize_image("base64data", "sys", "usr")
        except QwenAPIError as exc:
            assert "401" in str(exc)
            assert "Invalid API-key" in str(exc)
        else:
            raise AssertionError("Expected QwenAPIError")


def test_empty_response_content_raises_error() -> None:
    """Empty model output raises QwenAPIError."""
    client = QwenClient(_make_config())

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "   "}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("translator_app.qwen_client.requests.post", return_value=mock_response):
        try:
            client.recognize_image("base64data", "sys", "usr")
        except QwenAPIError as exc:
            assert "empty" in str(exc).lower()
        else:
            raise AssertionError("Expected QwenAPIError for empty content")