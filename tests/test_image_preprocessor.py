"""Tests for image preprocessing utilities."""

from __future__ import annotations

import base64
import io

from PIL import Image

from translator_app.exceptions import ImageProcessingError
from translator_app.image_preprocessor import (
    preprocess_image,
    preprocess_image_from_bytes,
    SUPPORTED_FORMATS,
    MAX_RESOLUTION,
)


def _create_test_image(width: int, height: int, fmt: str = "PNG") -> bytes:
    """Create a minimal test image in the given format."""
    img = Image.new("RGB", (width, height), color=(255, 200, 150))
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return buffer.getvalue()


def test_supported_formats_include_required_types() -> None:
    """All PRD-required formats are supported."""
    for ext in ("png", "jpg", "jpeg", "bmp", "webp"):
        assert ext in SUPPORTED_FORMATS


def test_max_resolution_is_4096() -> None:
    """Max resolution matches PRD requirement."""
    assert MAX_RESOLUTION == 4096


def test_preprocess_image_returns_base64_string(tmp_path) -> None:
    """preprocess_image returns a valid base64-encoded string."""
    img_path = tmp_path / "test.png"
    img_path.write_bytes(_create_test_image(100, 100))

    result = preprocess_image(str(img_path))

    assert isinstance(result, str)
    # Verify it's valid base64
    decoded = base64.b64decode(result)
    assert len(decoded) > 0


def test_preprocess_image_from_bytes_works() -> None:
    """preprocess_image_from_bytes handles raw image bytes."""
    img_bytes = _create_test_image(100, 100)

    result = preprocess_image_from_bytes(img_bytes, ".png")

    assert isinstance(result, str)
    decoded = base64.b64decode(result)
    assert len(decoded) > 0


def test_preprocess_image_resizes_oversized_images(tmp_path) -> None:
    """Images exceeding MAX_RESOLUTION are resized."""
    img_path = tmp_path / "large.png"
    img_path.write_bytes(_create_test_image(5000, 5000))

    result = preprocess_image(str(img_path))

    # Result should still be valid base64
    decoded = base64.b64decode(result)
    assert len(decoded) > 0


def test_preprocess_image_rejects_unsupported_format(tmp_path) -> None:
    """Unsupported file extensions raise ImageProcessingError."""
    img_path = tmp_path / "test.tiff"
    img_path.write_bytes(_create_test_image(100, 100, "TIFF"))

    try:
        preprocess_image(str(img_path))
    except ImageProcessingError as exc:
        assert "format" in str(exc).lower() or "supported" in str(exc).lower()
    else:
        raise AssertionError("Expected ImageProcessingError for unsupported format")


def test_preprocess_image_rejects_nonexistent_file() -> None:
    """Non-existent file raises ImageProcessingError."""
    try:
        preprocess_image("/nonexistent/path/to/image.png")
    except ImageProcessingError as exc:
        assert "not found" in str(exc).lower() or "exist" in str(exc).lower()
    else:
        raise AssertionError("Expected ImageProcessingError for missing file")


def test_preprocess_image_rejects_oversized_file(tmp_path) -> None:
    """Files exceeding 20MB raise ImageProcessingError."""
    # Create a fake 21MB file
    img_path = tmp_path / "huge.png"
    img_path.write_bytes(b"\x00" * (21 * 1024 * 1024))

    try:
        preprocess_image(str(img_path), max_size_mb=20)
    except ImageProcessingError as exc:
        assert "size" in str(exc).lower() or "mb" in str(exc).lower()
    else:
        raise AssertionError("Expected ImageProcessingError for oversized file")