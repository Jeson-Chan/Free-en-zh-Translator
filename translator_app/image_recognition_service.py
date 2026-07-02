"""Node 1: Recognize text content from an image using Qwen VL."""

from __future__ import annotations

import logging

from translator_app.constants import RECOGNITION_SYSTEM_PROMPT
from translator_app.exceptions import QwenAPIError
from translator_app.qwen_client import QwenClient

LOGGER = logging.getLogger(__name__)

_RECOGNITION_USER_PROMPT = "请识别这张图片中的所有文字内容，按照文档结构输出 Markdown 格式。"


class ImageRecognitionService:
    """Extract structured Markdown text from an image via Qwen VL."""

    def __init__(self, client: QwenClient) -> None:
        """Store the API client dependency."""
        self._client = client

    def recognize(self, image_base64: str) -> str:
        """Send the image to Qwen VL and return recognized Markdown text.

        Raises QwenAPIError if recognition fails or returns empty output.
        """
        LOGGER.info("Starting image recognition (Node 1)")

        result = self._client.recognize_image(
            image_base64=image_base64,
            system_prompt=RECOGNITION_SYSTEM_PROMPT,
            user_prompt=_RECOGNITION_USER_PROMPT,
        )

        if not result.strip():
            raise QwenAPIError(
                "Image recognition returned no text. "
                "Please confirm the image contains readable text."
            )

        LOGGER.info("Image recognition complete (%d chars)", len(result))
        return result