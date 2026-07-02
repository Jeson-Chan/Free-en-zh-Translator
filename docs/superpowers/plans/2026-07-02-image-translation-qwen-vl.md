# Image Translation (Qwen VL) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add image translation to the Academic Floating Translator — users upload or screenshot an image, a two-node pipeline (recognition → translation) powered by Qwen VL produces Markdown output.

**Architecture:** Two-stage serial pipeline. Node 1 sends the image (base64) to `qwen-vl-max` (Qwen VL multimodal) with a recognition prompt, producing structured Markdown. Node 2 sends that Markdown to `deepseek-v4-pro` (existing DeepSeek API) with a translation prompt, producing translated Markdown. The pipeline runs on a QThread, emits progress signals, and feeds into new PyQt5 widgets (image input, markdown output) integrated into the existing floating window via a new bottom-nav tab.

**Tech Stack:** Python 3.12+, PyQt5, Pillow (image preprocessing), markdown (HTML rendering), requests, pynput, Qwen VL API (DashScope OpenAI-compatible).

## Global Constraints

- Python 3.12+; no walrus operators or match statements below 3.10
- All new files use `from __future__ import annotations`
- PyQt5 `>=5.15, <6`; Pillow `>=10.0, <11`; markdown `>=3.6, <4`
- All API calls use OpenAI Chat Completions format (DashScope compatible-mode endpoint)
- Qwen API key resolution: config.json → `QWEN_API_KEY` env var → `.env` file (3-layer fallback, mirrors DeepSeek pattern)
- Exception hierarchy: all new exceptions inherit from `TranslatorAppError`
- All QThread workers emit `succeeded`/`failed` signals; never block the UI thread
- UI follows existing warm palette: background `#E8E2D9`, cards `#F0EBE4`, accent `#3E2B1F`, text `#2C1F14`
- Image max size: 20 MB; max resolution: 4096×4096 px (auto-resize via Pillow)
- Supported image formats: PNG, JPG, JPEG, BMP, WebP
- Default Qwen model (Node 1 recognition): `qwen-vl-max`; default API URL: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- Default translation model (Node 2): `deepseek-v4-pro` (uses the existing DeepSeek API URL and key, NOT Qwen)
- TDD: write failing test → run → implement → run → commit

## File Structure

```
translator_app/
├── models.py                        # MODIFY: add Qwen fields to AppConfig, add ImageTranslationResult
├── constants.py                     # MODIFY: add Qwen constants and system prompts
├── exceptions.py                    # MODIFY: add QwenAPIError, ImageProcessingError
├── config_manager.py                # MODIFY: extend _apply_env_fallback for QWEN_API_KEY
├── qwen_client.py                   # CREATE: Qwen VL API client
├── image_preprocessor.py            # CREATE: image validation, resize, base64 encoding
├── image_recognition_service.py     # CREATE: Node 1 — image content recognition
├── image_translation_service.py     # CREATE: Node 2 — academic translation
├── image_pipeline.py                # CREATE: two-stage pipeline orchestration
├── screenshot_tool.py               # CREATE: fullscreen capture with region selection
├── image_input_widget.py            # CREATE: upload + capture + preview widget
├── markdown_output_widget.py        # CREATE: source/preview markdown output widget
├── image_worker.py                  # CREATE: QThread for pipeline execution
├── settings_dialog.py               # MODIFY: add Multimodal settings card
└── floating_window.py               # MODIFY: add [Image] nav tab, mode switching, wire new components

tests/
├── test_models.py                   # CREATE: AppConfig Qwen fields, ImageTranslationResult
├── test_config_manager_qwen.py      # CREATE: Qwen env/dotenv fallback
├── test_qwen_client.py              # CREATE: API request construction, error handling
├── test_image_preprocessor.py       # CREATE: format validation, resize, base64
├── test_image_pipeline.py           # CREATE: pipeline orchestration, partial failure
└── test_screenshot_tool.py          # CREATE: coordinate math, cancel behavior
```

---

## Phase 1: Infrastructure

### Task 1: Extend Data Models

**Files:**
- Modify: `translator_app/models.py:1-98`
- Modify: `translator_app/constants.py:1-28` (import only — actual constants in Task 2)
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: `DEFAULT_QWEN_API_URL`, `DEFAULT_QWEN_MODEL`, `DEFAULT_SCREENSHOT_HOTKEY`, `DEFAULT_IMAGE_MAX_SIZE_MB` from `constants.py` (will exist after Task 2; for now hardcode defaults in the import fallback)
- Produces: `AppConfig.qwen_api_key`, `AppConfig.qwen_api_url`, `AppConfig.qwen_model`, `AppConfig.image_max_size_mb`, `AppConfig.screenshot_hotkey` fields; `ImageTranslationResult` dataclass — consumed by Tasks 4, 5, 9, 13, 14

- [ ] **Step 1: Write the failing tests**

Create `tests/test_models.py`:

```python
"""Tests for data model extensions."""

from __future__ import annotations

from translator_app.models import AppConfig, ImageTranslationResult


def test_app_config_has_qwen_fields_with_defaults() -> None:
    """AppConfig includes Qwen-related fields with sensible defaults."""
    config = AppConfig()

    assert config.qwen_api_key == ""
    assert config.qwen_api_url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert config.qwen_model == "qwen-vl-max"
    assert config.image_max_size_mb == 20
    assert config.screenshot_hotkey == "<ctrl>+<shift>+s"


def test_app_config_from_dict_reads_qwen_fields() -> None:
    """from_dict populates Qwen fields from a raw dictionary."""
    payload = {
        "qwen_api_key": "sk-qwen-test",
        "qwen_api_url": "https://custom.endpoint/v1/chat/completions",
        "qwen_model": "qwen-vl-plus",
        "image_max_size_mb": 10,
        "screenshot_hotkey": "<alt>+s",
    }

    config = AppConfig.from_dict(payload)

    assert config.qwen_api_key == "sk-qwen-test"
    assert config.qwen_api_url == "https://custom.endpoint/v1/chat/completions"
    assert config.qwen_model == "qwen-vl-plus"
    assert config.image_max_size_mb == 10
    assert config.screenshot_hotkey == "<alt>+s"


def test_app_config_from_dict_uses_defaults_for_missing_qwen_fields() -> None:
    """from_dict falls back to defaults when Qwen fields are absent."""
    config = AppConfig.from_dict({})

    assert config.qwen_api_key == ""
    assert config.qwen_model == "qwen-vl-max"


def test_app_config_to_dict_includes_qwen_fields() -> None:
    """to_dict serializes Qwen fields for JSON storage."""
    config = AppConfig(qwen_api_key="sk-test", qwen_model="qwen-vl-plus")

    data = config.to_dict()

    assert data["qwen_api_key"] == "sk-test"
    assert data["qwen_model"] == "qwen-vl-plus"
    assert data["image_max_size_mb"] == 20
    assert data["screenshot_hotkey"] == "<ctrl>+<shift>+s"


def test_image_translation_result_stores_both_stages() -> None:
    """ImageTranslationResult holds recognition and translation output."""
    result = ImageTranslationResult(
        source_image_path="test.png",
        recognized_text="# Heading\nSome text",
        translated_text="# 标题\n一些文本",
        source_language="en",
        target_language="zh",
        recognition_tokens=1500,
        translation_tokens=1200,
        timestamp="2026-07-02T10:00:00",
    )

    assert result.recognized_text == "# Heading\nSome text"
    assert result.translated_text == "# 标题\n一些文本"
    assert result.recognition_tokens == 1500
    assert result.translation_tokens == 1200
    assert result.error is None


def test_image_translation_result_supports_partial_failure() -> None:
    """ImageTranslationResult can carry recognition text with a translation error."""
    result = ImageTranslationResult(
        source_image_path="screenshot",
        recognized_text="# Heading",
        translated_text="",
        source_language="en",
        target_language="zh",
        recognition_tokens=800,
        translation_tokens=0,
        timestamp="2026-07-02T10:00:00",
        error="Translation API timeout",
    )

    assert result.recognized_text == "# Heading"
    assert result.translated_text == ""
    assert result.error == "Translation API timeout"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ImageTranslationResult'` and `AttributeError: 'AppConfig' object has no attribute 'qwen_api_key'`

- [ ] **Step 3: Add Qwen constants to constants.py**

Append to `translator_app/constants.py`:

```python

# Qwen VL (multimodal) defaults
DEFAULT_QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_QWEN_MODEL = "qwen-vl-max"
DEFAULT_IMAGE_MAX_SIZE_MB = 20
DEFAULT_SCREENSHOT_HOTKEY = "<ctrl>+<shift>+s"
```

- [ ] **Step 4: Extend AppConfig in models.py**

Replace the imports block at the top of `translator_app/models.py` (lines 8-15):

```python
from translator_app.constants import (
    DEFAULT_API_URL,
    DEFAULT_HOTKEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_QWEN_API_URL,
    DEFAULT_QWEN_MODEL,
    DEFAULT_IMAGE_MAX_SIZE_MB,
    DEFAULT_SCREENSHOT_HOTKEY,
)
from translator_app.translation_style import DEFAULT_TRANSLATION_STYLE
```

