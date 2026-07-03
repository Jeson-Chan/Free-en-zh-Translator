"""Markdown preview window with LaTeX rendering via QWebEngineView + KaTeX."""

from __future__ import annotations

import base64
import html
import logging
import os
import re
from typing import Optional

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt5.QtGui import QColor, QFont, QCloseEvent
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView

    _WEBENGINE_AVAILABLE = True
except ImportError:
    _WEBENGINE_AVAILABLE = False

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# KaTeX resource paths
# ---------------------------------------------------------------------------

_KATEX_DIR = os.path.join(os.path.dirname(__file__), "resources", "katex")

# ---------------------------------------------------------------------------
# Math protection / restoration
# ---------------------------------------------------------------------------

_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MATH_BLOCK_RE = re.compile(r"\$\$.*?\$\$", re.DOTALL)
_MATH_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)")
_PLACEHOLDER_RE = re.compile(r"\\MATH_(INLINE|BLOCK)_(\d+)\\MATH_END")


def _protect_math(
    markdown_text: str,
) -> tuple[str, dict[int, tuple[str, bool]]]:
    """Replace math expressions with placeholders safe for python-markdown."""
    code_spans: list[tuple[int, int]] = []
    for m in _FENCED_CODE_RE.finditer(markdown_text):
        code_spans.append((m.start(), m.end()))

    # Also exclude inline code spans (backtick-quoted, e.g. `$x^2$`)
    inline_code_spans: list[tuple[int, int]] = []
    for m in _INLINE_CODE_RE.finditer(markdown_text):
        inline_code_spans.append((m.start(), m.end()))

    placeholder_map: dict[int, tuple[str, bool]] = {}
    counter = 0

    def _in_code(pos: int) -> bool:
        return any(start <= pos < end for start, end in code_spans) or any(
            start <= pos < end for start, end in inline_code_spans
        )

    # Pass 1: block math $$...$$
    def _replace_block(m: re.Match) -> str:
        nonlocal counter
        start, end = m.start(), m.end()
        if _in_code(start) or _in_code(end - 1):
            return m.group(0)
        idx = counter
        counter += 1
        placeholder_map[idx] = (m.group(0), True)
        return f"\\MATH_BLOCK_{idx}\\MATH_END"

    protected = _MATH_BLOCK_RE.sub(_replace_block, markdown_text)

    # Pass 2: inline math $...$
    def _replace_inline(m: re.Match) -> str:
        nonlocal counter
        start, end = m.start(), m.end()
        if _in_code(start) or _in_code(end - 1):
            return m.group(0)
        idx = counter
        counter += 1
        placeholder_map[idx] = (m.group(0), False)
        return f"\\MATH_INLINE_{idx}\\MATH_END"

    protected = _MATH_INLINE_RE.sub(_replace_inline, protected)

    return protected, placeholder_map


def _restore_math(
    html_text: str, placeholder_map: dict[int, tuple[str, bool]]
) -> str:
    """Replace math placeholders with KaTeX-friendly HTML wrappers."""

    def _replace(m: re.Match) -> str:
        kind = m.group(1)  # INLINE or BLOCK
        idx = int(m.group(2))
        expr = placeholder_map.get(idx, ("", False))[0]
        if kind == "BLOCK":
            return f'<div class="math-block">{html.escape(expr)}</div>'
        return f'<span class="math-inline">{html.escape(expr)}</span>'

    return _PLACEHOLDER_RE.sub(_replace, html_text)


# ---------------------------------------------------------------------------
# KaTeX resource loading (with font embedding)
# ---------------------------------------------------------------------------

_KATEX_CSS: str = ""
_KATEX_JS: str = ""
_AUTO_RENDER_JS: str = ""
_KATEX_AVAILABLE = True


