"""DeepSeek API client."""

from __future__ import annotations

import logging
from typing import Any

import requests

from translator_app.constants import SYSTEM_PROMPT
from translator_app.exceptions import ConfigurationError, DeepSeekAPIError
from translator_app.models import AppConfig
from translator_app.translation_style import get_style_display_name, get_style_instruction

LOGGER = logging.getLogger(__name__)


class DeepSeekClient:
    """Send translation requests to a DeepSeek-compatible API."""

    def __init__(self, config: AppConfig) -> None:
        """Store request configuration for future API calls."""
        self._config = config

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        style: str,
    ) -> str:
        """Translate a single text block and return the model output."""
        headers = self._build_headers()
        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_user_message(
                        text=text,
                        source_language=source_language,
                        target_language=target_language,
                        style=style,
                    ),
                },
            ],
        }

        LOGGER.info(
            "Sending translation request with model=%s source=%s target=%s style=%s",
            self._config.model,
            source_language,
            target_language,
            style,
        )

        try:
            response = requests.post(
                self._config.api_url,
                headers=headers,
                json=payload,
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json()
        except requests.HTTPError as exc:
            raise self._build_http_error(exc) from exc
        except requests.RequestException as exc:
            raise DeepSeekAPIError(
                f"DeepSeek API request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise DeepSeekAPIError("DeepSeek API returned invalid JSON.") from exc

        content = self._extract_content(response_payload)
        if not content:
            raise DeepSeekAPIError("DeepSeek API returned an empty translation result.")

        return content

    def _build_headers(self) -> dict[str, str]:
        """Build validated request headers for the DeepSeek API."""
        api_key = self._validate_api_key(self._config.api_key)
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AcademicFloatingTranslator/1.0",
        }

    @staticmethod
    def _validate_api_key(raw_api_key: str) -> str:
        """Validate the configured API key before sending a request."""
        api_key = raw_api_key.strip()
        if not api_key:
            raise ConfigurationError("DeepSeek API key is missing. Open Settings first.")

        if api_key == "your-deepseek-api-key":
            raise ConfigurationError(
                "DeepSeek API key is still the placeholder value. Please update config.json or Settings."
            )

        if any(character.isspace() for character in api_key):
            raise ConfigurationError(
                "DeepSeek API key contains whitespace. Please re-copy the key in config.json or Settings."
            )

        return api_key

    @staticmethod
    def _build_http_error(exc: requests.HTTPError) -> DeepSeekAPIError:
        """Convert HTTP errors into user-friendly DeepSeek exceptions."""
        response = exc.response
        if response is None:
            return DeepSeekAPIError(f"DeepSeek API returned an HTTP error: {exc}")

        details = DeepSeekClient._extract_error_details(response)
        if response.status_code == 401:
            return DeepSeekAPIError(
                "DeepSeek authentication failed (401 Unauthorized). "
                "Please verify that your API key is valid, active, and copied exactly into config.json or Settings. "
                f"Server message: {details}"
            )

        return DeepSeekAPIError(
            f"DeepSeek API returned HTTP {response.status_code}. Server message: {details}"
        )

    @staticmethod
    def _extract_error_details(response: requests.Response) -> str:
        """Read a concise error message from an HTTP response."""
        try:
            payload: Any = response.json()
        except ValueError:
            text = response.text.strip()
            return text or response.reason or "No error details returned."

        if isinstance(payload, dict):
            error_payload = payload.get("error")
            if isinstance(error_payload, dict):
                message = error_payload.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()

            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

        text = response.text.strip()
        return text or response.reason or "No error details returned."

    @staticmethod
    def _build_user_message(
        text: str,
        source_language: str,
        target_language: str,
        style: str,
    ) -> str:
        """Build the user message sent to the model."""
        style_instruction = get_style_instruction(style)
        style_name = get_style_display_name(style)
        return (
            f"Source language: {source_language}\n"
            f"Target language: {target_language}\n"
            f"Translation style: {style_name}\n"
            f"Style instruction: {style_instruction}\n"
            "Please preserve formatting, terminology, and paragraph structure.\n\n"
            f"{text}"
        )

    @staticmethod
    def _extract_content(payload: dict) -> str:
        """Extract the translated message text from the API response."""
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DeepSeekAPIError("DeepSeek API response is missing choices.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise DeepSeekAPIError("DeepSeek API choice format is invalid.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise DeepSeekAPIError("DeepSeek API response is missing message data.")

        content = message.get("content", "")
        if not isinstance(content, str):
            raise DeepSeekAPIError("DeepSeek API message content is invalid.")

        return content.strip()