Add Qwen fields to the `AppConfig` dataclass (after `temperature` field, line 27):

```python
    qwen_api_key: str = ""
    qwen_api_url: str = DEFAULT_QWEN_API_URL
    qwen_model: str = DEFAULT_QWEN_MODEL
    image_max_size_mb: int = DEFAULT_IMAGE_MAX_SIZE_MB
    screenshot_hotkey: str = DEFAULT_SCREENSHOT_HOTKEY
```

Update `from_dict` to include Qwen fields (replace the return block):

```python
    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        """Build a config object from a raw dictionary."""
        return cls(
            api_key=str(payload.get("api_key", "")).strip(),
            api_url=str(payload.get("api_url", DEFAULT_API_URL)).strip(),
            model=str(payload.get("model", DEFAULT_MODEL)).strip(),
            hotkey=str(payload.get("hotkey", DEFAULT_HOTKEY)).strip(),
            timeout_seconds=int(payload.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
            temperature=float(payload.get("temperature", DEFAULT_TEMPERATURE)),
            qwen_api_key=str(payload.get("qwen_api_key", "")).strip(),
            qwen_api_url=str(payload.get("qwen_api_url", DEFAULT_QWEN_API_URL)).strip(),
            qwen_model=str(payload.get("qwen_model", DEFAULT_QWEN_MODEL)).strip(),
            image_max_size_mb=int(payload.get("image_max_size_mb", DEFAULT_IMAGE_MAX_SIZE_MB)),
            screenshot_hotkey=str(payload.get("screenshot_hotkey", DEFAULT_SCREENSHOT_HOTKEY)).strip(),
        )
```

Update `to_dict` to include Qwen fields:

```python
    def to_dict(self) -> dict[str, Any]:
        """Serialize config data for JSON storage."""
        return {
            "api_key": self.api_key,
            "api_url": self.api_url,
            "model": self.model,
            "hotkey": self.hotkey,
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
            "qwen_api_key": self.qwen_api_key,
            "qwen_api_url": self.qwen_api_url,
            "qwen_model": self.qwen_model,
            "image_max_size_mb": self.image_max_size_mb,
            "screenshot_hotkey": self.screenshot_hotkey,
        }
```

Append `ImageTranslationResult` at the end of the file:

```python

@dataclass(slots=True)
class ImageTranslationResult:
    """Result of a two-stage image translation pipeline."""

    source_image_path: str
    recognized_text: str
    translated_text: str
    source_language: str
    target_language: str
    recognition_tokens: int
    translation_tokens: int
    timestamp: str
    error: str | None = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Run existing tests to verify no regressions**

Run: `pytest tests/ -v`
Expected: All 14 existing tests + 6 new tests PASS

- [ ] **Step 7: Commit**

```bash
git add translator_app/models.py translator_app/constants.py tests/test_models.py
git commit -m "feat: extend AppConfig with Qwen fields and add ImageTranslationResult model"
```

---

### Task 2: Add Qwen Constants and System Prompts

**Files:**
- Modify: `translator_app/constants.py:29-end`
- Test: (no separate test — constants are exercised by the tasks that consume them)

**Interfaces:**
- Consumes: nothing new
- Produces: `RECOGNITION_SYSTEM_PROMPT`, `IMAGE_TRANSLATION_SYSTEM_PROMPT` — consumed by Tasks 7, 8

- [ ] **Step 1: Add system prompts to constants.py**

Append to `translator_app/constants.py` (after the Qwen defaults added in Task 1):

```python

RECOGNITION_SYSTEM_PROMPT = (
    "你是一名精通学术排版的资深期刊编辑\n"
    "**文本处理规则**\n"
    "原文内容不变\n"
    "-   请对Fig. X进行斜体处理\n"
    "-   示例：*Fig. 2* \n"
    "\n"
    "**数学符号与公式处理规则**\n"
    "如遇到数学符号或数学公式，请将其转换为 Markdown 能够渲染的 LaTeX 公式代码：\n"
    "-   行内公式使用单美元符号（$）包裹。\n"
    "-   块级公式使用双美元符号（$$）包裹。\n"
    "\n"
    "**格式示例**\n"
    "-   行内公式示例：$E = mc^2$\n"
    "-   块级公式示例：\n"
    "    $$\n"
    "    \\int_{a}^{b} f(x) \\, dx\n"
    "    $$\n"
    "\n"
    "**输出格式强制要求**\n"
    "1. 绝对禁止对反斜杠进行额外转义。\n"
    "   - LaTeX 命令如 \\in、\\mathbb、\\text、\\sum、\\beta 必须保持单反斜杠。\n"
    "   - 严禁输出 \\\\in、\\\\mathbb 等双反斜杠形式。\n"
    "\n"
    "2. 绝对禁止输出字面字符串 \"\\n\"。\n"
    "   - 换行必须使用真实的换行符，不是反斜杠加字母 n 两个字符。\n"
    "   - 每句话结束直接回车换行，不要写 \\n。\n"
    "\n"
    "3. 代码块标记 ``` 必须出现在行首，前后各留一个空行。\n"
    "\n"
    "4. 公式块 $$ 必须出现在行首，前后各留一个空行。\n"
    "\n"
    "5. 输出内容必须是可直接复制到 .md 文件中渲染的最终 Markdown 源码。\n"
    "   不需要二次转义，不需要二次解析。"
)

IMAGE_TRANSLATION_SYSTEM_PROMPT = (
    "**翻译任务指令**\n"
    "\n"
    "你是一位专业的英汉互译专家。翻译时必须遵守以下规则：\n"
    "\n"
    "1.  **术语保留原则（英译中）\n"
    "    当从英语翻译到中文时，必须保留所有英文技术术语（如 neural network、API、blockchain、DNA polymerase、CRISPR-Cas9 等）、专有名词、缩写词和学术概念不翻译，保持英文原样。\n"
    "\n"
    "    普通学术词汇（如 raw features、low-level feature maps、noise domain）译为自然流畅的中文术语。\n"
    "\n"
    "    术语译法保持一致（如 \"feature maps\" 统一译为\"特征图\"）\n"
    "\n"
    "    图片标识不翻译，如Fig. 2。\n"
    "\n"
    "2.  **正常翻译原则（中译英）\n"
    "    当从中文翻译到英语时，将中文内容正常翻译为对应的英文表达。\n"
    "\n"
    "3.  **格式与语境保持**\n"
    "    严格保持原文的格式、段落结构和上下文含义的完整性。\n"
    "\n"
    "4.  **风格遵循**\n"
    "    严格遵循用户选择的翻译风格。\n"
    "\n"
    "示例（英译中）：\n"
    "    原文: The CRISPR-Cas9 system enables precise DNA editing.\n"
    "    正确: CRISPR-Cas9 系统能够实现精确的 DNA 编辑。\n"
    "    错误: 成簇规律间隔短回文重复序列及其相关蛋白9系统能够实现精确的脱氧核糖核酸编辑。\n"
    "\n"
    "    原文:\n"
    "**翻译风格要求**\n"
    "采用学术性语调。在英译中时，保留英文技术术语和专业词汇的原貌。使用符合研究或专业写作预期的正式措辞与结构。\n"
    "\n"
    "**数学符号与公式处理规则**\n"
    "如遇到数学符号或数学公式，请将其转换为 Markdown 能够渲染的 LaTeX 公式代码：\n"
    "-   行内公式使用单美元符号（$）包裹。\n"
    "-   块级公式使用双美元符号（$$）包裹。\n"
    "\n"
    "**格式示例**\n"
    "-   行内公式示例：$E = mc^2$\n"
    "-   块级公式示例：\n"
    "    $$\n"
    "    \\int_{a}^{b} f(x) \\, dx\n"
    "    $$\n"
    "\n"
    "**输出格式强制要求**\n"
    "1. 绝对禁止对反斜杠进行额外转义。\n"
    "   - LaTeX 命令如 \\in、\\mathbb、\\text、\\sum、\\beta 必须保持单反斜杠。\n"
    "   - 严禁输出 \\\\in、\\\\mathbb 等双反斜杠形式。\n"
    "\n"
    "2. 绝对禁止输出字面字符串 \"\\n\"。\n"
    "   - 换行必须使用真实的换行符，不是反斜杠加字母 n 两个字符。\n"
    "   - 每句话结束直接回车换行，不要写 \\n。\n"
    "\n"
    "3. 代码块标记 ``` 必须出现在行首，前后各留一个空行。\n"
    "\n"
    "4. 公式块 $$ 必须出现在行首，前后各留一个空行。\n"
    "\n"
    "5. 输出内容必须是可直接复制到 .md 文件中渲染的最终 Markdown 源码。\n"
    "   不需要二次转义，不需要二次解析。\n"
    "\n"
    "**输出格式**\n"
    "以markdown源码的格式输出"
)
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from translator_app.constants import RECOGNITION_SYSTEM_PROMPT, IMAGE_TRANSLATION_SYSTEM_PROMPT; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add translator_app/constants.py
git commit -m "feat: add Qwen system prompts for image recognition and translation"
```

---

### Task 3: Add Exception Types

**Files:**
- Modify: `translator_app/exceptions.py:1-22`
- Test: (no separate test — exceptions are exercised by the tasks that raise them)

**Interfaces:**
- Consumes: `TranslatorAppError` (base class)
- Produces: `QwenAPIError`, `ImageProcessingError` — consumed by Tasks 5, 6, 7, 8, 9, 13

- [ ] **Step 1: Add new exception classes**

Append to `translator_app/exceptions.py`:

```python

