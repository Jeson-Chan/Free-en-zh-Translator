"""Qwen VL (Vision-Language) API client."""

from __future__ import annotations

import logging
from typing import Any

import requests

from translator_app.exceptions import ConfigurationError, QwenAPIError
from translator_app.models import AppConfig

LOGGER = logging.getLogger(__name__)

_RECOGNITION_TEMPERATURE = 0.1
_MAX_TOKENS = 8192


class QwenClient:
    """Send multimodal recognition requests to a Qwen VL-compatible API.

    Note: Node 2 (translation) uses the existing DeepSeekClient, not this client.
    """

    def __init__(self, config: AppConfig) -> None:
        """Store request configuration for future API calls."""
        self._config = config

    def recognize_image(
        self,
        image_base64: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Send an image + text request and return the model's text output."""
        api_key = self._validate_api_key(self._config.qwen_api_key)
        payload = {
            "model": self._config.qwen_model,
            "temperature": _RECOGNITION_TEMPERATURE,
            "max_tokens": _MAX_TOKENS,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                },
            ],
        }

        LOGGER.info("Sending image recognition request with model=%s", self._config.qwen_model)
        url = self._build_url(self._config.qwen_api_url)
        return self._send_request(url, payload, api_key)

    @staticmethod
    def _build_url(raw_url: str) -> str:
        """Ensure the API URL ends with /chat/completions.

        Accepts both base URLs (e.g. .../compatible-mode/v1) and full
        endpoint URLs (e.g. .../compatible-mode/v1/chat/completions).
        """
        url = raw_url.strip().rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        return url

    def _send_request(self, url: str, payload: dict[str, Any], api_key: str) -> str:
        """Execute an HTTP POST and extract the response content."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AcademicFloatingTranslator/1.0",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json()
        except requests.HTTPError as exc:
            raise self._build_http_error(exc) from exc
        except requests.RequestException as exc:
            raise QwenAPIError(f"Qwen API request failed: {exc}") from exc
        except ValueError as exc:
            raise QwenAPIError("Qwen API returned invalid JSON.") from exc

        content = self._extract_content(response_payload)
        if not content:
            raise QwenAPIError("Qwen API returned an empty result.")

        return content

    @staticmethod
    def _validate_api_key(raw_api_key: str) -> str:
        """Validate the Qwen API key before sending a request."""
        api_key = raw_api_key.strip()
        if not api_key:
            raise ConfigurationError(
                "Qwen API key is missing. Open Settings and configure the Multimodal section."
            )
        return api_key

    @staticmethod
    def _build_http_error(exc: requests.HTTPError) -> QwenAPIError:
        """Convert HTTP errors into user-friendly Qwen exceptions."""
        response = exc.response
        if response is None:
            return QwenAPIError(f"Qwen API returned an HTTP error: {exc}")

        details = QwenClient._extract_error_details(response)
        if response.status_code == 401:
            return QwenAPIError(
                "Qwen authentication failed (401 Unauthorized). "
                "Please verify that your Qwen API key is valid. "
                f"Server message: {details}"
            )

        return QwenAPIError(
            f"Qwen API returned HTTP {response.status_code}. Server message: {details}"
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

        text = response.text.strip()
        return text or response.reason or "No error details returned."

    @staticmethod
    def _extract_content(payload: dict) -> str:
        """Extract the message text from the API response."""
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise QwenAPIError("Qwen API response is missing choices.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise QwenAPIError("Qwen API choice format is invalid.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise QwenAPIError("Qwen API response is missing message data.")

        content = message.get("content", "")
        if not isinstance(content, str):
            raise QwenAPIError("Qwen API message content is invalid.")

        return content.strip()