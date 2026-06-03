"""Tests for DeepSeek client authentication helpers."""

from __future__ import annotations

import requests

from translator_app.deepseek_client import DeepSeekClient
from translator_app.exceptions import ConfigurationError, DeepSeekAPIError
from translator_app.models import AppConfig


def test_build_headers_includes_required_auth_headers() -> None:
    """Build headers with the validated bearer token."""
    client = DeepSeekClient(AppConfig(api_key="sk-valid-token"))

    headers = client._build_headers()

    assert headers["Authorization"] == "Bearer sk-valid-token"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


def test_validate_api_key_rejects_placeholder_value() -> None:
    """Reject the default placeholder key before a network call."""
    try:
        DeepSeekClient._validate_api_key("your-deepseek-api-key")
    except ConfigurationError as exc:
        assert "placeholder" in str(exc)
    else:
        raise AssertionError("Expected ConfigurationError for placeholder API key.")


def test_validate_api_key_rejects_whitespace() -> None:
    """Reject malformed keys that contain embedded whitespace."""
    try:
        DeepSeekClient._validate_api_key("sk-invalid token")
    except ConfigurationError as exc:
        assert "whitespace" in str(exc)
    else:
        raise AssertionError("Expected ConfigurationError for malformed API key.")


def test_build_http_error_for_401_is_user_friendly() -> None:
    """Convert 401 errors into a clearer authentication message."""
    response = requests.Response()
    response.status_code = 401
    response._content = b'{"error":{"message":"Authorization Required"}}'
    response.url = "https://api.deepseek.com/chat/completions"

    http_error = requests.HTTPError("401 Client Error", response=response)

    error = DeepSeekClient._build_http_error(http_error)

    assert isinstance(error, DeepSeekAPIError)
    assert "401 Unauthorized" in str(error)
    assert "Authorization Required" in str(error)


def test_build_user_message_includes_selected_style_instruction() -> None:
    """Embed the requested translation style in the user message."""
    message = DeepSeekClient._build_user_message(
        text="Hello world",
        source_language="en",
        target_language="zh",
        style="business",
    )

    assert "Translation style: Business" in message
    assert "professional business tone" in message