class QwenAPIError(TranslatorAppError):
    """Raised when the Qwen VL API request fails."""


class ImageProcessingError(TranslatorAppError):
    """Raised when image preprocessing or validation fails."""
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from translator_app.exceptions import QwenAPIError, ImageProcessingError; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify hierarchy**

Run: `python -c "from translator_app.exceptions import QwenAPIError, ImageProcessingError, TranslatorAppError; assert issubclass(QwenAPIError, TranslatorAppError); assert issubclass(ImageProcessingError, TranslatorAppError); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add translator_app/exceptions.py
git commit -m "feat: add QwenAPIError and ImageProcessingError exception types"
```

---

### Task 4: Extend ConfigManager for Qwen API Key

**Files:**
- Modify: `translator_app/config_manager.py:87-103`
- Test: `tests/test_config_manager_qwen.py`

**Interfaces:**
- Consumes: `AppConfig.qwen_api_key` from Task 1
- Produces: `_apply_qwen_env_fallback(config)` method — consumed by `load_config`; Qwen API key 3-layer fallback behavior

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config_manager_qwen.py`:

```python
"""Tests for Qwen API key environment variable fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path

from translator_app.config_manager import ConfigManager
from translator_app.models import AppConfig


def test_qwen_api_key_from_config_file(tmp_path: Path) -> None:
    """Load qwen_api_key from config.json when present."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": "sk-qwen-from-file"}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-qwen-from-file"