def _load_katex_resources() -> None:
    """Load and embed KaTeX CSS/JS at module load time."""
    global _KATEX_CSS, _KATEX_JS, _AUTO_RENDER_JS, _KATEX_AVAILABLE

    css_path = os.path.join(_KATEX_DIR, "katex.min.css")
    js_path = os.path.join(_KATEX_DIR, "katex.min.js")

    if not os.path.isfile(js_path):
        LOGGER.warning("KaTeX JS not found at %s", js_path)
        _KATEX_AVAILABLE = False
        return

    try:
        with open(js_path, "r", encoding="utf-8") as f:
            _KATEX_JS = f.read()
    except OSError as exc:
        LOGGER.warning("Could not read KaTeX JS: %s", exc)
        _KATEX_AVAILABLE = False
        return

    if not os.path.isfile(css_path):
        LOGGER.warning("KaTeX CSS not found at %s", css_path)
        _KATEX_CSS = ""
        return

    try:
        with open(css_path, "r", encoding="utf-8") as f:
            _KATEX_CSS = f.read()
        # Embed fonts as base64 data URIs
        fonts_dir = os.path.join(_KATEX_DIR, "fonts")

        def _replace_font_url(m: re.Match) -> str:
            # m.group(1) is "fonts/KaTeX_XXX.woff2" — strip the "fonts/" prefix
            font_relpath = m.group(1)
            font_filename = font_relpath.split("/", 1)[1]
            font_path = os.path.join(fonts_dir, font_filename)
            if not os.path.isfile(font_path):
                return m.group(0)
            with open(font_path, "rb") as ff:
                b64 = base64.b64encode(ff.read()).decode("ascii")
            ext = os.path.splitext(font_filename)[1].lstrip(".")
            mime_map = {
                "woff2": "font/woff2",
                "woff": "font/woff",
                "ttf": "font/ttf",
                "otf": "font/otf",
            }
            mime = mime_map.get(ext, "application/octet-stream")
            return f"url(data:{mime};base64,{b64})"

        _KATEX_CSS = re.sub(r"url\((fonts/[^)]+)\)", _replace_font_url, _KATEX_CSS)
    except OSError as exc:
        LOGGER.warning("Could not read/embed KaTeX CSS: %s", exc)
        _KATEX_CSS = ""

    # Load auto-render extension (cached at module level)
    ar_path = os.path.join(_KATEX_DIR, "auto-render.min.js")
    if os.path.isfile(ar_path):
        try:
            with open(ar_path, "r", encoding="utf-8") as f:
                _AUTO_RENDER_JS = f.read()
        except OSError:
            _AUTO_RENDER_JS = ""


_load_katex_resources()


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_MARKDOWN_THEME_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: Georgia, 'Times New Roman', 'SimSun', 'Songti SC', serif;
  font-size: 16px;
  line-height: 1.75;
  color: #2C1F14;
  background-color: #F0EBE4;
  padding: 28px 32px;
  max-width: 900px;
  margin: 0 auto;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
h1 { font-size: 28px; font-weight: 700; color: #3E2B1F;
     margin-top: 28px; margin-bottom: 14px; border-bottom: 1px solid #D4CCC4;
     padding-bottom: 8px; }
h2 { font-size: 22px; font-weight: 700; color: #3E2B1F;
     margin-top: 24px; margin-bottom: 12px; }
h3 { font-size: 18px; font-weight: 600; color: #5C3D2B;
     margin-top: 20px; margin-bottom: 10px; }
