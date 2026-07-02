"""Image preprocessing utilities for validation, resize, and base64 encoding."""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from PIL import Image

from translator_app.exceptions import ImageProcessingError

LOGGER = logging.getLogger(__name__)

SUPPORTED_FORMATS = frozenset({"png", "jpg", "jpeg", "bmp", "webp"})
MAX_RESOLUTION = 4096
_MAX_FILE_SIZE_MB = 20


def preprocess_image(
    file_path: str,
    max_size_mb: int = _MAX_FILE_SIZE_MB,
) -> str:
    """Validate, resize, and encode an image file as base64.

    Args:
        file_path: Path to the image file.
        max_size_mb: Maximum allowed file size in megabytes.

    Returns:
        Base64-encoded string of the processed image.

    Raises:
        ImageProcessingError: If the file is invalid, too large, or unsupported.
    """
    path = Path(file_path)

    if not path.exists():
        raise ImageProcessingError(f"Image file not found: {file_path}")

    # Check file extension
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FORMATS:
        raise ImageProcessingError(
            f"Unsupported image format '{suffix}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    # Check file size
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ImageProcessingError(
            f"Image file too large ({file_size_mb:.1f} MB). "
            f"Maximum allowed size: {max_size_mb} MB."
        )

    try:
        image_bytes = path.read_bytes()
    except OSError as exc:
        raise ImageProcessingError(f"Could not read image file: {exc}") from exc

    return preprocess_image_from_bytes(image_bytes, path.suffix)


def preprocess_image_from_bytes(
    image_bytes: bytes,
    extension: str,
    max_size_bytes: int = _MAX_FILE_SIZE_MB * 1024 * 1024,
) -> str:
    """Validate, resize, and encode image bytes as base64.

    Args:
        image_bytes: Raw image data.
        extension: File extension (e.g., ".png", ".jpg").
        max_size_bytes: Maximum allowed byte size before decompression.

    Returns:
        Base64-encoded string of the processed image.

    Raises:
        ImageProcessingError: If the image is invalid or cannot be processed.
    """
    suffix = extension.lower().lstrip(".")

    # Check raw byte size to prevent decompression bombs
    if len(image_bytes) > max_size_bytes:
        raise ImageProcessingError(
            f"Image data too large ({len(image_bytes)} bytes). "
            f"Maximum allowed: {max_size_bytes} bytes."
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ImageProcessingError(f"Invalid image data: {exc}") from exc

    # Convert to RGB if necessary (handles RGBA, palette, etc.)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    # Resize if exceeding max resolution
    width, height = image.size
    if width > MAX_RESOLUTION or height > MAX_RESOLUTION:
        scale = min(MAX_RESOLUTION / width, MAX_RESOLUTION / height)
        new_size = (int(width * scale), int(height * scale))
        LOGGER.info("Resizing image from %dx%d to %dx%d", width, height, *new_size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Encode to base64 - always output PNG for consistent MIME type in Qwen VL API
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    LOGGER.info("Image preprocessed: %d bytes -> %d chars base64", len(image_bytes), len(encoded))
    return encoded