"""Tests for screenshot tool coordinate math."""

from __future__ import annotations

from translator_app.screenshot_tool import normalize_selection_rect


def test_normalize_selection_rect_left_to_right() -> None:
    """Selection drawn left-to-right returns positive width/height."""
    x, y, w, h = normalize_selection_rect(100, 200, 300, 400)

    assert x == 100
    assert y == 200
    assert w == 200
    assert h == 200


def test_normalize_selection_rect_right_to_left() -> None:
    """Selection drawn right-to-left is normalized to positive dimensions."""
    x, y, w, h = normalize_selection_rect(300, 400, 100, 200)

    assert x == 100
    assert y == 200
    assert w == 200
    assert h == 200


def test_normalize_selection_rect_zero_area() -> None:
    """A single-point click (no drag) returns zero dimensions."""
    x, y, w, h = normalize_selection_rect(150, 250, 150, 250)

    assert w == 0
    assert h == 0