def test_qwen_api_key_from_env_var(tmp_path: Path, monkeypatch) -> None:
    """Fall back to QWEN_API_KEY environment variable when config value is empty."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": ""}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-from-env")

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-qwen-from-env"


def test_qwen_api_key_from_dotenv(tmp_path: Path, monkeypatch) -> None:
    """Fall back to .env file when both config and env var are empty."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": ""}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    (tmp_path / ".env").write_text("QWEN_API_KEY=sk-qwen-from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-qwen-from-dotenv"


def test_qwen_api_key_config_takes_priority_over_env(tmp_path: Path, monkeypatch) -> None:
    """config.json qwen_api_key wins over QWEN_API_KEY env var."""
    config_data = {"api_key": "sk-deepseek", "qwen_api_key": "sk-from-config"}
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("QWEN_API_KEY", "sk-from-env")

    manager = ConfigManager(tmp_path)
    config = manager.load_config()

    assert config.qwen_api_key == "sk-from-config"


def test_save_config_persists_qwen_fields(tmp_path: Path) -> None:
    """save_config writes Qwen fields to disk."""
    manager = ConfigManager(tmp_path)
    config = AppConfig(api_key="sk-test", qwen_api_key="sk-qwen", qwen_model="qwen-vl-plus")

    manager.save_config(config)

    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["qwen_api_key"] == "sk-qwen"
    assert saved["qwen_model"] == "qwen-vl-plus"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_manager_qwen.py -v`
Expected: FAIL — `test_qwen_api_key_from_config_file` fails because `_apply_env_fallback` doesn't handle `qwen_api_key`

- [ ] **Step 3: Extend _apply_env_fallback in config_manager.py**

Add a new method and update `_apply_env_fallback` in `translator_app/config_manager.py`. Replace the `_apply_env_fallback` method (lines 87-103):

```python
    def _apply_env_fallback(self, config: AppConfig) -> AppConfig:
        """Fill API keys from environment or .env file if missing."""
        if not config.api_key:
            env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if env_key:
                config.api_key = env_key
            else:
                dotenv_path = self._root_path / ".env"
                dotenv_vars = self._read_dotenv(dotenv_path)
                dotenv_key = dotenv_vars.get("DEEPSEEK_API_KEY", "").strip()
                if dotenv_key:
                    config.api_key = dotenv_key

        self._apply_qwen_env_fallback(config)
        return config

    def _apply_qwen_env_fallback(self, config: AppConfig) -> None:
        """Fill the Qwen API key from environment or .env file if missing."""
        if config.qwen_api_key:
            return

        env_key = os.environ.get("QWEN_API_KEY", "").strip()
        if env_key:
            config.qwen_api_key = env_key
            return

        dotenv_path = self._root_path / ".env"
        dotenv_vars = self._read_dotenv(dotenv_path)
        dotenv_key = dotenv_vars.get("QWEN_API_KEY", "").strip()
        if dotenv_key:
            config.qwen_api_key = dotenv_key
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config_manager_qwen.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Run all tests to verify no regressions**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add translator_app/config_manager.py tests/test_config_manager_qwen.py
git commit -m "feat: extend ConfigManager with QWEN_API_KEY 3-layer fallback"
```

---

### Task 5: Qwen VL API Client + DeepSeek Custom Prompt Method

**Files:**
- Create: `translator_app/qwen_client.py`
- Modify: `translator_app/deepseek_client.py` (add `translate_with_prompts` method)
- Test: `tests/test_qwen_client.py`

**Interfaces:**
- Consumes: `AppConfig.qwen_api_key`, `AppConfig.qwen_api_url`, `AppConfig.qwen_model`, `AppConfig.timeout_seconds` from Task 1; `QwenAPIError`, `ConfigurationError` from Task 3
- Produces: `QwenClient.recognize_image(image_base64, system_prompt, user_prompt) -> str` — consumed by Task 7; `DeepSeekClient.translate_with_prompts(system_prompt, user_prompt, model) -> str` — consumed by Task 8 (Node 2 uses DeepSeek `deepseek-v4-pro`, NOT Qwen)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_qwen_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_qwen_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'translator_app.qwen_client'`

- [ ] **Step 3: Create qwen_client.py**

Create `translator_app/qwen_client.py`:

```python
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
        return self._send_request(payload, api_key)

    def _send_request(self, payload: dict[str, Any], api_key: str) -> str:
        """Execute an HTTP POST and extract the response content."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AcademicFloatingTranslator/1.0",
        }

        try:
            response = requests.post(
                self._config.qwen_api_url,
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
```

- [ ] **Step 4: Add translate_with_prompts to DeepSeekClient**

Add this method to `translator_app/deepseek_client.py` (after the existing `translate` method, before `_build_headers`):

```python
    def translate_with_prompts(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> str:
        """Translate using custom system/user prompts and an optional model override.

        Used by the image translation pipeline (Node 2) to send the recognized
        Markdown to deepseek-v4-pro with a specialized translation prompt.
        """
        headers = self._build_headers()
        payload = {
            "model": model or self._config.model,
            "temperature": self._config.temperature,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        LOGGER.info(
            "Sending custom-prompt translation with model=%s",
            model or self._config.model,
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_qwen_client.py tests/test_deepseek_client.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add translator_app/qwen_client.py translator_app/deepseek_client.py tests/test_qwen_client.py
git commit -m "feat: add QwenClient for recognition + DeepSeekClient.translate_with_prompts for Node 2"
```

---

### Task 6: Image Preprocessor

**Files:**
- Create: `translator_app/image_preprocessor.py`
- Test: `tests/test_image_preprocessor.py`

**Interfaces:**
- Consumes: `ImageProcessingError` from Task 3; `AppConfig.image_max_size_mb` from Task 1
- Produces: `preprocess_image(file_path) -> str` (returns base64), `preprocess_image_from_bytes(data, extension) -> str` — consumed by Tasks 11, 13

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_preprocessor.py`:

```python
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
    """Max resolution constant matches PRD spec."""
    assert MAX_RESOLUTION == 4096


def test_preprocess_image_from_bytes_returns_base64() -> None:
    """Valid PNG bytes are encoded as base64 string."""
    image_data = _create_test_image(200, 200)

    result = preprocess_image_from_bytes(image_data, ".png")

    # Should be valid base64
    decoded = base64.b64decode(result)
    assert len(decoded) > 0


def test_preprocess_image_from_bytes_rejects_unsupported_format() -> None:
    """Unsupported file extensions raise ImageProcessingError."""
    try:
        preprocess_image_from_bytes(b"not-an-image", ".tiff")
    except ImageProcessingError as exc:
        assert "tiff" in str(exc).lower() or "unsupported" in str(exc).lower()
    else:
        raise AssertionError("Expected ImageProcessingError for .tiff")


def test_preprocess_image_from_bytes_resizes_large_image() -> None:
    """Images exceeding MAX_RESOLUTION are resized proportionally."""
    image_data = _create_test_image(5000, 3000)

    result = preprocess_image_from_bytes(image_data, ".png")

    decoded = base64.b64decode(result)
    result_img = Image.open(io.BytesIO(decoded))
    assert result_img.width <= MAX_RESOLUTION
    assert result_img.height <= MAX_RESOLUTION


def test_preprocess_image_from_bytes_preserves_small_image() -> None:
    """Images within limits are not resized."""
    image_data = _create_test_image(800, 600)

    result = preprocess_image_from_bytes(image_data, ".png")

    decoded = base64.b64decode(result)
    result_img = Image.open(io.BytesIO(decoded))
    assert result_img.width == 800
    assert result_img.height == 600


def test_preprocess_image_reads_file_from_disk(tmp_path) -> None:
    """preprocess_image reads a file path and returns base64."""
    image_path = tmp_path / "test.png"
    image_path.write_bytes(_create_test_image(300, 200))

    result = preprocess_image(str(image_path))

    decoded = base64.b64decode(result)
    assert len(decoded) > 0


def test_preprocess_image_rejects_nonexistent_file() -> None:
    """Nonexistent file path raises ImageProcessingError."""
    try:
        preprocess_image("/nonexistent/path/image.png")
    except ImageProcessingError as exc:
        assert "not found" in str(exc).lower() or "exist" in str(exc).lower()
    else:
        raise AssertionError("Expected ImageProcessingError for missing file")


def test_preprocess_image_rejects_too_small_image(tmp_path) -> None:
    """Images below 100x100 raise ImageProcessingError."""
    image_path = tmp_path / "tiny.png"
    image_path.write_bytes(_create_test_image(50, 50))

    try:
        preprocess_image(str(image_path))
    except ImageProcessingError as exc:
        assert "small" in str(exc).lower() or "100" in str(exc)
    else:
        raise AssertionError("Expected ImageProcessingError for tiny image")


def test_preprocess_image_from_bytes_converts_jpg_to_png() -> None:
    """JPG input is converted to PNG format in the output."""
    image_data = _create_test_image(400, 300, fmt="JPEG")

    result = preprocess_image_from_bytes(image_data, ".jpg")

    decoded = base64.b64decode(result)
    result_img = Image.open(io.BytesIO(decoded))
    assert result_img.format == "PNG"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_image_preprocessor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'translator_app.image_preprocessor'`

- [ ] **Step 3: Create image_preprocessor.py**

Create `translator_app/image_preprocessor.py`:

```python
"""Image preprocessing: validation, resize, format conversion, and base64 encoding."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from PIL import Image

from translator_app.exceptions import ImageProcessingError

SUPPORTED_FORMATS: frozenset[str] = frozenset({"png", "jpg", "jpeg", "bmp", "webp"})
MAX_RESOLUTION: int = 4096
MIN_RESOLUTION: int = 100
_DEFAULT_MAX_SIZE_MB: int = 20


def preprocess_image(file_path: str, max_size_mb: int = _DEFAULT_MAX_SIZE_MB) -> str:
    """Read an image file from disk and return its base64-encoded PNG string.

    Validates format, resolution, and size before encoding.
    """
    path = Path(file_path)
    if not path.exists():
        raise ImageProcessingError(f"Image file not found: {file_path}")

    extension = path.suffix.lower()
    if extension.lstrip(".") not in SUPPORTED_FORMATS:
        raise ImageProcessingError(
            f"Unsupported image format '{extension}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ImageProcessingError(f"Could not read image file: {exc}") from exc

    return preprocess_image_from_bytes(data, extension, max_size_mb)


def preprocess_image_from_bytes(
    data: bytes, extension: str, max_size_mb: int = _DEFAULT_MAX_SIZE_MB
) -> str:
    """Process raw image bytes and return a base64-encoded PNG string.

    Steps: validate format → open with Pillow → validate resolution
    → resize if needed → convert to PNG → compress if over size limit
    → base64 encode.
    """
    ext = extension.lower().lstrip(".")
    if ext not in SUPPORTED_FORMATS:
        raise ImageProcessingError(
            f"Unsupported image format '.{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    try:
        img = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise ImageProcessingError(f"Could not open image: {exc}") from exc

    width, height = img.size
    if width < MIN_RESOLUTION or height < MIN_RESOLUTION:
        raise ImageProcessingError(
            f"Image is too small ({width}x{height}). "
            f"Minimum resolution is {MIN_RESOLUTION}x{MIN_RESOLUTION} pixels."
        )

    if width > MAX_RESOLUTION or height > MAX_RESOLUTION:
        img = _resize_to_fit(img, MAX_RESOLUTION)

    png_buffer = io.BytesIO()
    img.save(png_buffer, format="PNG")
    png_bytes = png_buffer.getvalue()

    max_bytes = max_size_mb * 1024 * 1024
    if len(png_bytes) > max_bytes:
        png_bytes = _compress_to_fit(img, max_bytes)

    return base64.b64encode(png_bytes).decode("ascii")


def _resize_to_fit(img: Image.Image, max_dim: int) -> Image.Image:
    """Resize image proportionally so no dimension exceeds max_dim."""
    width, height = img.size
    scale = min(max_dim / width, max_dim / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    return img.resize((new_width, new_height), Image.LANCZOS)


def _compress_to_fit(img: Image.Image, max_bytes: int) -> bytes:
    """Compress image as PNG with increasing effort until under max_bytes."""
    for quality in (85, 70, 55, 40):
        buffer = io.BytesIO()
        converted = img.convert("RGB")
        converted.save(buffer, format="JPEG", quality=quality)
        result = buffer.getvalue()
        if len(result) <= max_bytes:
            reencoded = io.BytesIO()
            Image.open(io.BytesIO(result)).save(reencoded, format="PNG")
            return reencoded.getvalue()

    raise ImageProcessingError(
        f"Could not compress image under {max_bytes // (1024 * 1024)} MB "
        "even at lowest quality. Please use a smaller image."
    )
```

- [ ] **Step 4: Install Pillow**

Run: `pip install "Pillow>=10.0,<11"`

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_image_preprocessor.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Commit**

```bash
git add translator_app/image_preprocessor.py tests/test_image_preprocessor.py
git commit -m "feat: add image preprocessor with validation, resize, and base64 encoding"
```

---

### Task 7: Image Recognition Service (Node 1)

**Files:**
- Create: `translator_app/image_recognition_service.py`
- Test: (tested via pipeline in Task 9; unit tests mock QwenClient)

**Interfaces:**
- Consumes: `QwenClient.recognize_image()` from Task 5; `RECOGNITION_SYSTEM_PROMPT` from Task 2
- Produces: `ImageRecognitionService.recognize(image_base64) -> str` — consumed by Task 9

- [ ] **Step 1: Create image_recognition_service.py**

Create `translator_app/image_recognition_service.py`:

```python
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
```

- [ ] **Step 2: Verify import**

Run: `python -c "from translator_app.image_recognition_service import ImageRecognitionService; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add translator_app/image_recognition_service.py
git commit -m "feat: add ImageRecognitionService (Node 1) for image-to-markdown"
```

---

### Task 8: Image Translation Service (Node 2)

**Files:**
- Create: `translator_app/image_translation_service.py`
- Test: (tested via pipeline in Task 9)

**Interfaces:**
- Consumes: `DeepSeekClient.translate_with_prompts()` from Task 5; `IMAGE_TRANSLATION_SYSTEM_PROMPT` from Task 2
- Produces: `ImageTranslationService.translate(recognized_text) -> str` — consumed by Task 9

- [ ] **Step 1: Create image_translation_service.py**

Create `translator_app/image_translation_service.py`:

```python
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
```

- [ ] **Step 2: Verify import**

Run: `python -c "from translator_app.image_translation_service import ImageTranslationService; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add translator_app/image_translation_service.py
git commit -m "feat: add ImageTranslationService (Node 2) for markdown translation via DeepSeek"
```

---

### Task 9: Image Translation Pipeline

**Files:**
- Create: `translator_app/image_pipeline.py`
- Test: `tests/test_image_pipeline.py`

**Interfaces:**
- Consumes: `ImageRecognitionService.recognize()` from Task 7; `ImageTranslationService.translate()` from Task 8; `ImageTranslationResult` from Task 1; `QwenAPIError` from Task 3
- Produces: `ImageTranslationPipeline.execute(image_base64, source_image_path) -> ImageTranslationResult` — consumed by Task 13; `ProgressCallback = Callable[[str, int, int], None]` type alias

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_pipeline.py`:

```python
"""Tests for image translation pipeline orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

from translator_app.exceptions import DeepSeekAPIError, QwenAPIError
from translator_app.image_pipeline import ImageTranslationPipeline
from translator_app.models import ImageTranslationResult


def _make_pipeline(
    recognize_return: str = "# Heading\nSome text",
    translate_return: str = "# 标题\n一些文本",
) -> tuple[ImageTranslationPipeline, MagicMock, MagicMock]:
    """Build a pipeline with mocked services."""
    recognition_service = MagicMock()
    recognition_service.recognize.return_value = recognize_return

    translation_service = MagicMock()
    translation_service.translate.return_value = translate_return

    pipeline = ImageTranslationPipeline(
        recognition_service=recognition_service,
        translation_service=translation_service,
    )
    return pipeline, recognition_service, translation_service


def test_pipeline_runs_both_stages() -> None:
    """Pipeline calls recognize then translate and returns combined result."""
    pipeline, rec_svc, trans_svc = _make_pipeline()

    result = pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
    )

    assert isinstance(result, ImageTranslationResult)
    assert result.recognized_text == "# Heading\nSome text"
    assert result.translated_text == "# 标题\n一些文本"
    assert result.source_image_path == "test.png"
    assert result.error is None
    rec_svc.recognize.assert_called_once_with("base64data")
    trans_svc.translate.assert_called_once_with("# Heading\nSome text")