p { margin-bottom: 12px; }
a { color: #5C3D2B; text-decoration: underline; }
code {
  font-family: Consolas, 'Source Code Pro', 'Courier New', monospace;
  font-size: 14px;
  background-color: #E8E2D9;
  padding: 2px 6px;
  border-radius: 4px;
  color: #3E2B1F;
}
pre {
  background-color: #E8E2D9;
  border: 1px solid #D4CCC4;
  border-radius: 10px;
  padding: 16px;
  overflow-x: auto;
  margin: 16px 0;
}
pre code { background: none; padding: 0; border-radius: 0; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #D4CCC4; padding: 10px 14px; text-align: left; }
th { background-color: #E8E2D9; font-weight: 600; color: #3E2B1F; }
blockquote {
  border-left: 4px solid #D4CCC4;
  margin: 16px 0; padding: 8px 18px;
  color: #5C4033; background-color: #F8F5F0;
  border-radius: 0 8px 8px 0;
}
ul, ol { margin: 12px 0; padding-left: 28px; }
li { margin-bottom: 6px; }
hr { border: none; border-top: 1px solid #D4CCC4; margin: 24px 0; }
img { max-width: 100%; border-radius: 8px; }
.math-block { display: block; margin: 18px 0; text-align: center; overflow-x: auto; }
.math-inline { display: inline; }
.katex { font-size: 1.1em; }
.katex-display { margin: 18px 0; overflow-x: auto; overflow-y: hidden; }
"""


def _build_html(rendered_html: str) -> str:
    """Build the full self-contained HTML page with KaTeX."""
    katex_css_block = f"<style>{_KATEX_CSS}</style>" if _KATEX_CSS else ""
    katex_js_block = f"<script>{_KATEX_JS}</script>" if _KATEX_JS else ""
    auto_render_init = ""
    if _KATEX_AVAILABLE and "auto-render" not in katex_js_block.lower():
        auto_render_init = f"<script>{_AUTO_RENDER_JS}</script>\n" if _AUTO_RENDER_JS else ""

    return (
        "<!DOCTYPE html>"
        "<html lang='en'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        f"{katex_css_block}"
        f"<style>{_MARKDOWN_THEME_CSS}</style>"
        "</head><body>"
        f"{rendered_html}"
        "</body>"
        f"{katex_js_block}"
        f"{auto_render_init}"
        "<script>"
        "document.addEventListener('DOMContentLoaded', function() {"
        "  if (typeof renderMathInElement !== 'undefined') {"
        "    renderMathInElement(document.body, {"
        "      delimiters: ["
        "        {left: '$$', right: '$$', display: true},"
        "        {left: '$', right: '$', display: false}"
        "      ],"
        "      throwOnError: false,"
        "      strict: false"
        "    });"
        "  }"
        "});"
        "</script>"
        "</html>"
    )


# ---------------------------------------------------------------------------
# MarkdownPreviewWindow
# ---------------------------------------------------------------------------


class MarkdownPreviewWindow(QDialog):
    """Modeless dialog that renders Markdown + LaTeX via QWebEngineView + KaTeX."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the preview dialog UI."""
        super().__init__(parent)
        self.setWindowTitle("Markdown Preview")
        self.setModal(False)
        self.resize(800, 700)
        self.setMinimumSize(500, 400)

        self._current_markdown: str = ""
        self._web_view: Optional[QWebEngineView] = None
        self._copy_button: Optional[QPushButton] = None
        self._copied_timer_label: Optional[QLabel] = None

        # Fade-in animation
        self._fade_effect = None
        self._fade_animation = None

        self._apply_stylesheet()
        self._build_ui()

    def _apply_stylesheet(self) -> None:
        """Apply themed stylesheet matching the app palette."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #E8E2D9;
                color: #2C1F14;
            }
            QLabel#previewTitle {
                color: #2C1F14;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#previewButton {
                background-color: #D4CCC4;
                border: none;
                border-radius: 14px;
                color: #5C3D2B;
                padding: 8px 16px;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#previewButton:hover {
                background-color: #C8BFB7;
            }
            QPushButton#copyButton {
                background-color: #3E2B1F;
                border: none;
                border-radius: 14px;
                color: #F0EBE4;
                padding: 8px 16px;
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#copyButton:hover {
                background-color: #4A3425;
            }
            """
        )

    def _build_ui(self) -> None:
        """Build header bar + web view."""
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()

        title_label = QLabel("Markdown Preview")
        title_label.setObjectName("previewTitle")
        header_row.addWidget(title_label)
        header_row.addStretch()

        self._copied_timer_label = QLabel("")
        self._copied_timer_label.setStyleSheet(
            "QLabel { color: #5C4033; font-size: 13px; }"
        )
        self._copied_timer_label.setVisible(False)
        header_row.addWidget(self._copied_timer_label)

        self._copy_button = QPushButton("Copy")
        self._copy_button.setObjectName("copyButton")
        self._copy_button.clicked.connect(self._on_copy_clicked)
        self._copy_button.setEnabled(False)
        header_row.addWidget(self._copy_button)

        close_button = QPushButton("Close")
        close_button.setObjectName("previewButton")
        close_button.clicked.connect(self.hide)
        header_row.addWidget(close_button)

        root_layout.addLayout(header_row)

        # Web view
        if _WEBENGINE_AVAILABLE:
            self._web_view = QWebEngineView(self)

            # Configure WebEngine settings for better font rendering
            from PyQt5.QtWebEngineWidgets import QWebEngineSettings
            settings = self._web_view.settings()
            settings.setFontFamily(QWebEngineSettings.StandardFont, "Georgia")
            settings.setFontFamily(QWebEngineSettings.SerifFont, "Georgia")
            settings.setFontFamily(QWebEngineSettings.SansSerifFont, "Arial")
            settings.setFontFamily(QWebEngineSettings.FixedFont, "Consolas")
            settings.setFontSize(QWebEngineSettings.DefaultFontSize, 16)
            settings.setFontSize(QWebEngineSettings.DefaultFixedFontSize, 14)
            settings.setFontSize(QWebEngineSettings.MinimumFontSize, 12)

            self._web_view.setUrl(
                self._web_view.page().url()  # blank page initially
            )
            root_layout.addWidget(self._web_view, stretch=1)
        else:
            fallback = QLabel(
                "Preview requires PyQtWebEngine.\n"
                "Install it: pip install PyQtWebEngine>=5.15,<6"
            )
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet(
                "QLabel { color: #8C7B6E; font-size: 14px; }"
            )
            root_layout.addWidget(fallback, stretch=1)

        # Fade-in animation setup
        from PyQt5.QtWidgets import QGraphicsOpacityEffect

        self._fade_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fade_effect)
        self._fade_animation = QPropertyAnimation(self._fade_effect, b"opacity")

        self.setLayout(root_layout)

    def set_content(self, markdown_text: str) -> None:
        """Update content; render immediately if visible."""
        self._current_markdown = markdown_text
        self._copy_button.setEnabled(bool(markdown_text))
        if self.isVisible():
            self._render_markdown(markdown_text)

    def _render_markdown(self, markdown_text: str) -> None:
        """Convert Markdown to HTML with math and display in web view."""
        if self._web_view is None:
            return

        try:
            import markdown as md

            protected_text, placeholder_map = _protect_math(markdown_text)
            rendered_html = md.markdown(
                protected_text,
                extensions=["tables", "fenced_code", "codehilite"],
                extension_configs={"codehilite": {"css_class": "highlight"}},
            )
            restored_html = _restore_math(rendered_html, placeholder_map)
            full_html = _build_html(restored_html)
            # Use setContent for explicit encoding control (better for CJK text)
            self._web_view.page().setContent(
                full_html.encode("utf-8"),
                "text/html; charset=utf-8",
                self._web_view.url(),
            )
        except Exception as exc:
            LOGGER.error("Markdown preview rendering failed: %s", exc)
            error_html = (
                "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                f"<style>{_MARKDOWN_THEME_CSS}</style></head>"
                "<body>"
                f"<h2>Preview Error</h2>"
                f"<p>{html.escape(str(exc))}</p>"
                f"<pre>{html.escape(markdown_text)}</pre>"
                "</body></html>"
            )
            self._web_view.page().setContent(
                error_html.encode("utf-8"),
                "text/html; charset=utf-8",
                self._web_view.url(),
            )

    def _on_copy_clicked(self) -> None:
        """Copy the Markdown source to clipboard."""
        if not self._current_markdown:
            return
        QApplication.clipboard().setText(self._current_markdown)
        if self._copied_timer_label:
            self._copied_timer_label.setText("Copied!")
            self._copied_timer_label.setVisible(True)
            self._copied_timer_label.show()
            # Hide after 1.5s
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(1500, lambda: self._copied_timer_label.setVisible(False))

    def showEvent(self, event) -> None:  # type: ignore[override]
        """Fade in when shown."""
        if self._fade_animation is not None:
            self._fade_animation.stop()
            self._fade_effect.setOpacity(0.0)
            self._fade_animation.setDuration(180)
            self._fade_animation.setStartValue(0.0)
            self._fade_animation.setEndValue(1.0)
            self._fade_animation.setEasingCurve(QEasingCurve.OutCubic)
            self._fade_animation.start()

        if self._current_markdown:
            self._render_markdown(self._current_markdown)
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        """Hide instead of destroy so the instance can be reused."""
        event.ignore()
        self.hide()
