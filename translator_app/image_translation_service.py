"""Node 2: Translate recognized Markdown text using DeepSeek."""

from __future__ import annotations

import logging

from translator_app.constants import IMAGE_TRANSLATION_SYSTEM_PROMPT
from translator_app.deepseek_client import DeepSeekClient
from translator_app.exceptions import DeepSeekAPIError

LOGGER = logging.getLogger(__name__)

_TRANSLATION_USER_PROMPT_TEMPLATE = (
    "请将以下学术内容翻译为目标语言，保持 Markdown 格式不变：\n\n{recognized_text}"
)

_DEFAULT_TRANSLATION_MODEL = "deepseek-v4-pro"


class ImageTranslationService:
    """Translate structured Markdown text via DeepSeek deepseek-v4-pro."""

    def __init__(self, client: DeepSeekClient) -> None:
        """Store the API client dependency."""
        self._client = client

    def translate(self, recognized_text: str) -> str:
        """Translate recognized Markdown and return the translated output.

        Raises DeepSeekAPIError if translation fails or returns empty output.
        """
        LOGGER.info("Starting image translation (Node 2, %d chars input)", len(recognized_text))

        user_prompt = _TRANSLATION_USER_PROMPT_TEMPLATE.format(
            recognized_text=recognized_text,
        )

        result = self._client.translate_with_prompts(
            system_prompt=IMAGE_TRANSLATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=_DEFAULT_TRANSLATION_MODEL,
        )

        if not result.strip():
            raise DeepSeekAPIError("Image translation returned empty output.")

        LOGGER.info("Image translation complete (%d chars)", len(result))
        return result