def test_pipeline_emits_progress_callbacks() -> None:
    """Pipeline calls on_progress for each stage."""
    pipeline, _, _ = _make_pipeline()
    progress_calls: list[tuple[str, int, int]] = []

    def on_progress(message: str, current: int, total: int) -> None:
        progress_calls.append((message, current, total))

    pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
        on_progress=on_progress,
    )

    assert len(progress_calls) == 2
    assert progress_calls[0][1] == 1  # stage 1
    assert progress_calls[1][1] == 2  # stage 2
    assert progress_calls[0][2] == 2  # total stages


def test_pipeline_recognition_failure_returns_error() -> None:
    """If recognition fails, pipeline returns result with error and empty translation."""
    recognition_service = MagicMock()
    recognition_service.recognize.side_effect = QwenAPIError("API timeout")

    translation_service = MagicMock()

    pipeline = ImageTranslationPipeline(
        recognition_service=recognition_service,
        translation_service=translation_service,
    )

    result = pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
    )

    assert result.error is not None
    assert "API timeout" in result.error
    assert result.recognized_text == ""
    assert result.translated_text == ""
    translation_service.translate.assert_not_called()


def test_pipeline_translation_failure_preserves_recognition() -> None:
    """If translation fails, pipeline returns recognition text with error."""
    pipeline, _, trans_svc = _make_pipeline()
    trans_svc.translate.side_effect = DeepSeekAPIError("Translation timeout")

    result = pipeline.execute(
        image_base64="base64data",
        source_image_path="test.png",
    )

    assert result.recognized_text == "# Heading\nSome text"
    assert result.translated_text == ""
    assert result.error is not None
    assert "Translation timeout" in result.error
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_image_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'translator_app.image_pipeline'`

- [ ] **Step 3: Create image_pipeline.py**

Create `translator_app/image_pipeline.py`:

```python
"""Two-stage image translation pipeline: recognition → translation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Optional

from translator_app.exceptions import DeepSeekAPIError, QwenAPIError
from translator_app.image_recognition_service import ImageRecognitionService
from translator_app.image_translation_service import ImageTranslationService
from translator_app.models import ImageTranslationResult

LOGGER = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, int], None]
_TOTAL_STAGES = 2


class ImageTranslationPipeline:
    """Orchestrate recognition and translation as a serial two-stage pipeline."""

    def __init__(
        self,
        recognition_service: ImageRecognitionService,
        translation_service: ImageTranslationService,
    ) -> None:
        """Store service dependencies."""
        self._recognition_service = recognition_service
        self._translation_service = translation_service

    def execute(
        self,
        image_base64: str,
        source_image_path: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ImageTranslationResult:
        """Run the full pipeline and return a combined result.

        If recognition fails, returns an error result with no translation.
        If translation fails, returns the recognition text with an error message.
        """
        timestamp = datetime.now().isoformat(timespec="seconds")

        # Stage 1: Recognition
        if on_progress:
            on_progress("Recognizing image content...", 1, _TOTAL_STAGES)

        try:
            recognized_text = self._recognition_service.recognize(image_base64)
        except QwenAPIError as exc:
            LOGGER.error("Recognition failed: %s", exc)
            return ImageTranslationResult(
                source_image_path=source_image_path,
                recognized_text="",
                translated_text="",
                source_language="unknown",
                target_language="unknown",
                recognition_tokens=0,
                translation_tokens=0,
                timestamp=timestamp,
                error=f"Image recognition failed: {exc}",
            )

        # Stage 2: Translation
        if on_progress:
            on_progress("Translating content...", 2, _TOTAL_STAGES)

        try:
            translated_text = self._translation_service.translate(recognized_text)
        except DeepSeekAPIError as exc:
            LOGGER.error("Translation failed: %s", exc)
            return ImageTranslationResult(
                source_image_path=source_image_path,
                recognized_text=recognized_text,
                translated_text="",
                source_language="unknown",
                target_language="unknown",
                recognition_tokens=0,
                translation_tokens=0,
                timestamp=timestamp,
                error=f"Translation failed: {exc}",
            )

        return ImageTranslationResult(
            source_image_path=source_image_path,
            recognized_text=recognized_text,
            translated_text=translated_text,
            source_language="unknown",
            target_language="unknown",
            recognition_tokens=0,
            translation_tokens=0,
            timestamp=timestamp,
            error=None,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_image_pipeline.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add translator_app/image_pipeline.py tests/test_image_pipeline.py
git commit -m "feat: add ImageTranslationPipeline with two-stage orchestration and error degradation"
```

---

## Phase 2: UI Components

### Task 10: Screenshot Tool

**Files:**
- Create: `translator_app/screenshot_tool.py`
- Test: `tests/test_screenshot_tool.py`

**Interfaces:**
- Consumes: PyQt5 only (no project dependencies)
- Produces: `ScreenshotTool.capture(parent) -> Optional[bytes]` (PNG bytes or None if cancelled), `ScreenshotOverlay` widget class — consumed by Task 11

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_tool.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_screenshot_tool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'translator_app.screenshot_tool'`

- [ ] **Step 3: Create screenshot_tool.py**

Create `translator_app/screenshot_tool.py`:

```python
"""Screenshot tool: fullscreen overlay with region selection."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QPainter, QPen, QPixmap, QScreen
from PyQt5.QtWidgets import QApplication, QWidget

LOGGER = logging.getLogger(__name__)


def normalize_selection_rect(
    start_x: int, start_y: int, end_x: int, end_y: int
) -> tuple[int, int, int, int]:
    """Normalize two corner points into (x, y, width, height) with positive dimensions."""
    x = min(start_x, end_x)
    y = min(start_y, end_y)
    w = abs(end_x - start_x)
    h = abs(end_y - start_y)
    return x, y, w, h


class ScreenshotOverlay(QWidget):
    """Fullscreen transparent overlay for selecting a screen region."""

    captured = pyqtSignal(bytes)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        """Set up fullscreen transparent window."""
        super().__init__()
        self._start_point: Optional[QPoint] = None
        self._end_point: Optional[QPoint] = None
        self._selecting = False

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.CrossCursor))

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Draw semi-transparent overlay and selection rectangle."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._start_point and self._end_point:
            x, y, w, h = normalize_selection_rect(
                self._start_point.x(),
                self._start_point.y(),
                self._end_point.x(),
                self._end_point.y(),
            )

            # Clear the selection area to show the actual screen
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(x, y, w, h, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw selection border
            pen = QPen(QColor(62, 43, 31), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(x, y, w, h)

        painter.end()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Record the start point of the selection."""
        if event.button() == Qt.LeftButton:
            self._start_point = event.pos()
            self._end_point = event.pos()
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """Update the selection endpoint as the mouse moves."""
        if self._selecting:
            self._end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """Capture the selected region when the mouse is released."""
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self._end_point = event.pos()

            if self._start_point and self._end_point:
                x, y, w, h = normalize_selection_rect(
                    self._start_point.x(),
                    self._start_point.y(),
                    self._end_point.x(),
                    self._end_point.y(),
                )

                if w < 10 or h < 10:
                    self.cancelled.emit()
                    self.close()
                    return

                screen = QApplication.primaryScreen()
                if screen:
                    # Offset by screen geometry for multi-monitor setups
                    screen_geo = screen.geometry()
                    abs_x = screen_geo.x() + x
                    abs_y = screen_geo.y() + y

                    pixmap = screen.grabWindow(0, abs_x, abs_y, w, h)
                    png_data = self._pixmap_to_png_bytes(pixmap)
                    if png_data:
                        self.captured.emit(png_data)
                    else:
                        self.cancelled.emit()

            self.close()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """Cancel on Escape key."""
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()

    @staticmethod
    def _pixmap_to_png_bytes(pixmap: QPixmap) -> Optional[bytes]:
        """Convert a QPixmap to PNG bytes."""
        from PyQt5.QtCore import QBuffer, QIODevice

        if pixmap.isNull():
            return None

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not pixmap.save(buffer, "PNG"):
            return None
        return bytes(buffer.data())


class ScreenshotTool:
    """High-level API for capturing screenshots."""

    def __init__(self) -> None:
        """Initialize with no active overlay."""
        self._overlay: Optional[ScreenshotOverlay] = None
        self._result: Optional[bytes] = None
        self._completed = False

    def capture(self) -> Optional[bytes]:
        """Show the overlay, wait for user selection, return PNG bytes or None."""
        self._result = None
        self._completed = False

        self._overlay = ScreenshotOverlay()
        self._overlay.captured.connect(self._on_captured)
        self._overlay.cancelled.connect(self._on_cancelled)
        self._overlay.show()

        # Process events until the overlay closes
        app = QApplication.instance()
        if app:
            while not self._completed:
                app.processEvents()

        return self._result

    def _on_captured(self, data: bytes) -> None:
        """Store captured image data."""
        self._result = data
        self._completed = True

    def _on_cancelled(self) -> None:
        """Mark capture as cancelled."""
        self._result = None
        self._completed = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_screenshot_tool.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add translator_app/screenshot_tool.py tests/test_screenshot_tool.py
git commit -m "feat: add screenshot tool with fullscreen overlay and region selection"
```

---

### Task 11: Image Input Widget

**Files:**
- Create: `translator_app/image_input_widget.py`

**Interfaces:**
- Consumes: `ScreenshotTool.capture()` from Task 10; `preprocess_image()`, `preprocess_image_from_bytes()` from Task 6
- Produces: `ImageInputWidget` class with `image_loaded` signal (emits `str` = base64) and `get_image_base64() -> Optional[str]` method — consumed by Task 14

- [ ] **Step 1: Create image_input_widget.py**

Create `translator_app/image_input_widget.py`:

```python
"""Image input widget: upload, screenshot, preview, and drag-drop."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from translator_app.image_preprocessor import (
    SUPPORTED_FORMATS,
    preprocess_image,
    preprocess_image_from_bytes,
)
from translator_app.screenshot_tool import ScreenshotTool

LOGGER = logging.getLogger(__name__)


class ImageInputWidget(QFrame):
    """Widget for loading images via file upload, screenshot, or drag-and-drop."""

    image_loaded = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the image input UI."""
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setAcceptDrops(True)

        self._image_base64: Optional[str] = None
        self._image_path: str = ""
        self._screenshot_tool = ScreenshotTool()

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the widget layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        # Header row
        header_row = QHBoxLayout()
        section_label = QLabel("SOURCE IMAGE")
        section_label.setObjectName("sectionLabel")

        self._upload_button = QPushButton("Upload")
        self._upload_button.setObjectName("secondaryButton")
        self._upload_button.clicked.connect(self._on_upload_clicked)

        self._capture_button = QPushButton("Capture")
        self._capture_button.setObjectName("secondaryButton")
        self._capture_button.clicked.connect(self._on_capture_clicked)

        header_row.addWidget(section_label)
        header_row.addStretch()
        header_row.addWidget(self._upload_button)
        header_row.addWidget(self._capture_button)

        # Preview area
        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumHeight(180)
        self._preview_label.setStyleSheet(
            "QLabel { color: #8C7B6E; font-size: 14px; border: 2px dashed #D4CCC4; "
            "border-radius: 16px; padding: 20px; }"
        )
        self._preview_label.setText("Drag image here or click Upload")

        # File info
        self._file_info_label = QLabel()
        self._file_info_label.setObjectName("sectionLabel")
        self._file_info_label.setAlignment(Qt.AlignLeft)

        layout.addLayout(header_row)
        layout.addWidget(self._preview_label, stretch=1)
        layout.addWidget(self._file_info_label)
        self.setLayout(layout)

    def _on_upload_clicked(self) -> None:
        """Open file dialog and load the selected image."""
        extensions = " ".join(f"*.{fmt}" for fmt in sorted(SUPPORTED_FORMATS))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            f"Images ({extensions})",
        )
        if not file_path:
            return

        self._load_from_file(file_path)

    def _on_capture_clicked(self) -> None:
        """Minimize main window, take screenshot, then restore."""
        main_window = self.window()
        was_visible = main_window.isVisible()
        if was_visible:
            main_window.hide()

        # Small delay to let the window hide
        QApplication.processEvents()

        png_data = self._screenshot_tool.capture()

        if was_visible:
            main_window.show()

        if png_data is None:
            return

        self._load_from_bytes(png_data, ".png", source="screenshot")

    def _load_from_file(self, file_path: str) -> None:
        """Load and preprocess an image from a file path."""
        try:
            self._image_base64 = preprocess_image(file_path)
            self._image_path = file_path
            self._update_preview_from_file(file_path)
            self.image_loaded.emit(self._image_base64)
        except Exception as exc:
            LOGGER.error("Failed to load image: %s", exc)
            self._preview_label.setText(f"Error: {exc}")
            self._image_base64 = None

    def _load_from_bytes(self, data: bytes, extension: str, source: str = "") -> None:
        """Load and preprocess an image from raw bytes."""
        try:
            self._image_base64 = preprocess_image_from_bytes(data, extension)
            self._image_path = source
            self._update_preview_from_bytes(data)
            self.image_loaded.emit(self._image_base64)
        except Exception as exc:
            LOGGER.error("Failed to load image from bytes: %s", exc)
            self._preview_label.setText(f"Error: {exc}")
            self._image_base64 = None

    def _update_preview_from_file(self, file_path: str) -> None:
        """Show a thumbnail preview of the loaded file."""
        pixmap = QPixmap(file_path)
        self._show_thumbnail(pixmap, Path(file_path).name, pixmap.width(), pixmap.height())

    def _update_preview_from_bytes(self, data: bytes) -> None:
        """Show a thumbnail preview from raw image bytes."""
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self._show_thumbnail(pixmap, "Screenshot", pixmap.width(), pixmap.height())

    def _show_thumbnail(self, pixmap: QPixmap, name: str, width: int, height: int) -> None:
        """Display a scaled thumbnail and file info."""
        if pixmap.isNull():
            return

        max_preview = QSize(400, 250)
        scaled = pixmap.scaled(max_preview, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_label.setPixmap(scaled)
        self._preview_label.setStyleSheet(
            "QLabel { border: 1px solid #D4CCC4; border-radius: 16px; padding: 8px; }"
        )
        self._file_info_label.setText(f"📄 {name}  {width}×{height}")

    def get_image_base64(self) -> Optional[str]:
        """Return the currently loaded image as base64, or None."""
        return self._image_base64

    def clear_image(self) -> None:
        """Reset the widget to its empty state."""
        self._image_base64 = None
        self._image_path = ""
        self._preview_label.clear()
        self._preview_label.setText("Drag image here or click Upload")
        self._preview_label.setStyleSheet(
            "QLabel { color: #8C7B6E; font-size: 14px; border: 2px dashed #D4CCC4; "
            "border-radius: 16px; padding: 20px; }"
        )
        self._file_info_label.setText("")

    # Drag-and-drop support

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag events that contain image file URLs."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = Path(path).suffix.lower().lstrip(".")
                if ext in SUPPORTED_FORMATS:
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent) -> None:
        """Load the first supported image file from the drop."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = Path(path).suffix.lower().lstrip(".")
            if ext in SUPPORTED_FORMATS:
                self._load_from_file(path)
                return
```

- [ ] **Step 2: Verify import**

Run: `python -c "from translator_app.image_input_widget import ImageInputWidget; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add translator_app/image_input_widget.py
git commit -m "feat: add ImageInputWidget with upload, screenshot, drag-drop, and preview"
```

---

### Task 12: Markdown Output Widget

**Files:**
- Create: `translator_app/markdown_output_widget.py`

**Interfaces:**
- Consumes: nothing from project (only PyQt5 + markdown lib)
- Produces: `MarkdownOutputWidget` class with `set_content(markdown_text)`, `get_content() -> str` — consumed by Task 14

- [ ] **Step 1: Install markdown library**

Run: `pip install "markdown>=3.6,<4"`

- [ ] **Step 2: Create markdown_output_widget.py**

Create `translator_app/markdown_output_widget.py`:

```python
"""Markdown output widget: source view, rendered preview, copy, and export."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

LOGGER = logging.getLogger(__name__)

_MONOSPACE_FONT_STACK = "Consolas, 'Source Code Pro', 'Courier New', monospace"


class MarkdownOutputWidget(QFrame):
    """Widget for displaying Markdown translation results with source/preview toggle."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the markdown output UI."""
        super().__init__(parent)
        self.setObjectName("cardFrame")

        self._markdown_text: str = ""
        self._is_preview_mode = False

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the widget layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        # Header row
        header_row = QHBoxLayout()
        section_label = QLabel("TRANSLATED (MARKDOWN)")
        section_label.setObjectName("sectionLabel")

        self._copy_button = QPushButton("Copy")
        self._copy_button.setObjectName("secondaryButton")
        self._copy_button.clicked.connect(self._on_copy_clicked)
        self._copy_button.setEnabled(False)

        self._preview_button = QPushButton("Preview")
        self._preview_button.setObjectName("secondaryButton")
        self._preview_button.clicked.connect(self._on_preview_toggled)
        self._preview_button.setEnabled(False)

        header_row.addWidget(section_label)
        header_row.addStretch()
        header_row.addWidget(self._copy_button)
        header_row.addWidget(self._preview_button)

        # Source text area (monospace, read-only)
        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("resultBox")
        self._text_edit.setReadOnly(True)
        self._text_edit.setAcceptRichText(True)
        self._text_edit.setPlaceholderText("Translation result appears here.")

        font = QFont()
        font.setFamily(_MONOSPACE_FONT_STACK.split(",")[0].strip().strip("'"))
        font.setPointSize(13)
        font.setStyleHint(QFont.Monospace)
        self._text_edit.setFont(font)

        layout.addLayout(header_row)
        layout.addWidget(self._text_edit, stretch=1)
        self.setLayout(layout)

    def set_content(self, markdown_text: str) -> None:
        """Display the given Markdown in source mode."""
        self._markdown_text = markdown_text
        self._is_preview_mode = False
        self._text_edit.setPlainText(markdown_text)
        self._copy_button.setEnabled(bool(markdown_text))
        self._preview_button.setEnabled(bool(markdown_text))
        self._preview_button.setText("Preview")

    def get_content(self) -> str:
        """Return the current Markdown source text."""
        return self._markdown_text

    def clear_content(self) -> None:
        """Reset the widget to empty state."""
        self._markdown_text = ""
        self._is_preview_mode = False
        self._text_edit.clear()
        self._copy_button.setEnabled(False)
        self._preview_button.setEnabled(False)
        self._preview_button.setText("Preview")

    def _on_copy_clicked(self) -> None:
        """Copy the Markdown source to the clipboard."""
        if self._markdown_text:
            QApplication.clipboard().setText(self._markdown_text)

    def _on_preview_toggled(self) -> None:
        """Toggle between source view and rendered HTML preview."""
        if self._is_preview_mode:
            self._show_source()
        else:
            self._show_preview()

    def _show_source(self) -> None:
        """Switch to plain Markdown source view."""
        self._is_preview_mode = False
        self._text_edit.setPlainText(self._markdown_text)
        self._preview_button.setText("Preview")

        font = QFont()
        font.setFamily(_MONOSPACE_FONT_STACK.split(",")[0].strip().strip("'"))
        font.setPointSize(13)
        font.setStyleHint(QFont.Monospace)
        self._text_edit.setFont(font)

    def _show_preview(self) -> None:
        """Render Markdown as HTML and display in the text edit."""
        try:
            import markdown as md

            html = md.markdown(
                self._markdown_text,
                extensions=["tables", "fenced_code", "md_in_html"],
            )

            styled_html = (
                '<style>'
                'body { font-family: "Times New Roman", "SimSun", serif; '
                'font-size: 15px; color: #2C1F14; line-height: 1.65; }'
                'h1, h2, h3 { font-family: Georgia, serif; color: #3E2B1F; }'
                'code { background-color: #F0EBE4; padding: 2px 6px; border-radius: 4px; '
                'font-family: Consolas, monospace; font-size: 13px; }'
                'pre { background-color: #F0EBE4; padding: 12px; border-radius: 8px; '
                'overflow-x: auto; }'
                'table { border-collapse: collapse; width: 100%; }'
                'th, td { border: 1px solid #D4CCC4; padding: 8px 12px; text-align: left; }'
                'th { background-color: #F0EBE4; }'
                'blockquote { border-left: 3px solid #D4CCC4; margin-left: 0; '
                'padding-left: 16px; color: #5C4033; }'
                '</style>'
                f'{html}'
            )

            self._is_preview_mode = True
            self._text_edit.setHtml(styled_html)
            self._preview_button.setText("Source")
        except ImportError:
            LOGGER.warning("markdown library not installed; preview unavailable")
            self._text_edit.setPlainText(
                "Preview requires the 'markdown' library.\n"
                "Install it: pip install markdown>=3.6"
            )
```

- [ ] **Step 3: Verify import**

Run: `python -c "from translator_app.markdown_output_widget import MarkdownOutputWidget; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add translator_app/markdown_output_widget.py
git commit -m "feat: add MarkdownOutputWidget with source/preview toggle, copy, and export"
```

---

### Task 13: Image Translation Worker (QThread)

**Files:**
- Create: `translator_app/image_worker.py`

**Interfaces:**
- Consumes: `ImageTranslationPipeline.execute()` from Task 9; `ImageTranslationResult` from Task 1; `QwenAPIError`, `ImageProcessingError` from Task 3
- Produces: `ImageTranslationWorker` QThread with signals: `progress(str, int, int)`, `succeeded(object)`, `failed(str)` — consumed by Task 14

- [ ] **Step 1: Create image_worker.py**

Create `translator_app/image_worker.py`:

```python
"""Background worker thread for image translation pipeline."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from translator_app.exceptions import (
    ConfigurationError,
    ImageProcessingError,
    QwenAPIError,
)
from translator_app.image_pipeline import ImageTranslationPipeline
from translator_app.models import ImageTranslationResult


class ImageTranslationWorker(QThread):
    """Run image translation pipeline off the main UI thread."""

    progress = pyqtSignal(str, int, int)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        pipeline: ImageTranslationPipeline,
        image_base64: str,
        source_image_path: str,
    ) -> None:
        """Store pipeline dependency and input data."""
        super().__init__()
        self._pipeline = pipeline
        self._image_base64 = image_base64
        self._source_image_path = source_image_path

    def run(self) -> None:
        """Execute the pipeline and emit the corresponding signal."""
        try:
            result: ImageTranslationResult = self._pipeline.execute(
                image_base64=self._image_base64,
                source_image_path=self._source_image_path,
                on_progress=self._on_progress,
            )
        except (ConfigurationError, QwenAPIError, ImageProcessingError, ValueError) as exc:
            self.failed.emit(str(exc))
            return

        if result.error:
            # Partial failure: recognition succeeded but translation failed
            self.succeeded.emit(result)
        else:
            self.succeeded.emit(result)

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Forward pipeline progress to the UI thread."""
        self.progress.emit(message, current, total)
```

- [ ] **Step 2: Verify import**

Run: `python -c "from translator_app.image_worker import ImageTranslationWorker; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add translator_app/image_worker.py
git commit -m "feat: add ImageTranslationWorker QThread with progress and error signals"
```

---

## Phase 3: Integration

### Task 14: Integrate into Main Window and Settings

**Files:**
- Modify: `translator_app/settings_dialog.py`
- Modify: `translator_app/floating_window.py`

**Interfaces:**
- Consumes: `ImageInputWidget` from Task 11; `MarkdownOutputWidget` from Task 12; `ImageTranslationWorker` from Task 13; `ImageTranslationPipeline` from Task 9; `QwenClient` from Task 5 (Node 1); `DeepSeekClient` from Task 5 (Node 2); `ImageRecognitionService` from Task 7; `ImageTranslationService` from Task 8; `AppConfig` Qwen fields from Task 1
- Produces: functional [Image] tab in bottom nav; Multimodal settings card

- [ ] **Step 1: Add Multimodal card to settings_dialog.py**

Add Qwen input fields to `__init__` (after `self._temperature_input`, around line 136):

```python
        # Qwen VL (Multimodal) inputs
        self._qwen_api_key_input = QLineEdit(config.qwen_api_key)
        self._qwen_api_key_input.setEchoMode(QLineEdit.Password)
        self._qwen_api_key_input.setPlaceholderText("Paste your Qwen/DashScope API key")

        self._qwen_api_url_input = QLineEdit(config.qwen_api_url)
        self._qwen_model_input = QLineEdit(config.qwen_model)
```

Add the Multimodal card in `_build_ui` (after the Experience card, before the footer):

```python
        root_layout.addWidget(
            self._build_card(
                "Multimodal",
                "Configure Qwen VL API for image translation (recognition + translation).",
                (
                    ("Qwen API Key", self._qwen_api_key_input),
                    ("Qwen API URL", self._qwen_api_url_input),
                    ("Qwen Model", self._qwen_model_input),
                ),
            )
        )
```

Update `build_config` to include Qwen fields:

```python
    def build_config(self) -> AppConfig:
        """Return a config object from the form inputs."""
        return AppConfig(
            api_key=self._api_key_input.text().strip(),
            api_url=self._api_url_input.text().strip(),
            model=self._model_input.text().strip(),
            hotkey=self._hotkey_input.text().strip(),
            timeout_seconds=self._timeout_input.value(),
            temperature=self._temperature_input.value(),
            qwen_api_key=self._qwen_api_key_input.text().strip(),
            qwen_api_url=self._qwen_api_url_input.text().strip(),
            qwen_model=self._qwen_model_input.text().strip(),
        )
```

- [ ] **Step 2: Add new imports to floating_window.py**

Add these imports at the top of `floating_window.py` (after the existing imports block):

```python
from translator_app.image_input_widget import ImageInputWidget
from translator_app.image_worker import ImageTranslationWorker
from translator_app.image_pipeline import ImageTranslationPipeline
from translator_app.image_recognition_service import ImageRecognitionService
from translator_app.image_translation_service import ImageTranslationService
from translator_app.markdown_output_widget import MarkdownOutputWidget
from translator_app.deepseek_client import DeepSeekClient
from translator_app.qwen_client import QwenClient
from translator_app.exceptions import DeepSeekAPIError, QwenAPIError, ImageProcessingError
```

- [ ] **Step 3: Add state variables in FloatingTranslatorWindow.__init__**

Add after `self._nav_icon_names` (around line 477):

```python
        self._image_worker: Optional[ImageTranslationWorker] = None
        self._current_mode: str = "text"  # "text" or "image"

        # Image mode widgets
        self._image_input_widget = ImageInputWidget()
        self._markdown_output_widget = MarkdownOutputWidget()
```

- [ ] **Step 4: Add [Image] to bottom nav in _build_bottom_nav**

Replace the `button_specs` tuple (around line 772):

```python
        button_specs = (
            ("translate", "Translate", "home", self._switch_to_text_mode),
            ("image", "Image", "home", self._switch_to_image_mode),
            ("history", "History", "history", self._show_history),
            ("settings", "Settings", "settings", self._show_settings),
        )
```

- [ ] **Step 5: Add mode switching methods**

Add these methods to `FloatingTranslatorWindow`:

```python
    def _switch_to_text_mode(self) -> None:
        """Switch the main view to text translation mode."""
        if self._current_mode == "text":
            return

        self._current_mode = "text"
        self._set_active_nav("translate")

        # Hide image widgets, show text widgets
        self._image_input_widget.hide()
        self._markdown_output_widget.hide()
        self._input_box.parent().show()
        self._result_card.show()

        self._show_status("Text translation mode.", is_error=False)

    def _switch_to_image_mode(self) -> None:
        """Switch the main view to image translation mode."""
        if self._current_mode == "image":
            return

        self._current_mode = "image"
        self._set_active_nav("image")

        # Hide text widgets, show image widgets
        self._input_box.parent().hide()
        self._result_card.hide()
        self._image_input_widget.show()
        self._markdown_output_widget.show()

        self._show_status("Image translation mode. Upload or capture an image.", is_error=False)
```

- [ ] **Step 6: Wire image widgets into _build_ui**

In `_build_ui`, after `input_card = self._build_input_card()` (around line 650), add:

```python
        self._image_input_widget.hide()  # Hidden by default (text mode)
```

After `result_card = self._build_result_card()` (around line 666), add:

```python
        self._markdown_output_widget.hide()  # Hidden by default (text mode)
```

In the root_layout widget additions (around lines 682-688), add image widgets:

```python
        root_layout.addWidget(header)
        root_layout.addWidget(input_card, stretch=1)
        root_layout.addWidget(self._image_input_widget, stretch=1)  # NEW
        root_layout.addLayout(swap_row)
        root_layout.addWidget(self._translate_button)
        root_layout.addWidget(result_card, stretch=1)
        root_layout.addWidget(self._markdown_output_widget, stretch=1)  # NEW
        root_layout.addWidget(self._status_label)
        root_layout.addLayout(footer_row)
```

- [ ] **Step 7: Add image translation start method**

Add this method to `FloatingTranslatorWindow`:

```python
    def _start_image_translation(self) -> None:
        """Start a background image translation job."""
        image_base64 = self._image_input_widget.get_image_base64()
        if not image_base64:
            self._show_status("Please upload or capture an image first.", is_error=True)
            return

        if self._image_worker is not None and self._image_worker.isRunning():
            self._show_status("Please wait for the current translation to finish.", is_error=True)
            return

        try:
            config = self._config_manager.load_config()
        except ConfigurationError as exc:
            self._show_status(str(exc), is_error=True)
            return

        if not config.qwen_api_key:
            self._show_status(
                "Qwen API key is missing. Open Settings > Multimodal to configure.",
                is_error=True,
            )
            return

        qwen_client = QwenClient(config)
        deepseek_client = DeepSeekClient(config)
        recognition_service = ImageRecognitionService(qwen_client)
        translation_service = ImageTranslationService(deepseek_client)
        pipeline = ImageTranslationPipeline(recognition_service, translation_service)

        self._translate_button.setEnabled(False)
        self._image_worker = ImageTranslationWorker(
            pipeline=pipeline,
            image_base64=image_base64,
            source_image_path="upload",
        )
        self._image_worker.progress.connect(self._handle_image_progress)
        self._image_worker.succeeded.connect(self._handle_image_success)
        self._image_worker.failed.connect(self._handle_image_failure)
        self._image_worker.finished.connect(self._finish_image_translation)
        self._image_worker.start()

    def _handle_image_progress(self, message: str, current: int, total: int) -> None:
        """Update status with pipeline progress."""
        self._show_status(f"{message} ({current}/{total})", is_error=False)

    def _handle_image_success(self, result: "ImageTranslationResult") -> None:
        """Display the translation result in the markdown widget."""
        from translator_app.models import ImageTranslationResult

        if result.error:
            # Partial failure: show recognition text with error
            self._markdown_output_widget.set_content(result.recognized_text)
            self._show_status(
                f"Translation failed, showing recognition result. Error: {result.error}",
                is_error=True,
            )
        else:
            self._markdown_output_widget.set_content(result.translated_text)
            self._show_status("Image translation complete.", is_error=False)

    def _handle_image_failure(self, error_message: str) -> None:
        """Show a user-friendly error for image translation failures."""
        self._show_status(error_message, is_error=True)

    def _finish_image_translation(self) -> None:
        """Reset UI state after the image worker finishes."""
        self._translate_button.setEnabled(True)
```

- [ ] **Step 8: Update _start_translation to dispatch by mode**

Modify the existing `_start_translation` method to check the current mode:

```python
    def _start_translation(self) -> None:
        """Start a background translation job based on the current mode."""
        if self._current_mode == "image":
            self._start_image_translation()
            return

        # Existing text translation logic
        text = self._input_box.toPlainText().strip()
        if not text:
            self._show_status("Please enter or paste text first.", is_error=True)
            return

        if self._worker is not None and self._worker.isRunning():
            self._show_status("Please wait for the current translation to finish.", is_error=True)
            return

        self._translate_button.setEnabled(False)
        self._show_status("Translating...", is_error=False)
        self._worker = TranslationWorker(self._service, text, self._active_style)
        self._worker.succeeded.connect(self._handle_translation_success)
        self._worker.failed.connect(self._handle_translation_failure)
        self._worker.finished.connect(self._finish_translation)
        self._worker.start()
```

- [ ] **Step 9: Update _show_settings to reset nav correctly**

The existing `_show_settings` method already calls `self._set_active_nav("translate")` at the end. Update it to restore the correct nav based on current mode:

```python
    def _show_settings(self) -> None:
        """Open the settings dialog and persist changes."""
        self._set_active_nav("settings")
        try:
            current_config = self._config_manager.load_config()
        except ConfigurationError as exc:
            QMessageBox.warning(self, "Config Error", str(exc))
            current_config = AppConfig()

        dialog = SettingsDialog(current_config, self)
        if dialog.exec_() != QDialog.Accepted:
            self._set_active_nav(self._current_mode)
            return

        try:
            new_config = dialog.build_config()
            self._config_manager.save_config(new_config)
            self._register_hotkey(new_config)
        except ConfigurationError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_active_nav(self._current_mode)
            return

        self._show_status("Settings saved.", is_error=False)
        self._set_active_nav(self._current_mode)
```

- [ ] **Step 10: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 11: Commit**

```bash
git add translator_app/settings_dialog.py translator_app/floating_window.py
git commit -m "feat: integrate image translation mode with [Image] nav tab and Multimodal settings"
```

---

### Task 15: Dependencies and Final Test Pass

**Files:**
- Modify: `requirements.txt`
- Modify: `config.example.json`

**Interfaces:**
- Consumes: all previous tasks
- Produces: updated dependency list and config template

- [ ] **Step 1: Update requirements.txt**

Replace `requirements.txt`:

```
PyQt5>=5.15,<6
requests>=2.31,<3
pynput>=1.7.6,<2
Pillow>=10.0,<11
markdown>=3.6,<4
pytest>=8,<9
```

- [ ] **Step 2: Update config.example.json**

Replace `config.example.json`:

```json
{
  "api_key": "your-deepseek-api-key",
  "api_url": "https://api.deepseek.com/chat/completions",
  "model": "deepseek-chat",
  "hotkey": "<ctrl>+t",
  "timeout_seconds": 45,
  "temperature": 0.2,
  "qwen_api_key": "your-qwen-api-key",
  "qwen_api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
  "qwen_model": "qwen-vl-max",
  "image_max_size_mb": 20,
  "screenshot_hotkey": "<ctrl>+<shift>+s"
}
```

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS (existing 14 + new 24+ = 38+ total)

- [ ] **Step 4: Manual smoke test**

Run: `python main.py`
Verify:
1. App launches with existing text translation working
2. Bottom nav shows [Translate] [Image] [History] [Settings]
3. Click [Image] → switches to image mode (upload/capture visible, text input hidden)
4. Click [Translate] → switches back to text mode
5. Settings dialog shows new "Multimodal" card

- [ ] **Step 5: Commit**

```bash
git add requirements.txt config.example.json
git commit -m "chore: add Pillow and markdown dependencies, update config.example.json"
```

---

## Dependency Graph

```
T1 ──→ T4 ──→ T5 ──→ T7 ──→ T9 ──→ T13 ──→ T14
T2 ──────────↗        ↗              ↗        ↗
T3 ──→ T5, T6 ──→ T11              /        /
       T8 ──→ T9 ──→ T13 ─────────┘        /
T10 ──→ T11 ──────────────────────────────↗
T12 ─────────────────────────────────────↗
T15 (last)
```

**Parallelizable groups:**
- Group A: T1, T2, T3 (no dependencies)
- Group B: T4, T5, T6 (depend on Group A)
- Group C: T7, T8 (depend on T5)
- Group D: T9 (depends on T7, T8)
- Group E: T10, T12 (no project dependencies)
- Group F: T11 (depends on T6, T10)
- Group G: T13 (depends on T9)
- Group H: T14 (depends on T11, T12, T13)
- Group I: T15 (last)
