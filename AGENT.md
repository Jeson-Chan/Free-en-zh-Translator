# AGENT.md — Academic Floating Translator

> 本文档为 AI 编码代理（AGENT）生成的项目全面参考手册，涵盖技术栈、架构设计、模块职责、编码规范和扩展指南。所有信息基于 `2026-07-02` 代码库快照。

---

## 1. 项目概述

**项目名称**：Academic Floating Translator（学术英文翻译器）

**核心用途**：一款基于 Python/PyQt5 的桌面浮动翻译工具，支持文本翻译和图片翻译两种模式。文本翻译通过 OpenAI 兼容格式调用 DeepSeek API；图片翻译采用两节点流水线（Qwen VL 识别 → DeepSeek 翻译）。

**入口文件**：[`main.py`](main.py) — 启动 PyQt 应用，执行初始配置校验，实例化主窗口。

---

## 2. 技术栈

### 2.1 运行时依赖

| 依赖 | 版本范围 | 用途 |
|------|---------|------|
| **PyQt5** | `>=5.15, <6` | 桌面 GUI 框架（浮动窗口、对话框、系统托盘） |
| **requests** | `>=2.31, <3` | HTTP 客户端，向 DeepSeek/Qwen API 发送 POST 请求 |
| **pynput** | `>=1.7.6, <2` | 全局热键监听（非 Qt 原生快捷键） |
| **Pillow** | `>=10.0, <11` | 图片预处理（校验格式、缩放、base64 编码） |
| **markdown** | `>=3.6, <4` | Markdown 渲染为 HTML（图片翻译结果预览） |

### 2.2 开发依赖

| 依赖 | 版本范围 | 用途 |
|------|---------|------|
| **pytest** | `>=8, <9` | 单元测试框架 |

### 2.3 Python 版本

- 要求 **Python 3.12+**

### 2.4 技术选型依据

- **PyQt5**：稳定的跨平台桌面 GUI 框架，支持系统托盘、无边框窗口、QSS 样式
- **requests**：轻量 HTTP 库，无异步需求（翻译操作已通过 QThread 移出主线程）
- **pynput**：唯一支持的跨平台全局热键库，弥补 PyQt 无全局快捷键 API 的短板
- **Pillow**：Python 生态标准图像处理库，支持格式校验、尺寸缩放、PNG 编码
- **markdown**：轻量 Markdown 渲染库，将图片翻译结果转为 HTML 用于 QTextEdit 预览
- **pytest**：Python 生态标准测试框架，简洁断言语法

---

## 3. 架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           UI Layer                                   │
│  floating_window.py          settings_dialog.py                     │
│  image_input_widget.py       markdown_output_widget.py              │
│  TrayIcon / QMenu                                                   │
└──────────────┬──────────────────────────────────────────────────────┘
               │ 调用
┌──────────────▼──────────────────────────────────────────────────────┐
│                         Service Layer                                │
│  translation_service.py      ← 文本翻译：组装配置、检测语言、调用API │
│  image_recognition_service.py ← 图片识别（Node 1）                   │
│  image_translation_service.py ← 图片翻译（Node 2）                   │
│  image_pipeline.py           ← 两阶段流水线编排                      │
└──────┬───────────────┬──────────────┬───────────────────────────────┘
       │               │              │
       ▼               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Client Layer │ │ Client Layer │ │ Persistence Layer│
│ deepseek_    │ │ qwen_client  │ │ config_manager   │
│ client.py    │ │ .py          │ │ history_manager  │
└──────┬───────┘ └──────┬───────┘ └──────────────────┘
       │                │
       ▼                ▼
┌──────────────┐ ┌──────────────┐
│ DeepSeek API │ │  Qwen VL API │ (外部)
│              │ │ (DashScope)  │
└──────────────┘ └──────────────┘
```

### 3.2 数据流

#### 3.2.1 文本翻译

```
用户输入文本
    │
    ▼
FloatingTranslatorWindow._start_translation()
    │ 创建 TranslationWorker(QThread)
    ▼
TranslationWorker.run()
    │ 调用
    ▼
TranslationService.translate_text()
    ├─ ConfigManager.load_config()         → AppConfig
    ├─ detect_language(text)               → "zh" | "en" | "unknown"
    ├─ select_target_language(source)      → 取反
    ├─ DeepSeekClient.translate()          → 发送 HTTP POST
    └─ HistoryManager.add_entry()          → 持久化翻译记录
    │
    ▼
Worker 发射 succeeded / failed 信号
    │
    ▼
FloatingTranslatorWindow 更新 UI
```

#### 3.2.2 图片翻译（两节点流水线）

```
用户加载图片（上传/截图/拖拽）
    │
    ▼
ImageInputWidget._load_from_file() / _load_from_bytes()
    ├─ preprocess_image() / preprocess_image_from_bytes()  → 校验、缩放、PNG 编码
    └─ image_loaded 信号 → base64 字符串
    │
    ▼
FloatingTranslatorWindow._start_image_translation()
    │ 创建 ImageTranslationWorker(QThread)
    ▼
ImageTranslationWorker.run()
    │ 调用
    ▼
ImageTranslationPipeline.execute()
    ├─ Stage 1: ImageRecognitionService.recognize()
    │      ├─ QwenClient.recognize_image()   → 发送多模态请求（image_url + text）
    │      └─ 返回 Markdown 格式的识别文本
    ├─ Stage 2: ImageTranslationService.translate()
    │      ├─ DeepSeekClient.translate_with_prompts()  → 使用 deepseek-v4-pro
    │      └─ 返回翻译后的 Markdown
    └─ 返回 ImageTranslationResult（含两阶段结果和 token 统计）
    │
    ▼
Worker 发射 succeeded / failed 信号
    │
    ▼
FloatingTranslatorWindow 更新 MarkdownOutputWidget
```

### 3.3 API Key 解析优先级

#### DeepSeek API Key

```
config.json 的 api_key 字段（非空）
  → 环境变量 DEEPSEEK_API_KEY
    → 项目根目录 .env 文件中的 DEEPSEEK_API_KEY=...
      → 空（触发 ConfigurationError）
```

#### Qwen VL API Key

```
config.json 的 qwen_api_key 字段（非空）
  → 环境变量 QWEN_API_KEY
    → 项目根目录 .env 文件中的 QWEN_API_KEY=...
      → 空（触发 ConfigurationError）
```

实现位于 [`config_manager.py`](translator_app/config_manager.py) 的 `_apply_env_fallback()` 和 `_apply_qwen_env_fallback()` 方法。

---

## 4. 模块清单与职责边界

### 4.1 `main.py` — 应用入口

- **文件**：[`main.py`](main.py)（72 行）
- **职责**：
  - 初始化日志、QApplication
  - 创建 `ConfigManager`、`HistoryManager`、`TranslationService`
  - 调用 `ensure_configuration()`：无 API Key 时弹出 SettingsDialog
  - 实例化 `FloatingTranslatorWindow` 并进入事件循环
- **与外部交互**：无直接依赖

### 4.2 `translator_app/__init__.py` — 包标记

- **文件**：[`translator_app/__init__.py`](translator_app/__init__.py)（1 行）
- **职责**：标记 `translator_app` 为 Python 包，无实际逻辑

### 4.3 `translator_app/constants.py` — 全局常量

- **文件**：[`translator_app/constants.py`](translator_app/constants.py)
- **职责**：
  - 定义所有硬编码常量：应用名、文件名、默认配置值、系统提示词
- **关键常量**：
  | 常量 | 值 | 说明 |
  |------|-----|------|
  | `APP_NAME` | `"Academic Floating Translator"` | 应用标识 |
  | `CONFIG_FILE_NAME` | `"config.json"` | 配置文件名称 |
  | `HISTORY_FILE_NAME` | `"history.json"` | 历史记录文件名称 |
  | `LOG_FILE_NAME` | `"translator.log"` | 日志文件名称 |
  | `DEFAULT_API_URL` | `"https://api.deepseek.com/chat/completions"` | DeepSeek API 端点 |
  | `DEFAULT_MODEL` | `"deepseek-chat"` | 默认文本翻译模型 |
  | `DEFAULT_TIMEOUT_SECONDS` | `45` | HTTP 请求超时（秒） |
  | `DEFAULT_TEMPERATURE` | `0.2` | 翻译温度（低=更确定性） |
  | `DEFAULT_HOTKEY` | `"<ctrl>+t"` | 默认全局热键 |
  | `MAX_HISTORY_ITEMS` | `10` | 历史记录上限 |
  | `SYSTEM_PROMPT` | 中文提示词 | 文本翻译系统提示词 |
  | `DEFAULT_QWEN_API_URL` | `"https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"` | Qwen VL API 端点 |
  | `DEFAULT_QWEN_MODEL` | `"qwen-vl-max"` | 默认图片识别模型 |
  | `DEFAULT_IMAGE_MAX_SIZE_MB` | `20` | 图片最大尺寸（MB） |
  | `DEFAULT_SCREENSHOT_HOTKEY` | `"<ctrl>+<shift>+s"` | 截图快捷键 |
  | `RECOGNITION_SYSTEM_PROMPT` | 中文提示词 | 图片识别系统提示词（Node 1） |
  | `IMAGE_TRANSLATION_SYSTEM_PROMPT` | 中文提示词 | 图片翻译系统提示词（Node 2） |

### 4.4 `translator_app/exceptions.py` — 异常层次结构

- **文件**：[`translator_app/exceptions.py`](translator_app/exceptions.py)
- **职责**：定义所有应用级异常类型，实现清晰错误分类
- **异常树**：
  ```
  TranslatorAppError (基类)
    ├── ConfigurationError   — 配置缺失/无效
    ├── DeepSeekAPIError     — DeepSeek API 请求失败
    ├── QwenAPIError         — Qwen VL API 请求失败
    ├── HistoryError         — 历史记录加载/保存失败
    ├── HotkeyError          — 全局热键注册失败
    └── ImageProcessingError — 图片预处理失败（格式不支持、文件过大等）
  ```

### 4.5 `translator_app/models.py` — 数据模型

- **文件**：[`translator_app/models.py`](translator_app/models.py)
- **职责**：定义核心 dataclass，使用 `slots=True` 优化内存
- **模型清单**：

  | 模型 | 字段 | 说明 |
  |------|------|------|
  | `AppConfig` | `api_key`, `api_url`, `model`, `hotkey`, `timeout_seconds`, `temperature`, `qwen_api_key`, `qwen_api_url`, `qwen_model`, `image_max_size_mb`, `screenshot_hotkey` | 运行时配置，含 `from_dict()`/`to_dict()` 序列化 |
  | `HistoryEntry` | `timestamp`, `source_text`, `translated_text`, `source_language`, `target_language`, `style` | 单条翻译历史记录 |
  | `TranslationResult` | `source_text`, `translated_text`, `source_language`, `target_language`, `model`, `style` | 文本翻译的完整结果（传回 UI） |
  | `ImageTranslationResult` | `source_image_path`, `recognized_text`, `translated_text`, `source_language`, `target_language`, `recognition_tokens`, `translation_tokens`, `timestamp`, `error` | 图片翻译的完整结果（含两阶段输出） |

### 4.6 `translator_app/logging_config.py` — 日志配置

- **文件**：[`translator_app/logging_config.py`](translator_app/logging_config.py)（24 行）
- **职责**：配置双输出日志（文件 + stderr），格式为 `时间 | 级别 | 模块名 | 消息`
- **日志文件位置**：`{项目根目录}/translator.log`

### 4.7 `translator_app/config_manager.py` — 配置管理

- **文件**：[`translator_app/config_manager.py`](translator_app/config_manager.py)
- **职责**：
  - 从 `config.json` 加载/保存 `AppConfig`
  - 实现三层 API Key 回退机制（config.json → 环境变量 → .env），分别用于 DeepSeek 和 Qwen
  - 静态方法 `_read_dotenv()` 解析 `.env` 文件（K=V 格式，忽略注释和空行）
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `load_config()` | 读 config.json，反序列化为 AppConfig，调用 `_apply_env_fallback` |
  | `save_config(config)` | 序列化 AppConfig 写入 config.json |
  | `_apply_env_fallback(config)` | DeepSeek API Key 三层回退 |
  | `_apply_qwen_env_fallback(config, dotenv_vars)` | Qwen API Key 三层回退，复用已解析的 dotenv_vars |
  | `_read_dotenv(path)` | 静态方法，解析 .env 为 dict |
  | `config_exists()` | 判断 config.json 是否存在 |

### 4.8 `translator_app/language.py` — 语言检测

- **文件**：[`translator_app/language.py`](translator_app/language.py)（34 行）
- **职责**：纯函数模块，无状态、无副作用
- **检测策略**：**CJK-first** — 只要文本含任一 CJK 统一汉字（`\u4e00-\u9fff`），即返回 `"zh"`。这是有意设计：学术场景下中文文档常夹杂英文术语（如 "Transformer 架构"），应视为中文源文。
- **函数清单**：
  | 函数 | 输入 | 输出 | 逻辑 |
  |------|------|------|------|
  | `detect_language(text)` | 文本 | `"zh"` / `"en"` / `"unknown"` | CJK 字符优先，其次拉丁字母，否则 unknown |
  | `select_target_language(source)` | 语言代码 | 取反的语言代码 | `"zh"`→`"en"`，其他→`"zh"` |
  | `describe_language(code)` | 语言代码 | 可读标签 | `"zh"`→`"Chinese"`, `"en"`→`"English"` |

### 4.9 `translator_app/translation_style.py` — 翻译风格

- **文件**：[`translator_app/translation_style.py`](translator_app/translation_style.py)（54 行）
- **职责**：定义 4 种翻译风格及对应的英文提示词指令
- **可用风格**（`TranslationStyle` 类型）：
  | 风格 | 显示名 | 指令要点 |
  |------|--------|---------|
  | `academic` | Academic | 学术语气，保留术语、正式措辞 |
  | `casual` | Casual | 自然对话语气，日常语言 |
  | `business` | Business | 专业商务语气，简洁清晰 |
  | `literary` | Literary | 文学语气，保留意象、节奏、风格细节 |
- **默认风格**：`academic`
- **核心函数**：
  | 函数 | 说明 |
  |------|------|
  | `normalize_translation_style(style)` | 标准化输入风格字符串，不支持时回退到默认 |
  | `get_style_instruction(style)` | 返回对应风格的英文 prompt 指令 |
  | `get_style_display_name(style)` | 返回 Title Case 显示名 |

### 4.10 `translator_app/deepseek_client.py` — DeepSeek API 客户端

- **文件**：[`translator_app/deepseek_client.py`](translator_app/deepseek_client.py)
- **职责**：
  - 构造 OpenAI 兼容的 chat completions 请求
  - 验证 API Key（占位符检测、空白字符检测）
  - 解析 API 响应，提取翻译文本
  - 将 HTTP 错误转换为用户友好的 `DeepSeekAPIError`
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `translate(text, source, target, style)` | 发送文本翻译请求，返回翻译文本 |
  | `translate_with_prompts(system_prompt, user_prompt, model)` | 使用自定义 prompt 翻译（图片翻译 Node 2 使用），默认使用 `deepseek-v4-pro` |
  | `_call_api(payload, headers)` | 执行 API 请求并提取内容（共享方法） |
  | `_build_headers()` | 构造 Authorization Bearer 和 Content-Type 头 |
  | `_validate_api_key(raw)` | 静态方法，校验 API Key 有效性 |
  | `_build_user_message(text, source, target, style)` | 构造发给模型的 user message（含语言方向、风格指令） |
  | `_build_http_error(exc)` | 将 requests.HTTPError 转为 DeepSeekAPIError（401 特殊处理） |
  | `_extract_error_details(response)` | 从 HTTP 响应体中提取错误消息 |
  | `_extract_content(payload)` | 从 API 响应 JSON 中提取 `choices[0].message.content` |

### 4.11 `translator_app/translation_service.py` — 翻译服务编排

- **文件**：[`translator_app/translation_service.py`](translator_app/translation_service.py)（66 行）
- **职责**：业务编排层，协调配置加载、语言检测、API 调用、历史持久化
- **唯一公开方法**：
  | 方法 | 说明 |
  |------|------|
  | `translate_text(text, style)` | 输入文本和风格 → 加载配置 → 检测语言 → 调用 API → 返回 TranslationResult → 自动持久化 HistoryEntry |

### 4.12 `translator_app/worker.py` — 后台线程

- **文件**：[`translator_app/worker.py`](translator_app/worker.py)（45 行）
- **职责**：将翻译操作移到 QThread，避免阻塞 UI 主线程
- **信号**：
  | 信号 | 参数 | 触发时机 |
  |------|------|---------|
  | `succeeded` | `TranslationResult` | 翻译成功 |
  | `failed` | `str`（错误消息） | 翻译失败（捕获 5 种异常类型） |

### 4.13 `translator_app/history_manager.py` — 历史记录持久化

- **文件**：[`translator_app/history_manager.py`](translator_app/history_manager.py)（76 行）
- **职责**：
  - 以 JSON 数组格式持久化翻译历史到 `history.json`
  - 维护最近 N 条记录（`MAX_HISTORY_ITEMS = 10`，新记录插入头部）
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `load_entries()` | 从 history.json 读取并反序列化为 `list[HistoryEntry]` |
  | `add_entry(entry)` | 在列表头部插入新记录，裁剪到 MAX_HISTORY_ITEMS，写回文件 |
  | `clear_entries()` | 清空历史文件（写 `[]`） |

### 4.14 `translator_app/hotkey_manager.py` — 全局热键

- **文件**：[`translator_app/hotkey_manager.py`](translator_app/hotkey_manager.py)（43 行）
- **职责**：通过 pynput 注册全局热键，按键时发射 Qt 信号
- **设计**：继承 `QObject`，使用 `pyqtSignal` 桥接 pynput 回调和 Qt 事件循环
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `start()` | 启动全局热键监听器 |
  | `stop()` | 停止监听器 |
  | `_on_activated()` | 热键触发时发射 `activated` 信号 |

### 4.15 `translator_app/settings_dialog.py` — 设置对话框

- **文件**：[`translator_app/settings_dialog.py`](translator_app/settings_dialog.py)
- **职责**：
  - 提供 API Key、API URL、Model、Hotkey、Timeout、Temperature 的编辑界面
  - 分三区：Connectivity（连接配置）、Experience（体验设置）、Multimodal（Qwen VL 配置）
  - 输入验证：保存前检查必填字段非空
  - 淡入动画（`showEvent` 重写）
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `build_config()` | 从表单控件提取值构建 AppConfig（含 Qwen 字段） |
  | `_validate_before_accept()` | 校验必填字段，通过后调用 `accept()` |
  | `_build_card(title, hint, fields)` | 构建分组卡片 |

### 4.16 `translator_app/floating_window.py` — 主浮动窗口

- **文件**：[`translator_app/floating_window.py`](translator_app/floating_window.py)
- **职责**：核心 UI 模块，包含以下子组件：
  - **`create_line_icon()`**：用 QPainter 绘制自定义 SVG 风格图标（paste/copy/clear/swap/translate/history/settings/home/image，24x24）
  - **`DraggableHeaderFrame`**：无边框窗口拖拽移动
  - **`ClickToCopyTextEdit`**：点击即复制翻译结果
  - **`_make_copy_button(text)`**：创建 Copy 按钮（点击变 "Copied!" 1.5 秒后恢复）
  - **`HistoryCard`**：单条历史记录的卡片组件（含 SOURCE/TRANSLATION 各一个 Copy 按钮）
  - **`HistoryDialog`**：历史记录弹窗（ScrollArea + 卡片列表 + Clear History 按钮 + 淡入动画）
  - **`FloatingTranslatorWindow`**：主窗口类，支持文本/图片两种模式切换
- **系统托盘**：`_create_tray_icon()` 创建系统托盘，含 Show/Hide、History、Settings、Quit 菜单项
- **布局结构**：
  ```
  ┌───────────────────────────────────┐
  │  [titleLabel] "translator"        │  ← DraggableHeaderFrame
  │  [subtitleLabel]                  │
  │  [Academic] [Casual] [Business] [Literary] │ ← 风格选择
  ├───────────────────────────────────┤
  │  [Text Mode]                      │
  │  SOURCE TEXT        [Clear] [Paste]│  ← _build_input_card
  │  ┌─────────────────────────────┐  │
  │  │  QTextEdit (可编辑)          │  │
  │  └─────────────────────────────┘  │
  │           [Swap]                   │
  │         [ Translate ]              │  ← primaryButton
  │  TRANSLATED TEXT         [Copy]   │  ← _build_result_card
  │  ┌─────────────────────────────┐  │
  │  │  ClickToCopyTextEdit (只读) │  │
  │  └─────────────────────────────┘  │
  ├───────────────────────────────────┤
  │  [Image Mode]                     │
  │  SOURCE IMAGE     [Upload][Capture]│ ← ImageInputWidget
  │  ┌─────────────────────────────┐  │
  │  │  图片预览                    │  │
  │  └─────────────────────────────┘  │
  │      [ Translate Image ]          │
  │  TRANSLATED (MARKDOWN)            │ ← MarkdownOutputWidget
  │  ┌─────────────────────────────┐  │
  │  │  Markdown 预览              │  │
  │  └─────────────────────────────┘  │
  ├───────────────────────────────────┤
  │   [statusLabel]                    │  ← statusToast
  ├───────────────────────────────────┤
  │  [Translate][Image][History][Settings] [⤢] │ ← bottom nav + size grip
  └───────────────────────────────────┘
  ```
- **模式切换**：`_set_mode(mode)` 控制 text/image 两组 widget 的显隐
- **动画系统**：
  - 结果卡片淡入（`_animate_result_card`）
  - 状态提示淡入（`_show_status`）
  - 窗口显隐动画（位置 + 透明度同时变化，`_start_visibility_animation`）
  - 设置/历史对话框淡入（`showEvent` 重写）

### 4.17 `translator_app/qwen_client.py` — Qwen VL API 客户端

- **文件**：[`translator_app/qwen_client.py`](translator_app/qwen_client.py)
- **职责**：
  - 构造多模态（image_url + text）请求发送给 Qwen VL API
  - 验证 Qwen API Key
  - 解析 API 响应，提取识别文本
  - 将 HTTP 错误转换为用户友好的 `QwenAPIError`
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `recognize_image(image_base64, system_prompt, user_prompt)` | 发送图片识别请求，返回 Markdown 格式文本 |
  | `_send_request(payload, api_key)` | 执行 HTTP POST 并提取内容 |
  | `_validate_api_key(raw)` | 静态方法，校验 Qwen API Key 有效性 |
  | `_build_http_error(exc)` | 将 requests.HTTPError 转为 QwenAPIError |
  | `_extract_content(payload)` | 从 API 响应 JSON 中提取 `choices[0].message.content` |

### 4.18 `translator_app/image_preprocessor.py` — 图片预处理

- **文件**：[`translator_app/image_preprocessor.py`](translator_app/image_preprocessor.py)
- **职责**：
  - 校验图片格式（png/jpg/jpeg/bmp/webp）
  - 校验文件大小（默认 20MB 上限，防解压炸弹）
  - 缩放超大分辨率（> 4096px）
  - 转换为 RGB 模式并输出 PNG 格式的 base64 字符串
- **关键常量**：
  | 常量 | 值 | 说明 |
  |------|-----|------|
  | `SUPPORTED_FORMATS` | `frozenset({"png", "jpg", "jpeg", "bmp", "webp"})` | 支持的图片格式 |
  | `MAX_RESOLUTION` | `4096` | 最大分辨率（像素） |
  | `_MAX_FILE_SIZE_MB` | `20` | 默认文件大小上限 |
- **关键函数**：
  | 函数 | 说明 |
  |------|------|
  | `preprocess_image(file_path, max_size_mb)` | 从文件路径加载并预处理 |
  | `preprocess_image_from_bytes(image_bytes, extension, max_size_bytes)` | 从字节数据预处理 |

### 4.19 `translator_app/image_recognition_service.py` — 图片识别服务（Node 1）

- **文件**：[`translator_app/image_recognition_service.py`](translator_app/image_recognition_service.py)
- **职责**：
  - 封装 `QwenClient.recognize_image()` 调用
  - 使用 `RECOGNITION_SYSTEM_PROMPT` 和固定 user prompt
  - 返回 Markdown 格式的识别文本
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `recognize(image_base64)` | 调用 Qwen VL API 识别图片内容，返回 Markdown 文本 |

### 4.20 `translator_app/image_translation_service.py` — 图片翻译服务（Node 2）

- **文件**：[`translator_app/image_translation_service.py`](translator_app/image_translation_service.py)
- **职责**：
  - 封装 `DeepSeekClient.translate_with_prompts()` 调用
  - 使用 `IMAGE_TRANSLATION_SYSTEM_PROMPT` 和 `deepseek-v4-pro` 模型
  - 将识别后的 Markdown 文本翻译为目标语言
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `translate(recognized_text)` | 调用 DeepSeek API 翻译 Markdown 文本 |

### 4.21 `translator_app/image_pipeline.py` — 图片翻译流水线

- **文件**：[`translator_app/image_pipeline.py`](translator_app/image_pipeline.py)
- **职责**：
  - 编排两阶段流水线：识别（Node 1）→ 翻译（Node 2）
  - 处理各阶段异常，返回包含错误信息的 `ImageTranslationResult`
  - 支持进度回调
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `execute(image_base64, source_image_path, on_progress)` | 执行完整流水线，返回 ImageTranslationResult |
  | `_execute_stages(...)` | 内部方法，实际执行两阶段逻辑 |

### 4.22 `translator_app/image_worker.py` — 图片翻译后台线程

- **文件**：[`translator_app/image_worker.py`](translator_app/image_worker.py)
- **职责**：将图片翻译操作移到 QThread，避免阻塞 UI 主线程
- **信号**：
  | 信号 | 参数 | 触发时机 |
  |------|------|---------|
  | `progress` | `str, int, int`（消息, 当前阶段, 总阶段） | 流水线进度更新 |
  | `succeeded` | `ImageTranslationResult` | 翻译成功（含部分失败情况） |
  | `failed` | `str`（错误消息） | 翻译失败 |

### 4.23 `translator_app/screenshot_tool.py` — 截图工具

- **文件**：[`translator_app/screenshot_tool.py`](translator_app/screenshot_tool.py)
- **职责**：
  - 全屏透明覆盖层（`ScreenshotOverlay`）
  - 区域选择（鼠标拖拽）
  - 捕获选定区域为 PNG 字节
- **关键类/函数**：
  | 类/函数 | 说明 |
  |------|------|
  | `ScreenshotOverlay(QWidget)` | 全屏透明覆盖层，支持区域选择和截图 |
  | `ScreenshotTool` | 高级 API，管理覆盖层生命周期和事件循环 |
  | `normalize_selection_rect(x1, y1, x2, y2)` | 标准化选择矩形坐标 |
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `ScreenshotTool.capture()` | 显示覆盖层，阻塞等待用户选择，返回 PNG 字节或 None |
  | `ScreenshotOverlay.paintEvent(event)` | 绘制半透明遮罩和选择框 |
  | `ScreenshotOverlay.closeEvent(event)` | 外部关闭时发射 cancelled 信号 |

### 4.24 `translator_app/image_input_widget.py` — 图片输入控件

- **文件**：[`translator_app/image_input_widget.py`](translator_app/image_input_widget.py)
- **职责**：
  - 提供图片加载入口：文件上传、截图、拖拽
  - 显示图片预览和文件信息
  - 发射 `image_loaded` 信号（base64 字符串）
- **信号**：
  | 信号 | 参数 | 触发时机 |
  |------|------|---------|
  | `image_loaded` | `str`（base64） | 图片加载成功 |
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `get_image_base64()` | 返回当前加载图片的 base64 |
  | `clear_image()` | 重置控件到空状态 |
  | `_on_upload_clicked()` | 打开文件对话框 |
  | `_on_capture_clicked()` | 最小化主窗口并截图 |
  | `_load_from_file(file_path)` | 从文件加载并预处理 |
  | `_load_from_bytes(data, extension, source)` | 从字节加载并预处理 |
  | `dragEnterEvent(event)` / `dropEvent(event)` | 拖拽支持 |

### 4.25 `translator_app/markdown_output_widget.py` — Markdown 输出控件

- **文件**：[`translator_app/markdown_output_widget.py`](translator_app/markdown_output_widget.py)
- **职责**：
  - 显示 Markdown 翻译结果
  - 支持源文本/预览两种模式切换
  - 提供复制按钮
  - 使用 `markdown` 库渲染 HTML
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `set_content(markdown_text)` | 设置内容并切换到源文本模式 |
  | `get_content()` | 返回当前 Markdown 源文本 |
  | `clear_content()` | 重置控件到空状态 |
  | `_show_source()` | 切换到纯文本源视图 |
  | `_show_preview()` | 渲染 Markdown 为 HTML 并显示 |
  | `_create_monospace_font()` | 静态方法，创建等宽字体 |

---

## 5. 编码规范

### 5.1 Python 代码风格

| 规范项 | 约定 |
|--------|------|
| **编码声明** | 每个 `.py` 文件首行 `"""模块文档字符串"""`，第二行 `from __future__ import annotations` |
| **类型注解** | 所有函数参数和返回值有类型注解（含 `-> None`）。Nullable 类型混用 `Optional[X]` 和 `X | None`（逐步迁移到后者） |
| **导入顺序** | `from __future__` → 标准库 → 第三方库（PyQt5, requests, pynput）→ 项目内部（`translator_app.*`），每组间空一行 |
| **命名规则** | 类名 `PascalCase`，函数/方法/变量 `snake_case`，私有成员 `_leading_underscore`，常量 `UPPER_CASE`，模块级私有 `_leading_underscore` |
| **文档字符串** | 所有 public class、method、function 有 docstring（单行或简短描述），位于 `def`/`class` 下一行 |
| **类型注释风格** | 函数注解写在签名中（非注释形式），变量类型用 `variable: Type = value` |
| **Dataclass** | 使用 `@dataclass(slots=True)`，含 `from_dict()` 类方法和 `to_dict()` 实例方法 |

### 5.2 错误处理规范

- 所有可恢复错误抛出应用自定义异常（`TranslatorAppError` 子类）
- API 层（`deepseek_client.py`）负责将底层异常（`requests.*Error`）转换为 `DeepSeekAPIError`
- UI 层（`floating_window.py`）通过 `TranslationWorker.failed` 信号接收错误消息字符串并显示给用户
- 文件 I/O 操作统一捕获 `OSError` / `json.JSONDecodeError` 并转为对应自定义异常
- 敏感路径（API Key）在发送请求前通过 `_validate_api_key()` 做最终校验

### 5.3 文件编码

- 所有 Python 源文件使用 **UTF-8** 编码
- 读取 JSON 配置文件使用 **`utf-8-sig`**（兼容 BOM 标记）
- `.env` 文件读取使用 **`utf-8-sig`**

### 5.4 目录结构约定

```
Free-en-zh-Translator/
├── main.py                    # 应用入口
├── requirements.txt           # 依赖声明
├── config.example.json        # 配置模板（可提交 Git）
├── .env.example               # 环境变量模板（可提交 Git）
├── config.json                # 运行时配置（Git 忽略）
├── .env                       # API Key 文件（Git 忽略）
├── history.json               # 翻译历史（Git 忽略）
├── translator.log             # 运行日志（Git 忽略）
├── .gitignore                 # 敏感文件排除
├── AGENT.md                   # AI 代理参考手册
├── docs/                      # 文档目录
│   └── superpowers/plans/     # 实现计划
├── translator_app/            # 主包（24 个模块）
│   ├── __init__.py
│   ├── models.py              # 数据模型（AppConfig, HistoryEntry, TranslationResult, ImageTranslationResult）
│   ├── constants.py           # 全局常量
│   ├── exceptions.py          # 自定义异常
│   ├── config_manager.py      # 配置管理
│   ├── logging_config.py      # 日志配置
│   ├── language.py            # 语言检测
│   ├── translation_style.py   # 翻译风格
│   ├── deepseek_client.py     # DeepSeek API 客户端
│   ├── qwen_client.py         # Qwen VL API 客户端（图片识别）
│   ├── translation_service.py # 文本翻译服务
│   ├── image_preprocessor.py  # 图片预处理
│   ├── image_recognition_service.py  # 图片识别服务（Node 1）
│   ├── image_translation_service.py  # 图片翻译服务（Node 2）
│   ├── image_pipeline.py      # 图片翻译两阶段流水线
│   ├── worker.py              # 文本翻译后台线程
│   ├── image_worker.py        # 图片翻译后台线程
│   ├── screenshot_tool.py     # 截图工具
│   ├── image_input_widget.py  # 图片输入控件
│   ├── markdown_output_widget.py     # Markdown 输出控件
│   ├── history_manager.py     # 历史记录持久化
│   ├── hotkey_manager.py      # 全局热键
│   ├── settings_dialog.py     # 设置对话框
│   └── floating_window.py     # 主浮动窗口
├── tests/                     # pytest 测试集（45 个测试）
│   ├── test_language.py
│   ├── test_deepseek_client.py
│   ├── test_translation_style.py
│   ├── test_models.py
│   ├── test_config_manager_qwen.py
│   ├── test_qwen_client.py
│   ├── test_image_preprocessor.py
│   ├── test_image_pipeline.py
│   └── test_screenshot_tool.py
└── project/                   # 实验性 React 前端（非主应用）
    └── ...
```

### 5.5 Git 忽略规则

详见 [`.gitignore`](.gitignore)：

- **敏感配置**：`config.json`、`.env`
- **生成文件**：`history.json`、`translator.log`、`*.log`
- **Python 产物**：`__pycache__/`、`*.py[cod]`、`*.egg-info/`、`dist/`、`build/`、`.pytest_cache/`
- **虚拟环境**：`venv/`、`.venv/`、`env/`
- **IDE**：`.vscode/`、`.idea/`、`.trae/`
- **OS**：`.DS_Store`、`Thumbs.db`

### 5.6 提交消息规范

- 推荐前缀：`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`
- 简短描述变更意图（Why > What）
- 中英文均可

---

## 6. 测试体系

### 6.1 测试文件与覆盖范围

| 测试文件 | 测试数 | 覆盖模块 |
|---------|--------|---------|
| [`tests/test_language.py`](tests/test_language.py) | 5 | `language.py`：语言检测、目标语言选择、标签描述 |
| [`tests/test_deepseek_client.py`](tests/test_deepseek_client.py) | 5 | `deepseek_client.py`：请求头构建、API Key 校验、HTTP 错误转换、用户消息构建 |
| [`tests/test_translation_style.py`](tests/test_translation_style.py) | 4 | `translation_style.py`：风格标准化、回退逻辑、指令获取、显示名 |
| [`tests/test_models.py`](tests/test_models.py) | 6 | `models.py`：AppConfig Qwen 字段、ImageTranslationResult |
| [`tests/test_config_manager_qwen.py`](tests/test_config_manager_qwen.py) | 5 | `config_manager.py`：Qwen API Key 三层回退、保存 Qwen 字段 |
| [`tests/test_qwen_client.py`](tests/test_qwen_client.py) | 5 | `qwen_client.py`：多模态 payload 构建、模型/温度、API Key 校验、HTTP 401、空响应 |
| [`tests/test_image_preprocessor.py`](tests/test_image_preprocessor.py) | 8 | `image_preprocessor.py`：格式支持、分辨率、base64、缩放、不支持格式、文件不存在、文件过大 |
| [`tests/test_image_pipeline.py`](tests/test_image_pipeline.py) | 4 | `image_pipeline.py`：两阶段执行、进度回调、识别失败、翻译失败保留识别 |
| [`tests/test_screenshot_tool.py`](tests/test_screenshot_tool.py) | 3 | `screenshot_tool.py`：选择矩形标准化 |

### 6.2 运行测试

```bash
python -m pytest tests/ -v
```

### 6.3 测试命名约定

- 文件名：`test_<模块名>.py`
- 函数名：`test_<被测函数>_<场景描述>()`
- 每个测试函数有独立 docstring

---

## 7. 关键设计决策

### 7.1 CJK-first 语言检测

`detect_language()` 采用 **CJK 字符优先**策略：只要文本含任一中文字符即返回 `"zh"`。这是因为在学术翻译场景中，中文文档频繁夹带英文术语（如 "本文提出一种基于 Transformer 的模型"），应整体视为中文源文。该策略对"英文为主 + 少量中文"的边界输入不友好，但在目标用户场景中极少触发。

### 7.2 API Key 三层安全机制

为防止 API Key 泄露到 Git 仓库：
1. `config.json` 由 `.gitignore` 排除，提供 `config.example.json` 作为模板
2. 支持环境变量（`DEEPSEEK_API_KEY` / `QWEN_API_KEY`）（最高灵活性，CI/CD 友好）
3. 支持 `.env` 文件（开发者友好，`.gitignore` 已排除）

### 7.3 QThread 异步翻译

翻译 API 调用不阻塞 UI 主线程，通过 `TranslationWorker` / `ImageTranslationWorker`（QThread）实现。Worker 通过 pyqtSignal 将结果传回 UI 层，异常也通过信号传递。

### 7.4 历史记录上限

`MAX_HISTORY_ITEMS = 10`，新记录插入 `history.json` 数组头部，超出上限的旧记录被裁剪丢弃。

### 7.5 图片翻译两节点流水线

图片翻译采用 **两节点串行流水线** 架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                    ImageTranslationPipeline                      │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────────────┐   │
│  │   Node 1: 识别       │    │   Node 2: 翻译                │   │
│  │                      │    │                              │   │
│  │  Qwen VL API         │───▶│  DeepSeek API                │   │
│  │  (qwen-vl-max)       │    │  (deepseek-v4-pro)           │   │
│  │                      │    │                              │   │
│  │  输入: 图片 base64   │    │  输入: Markdown 文本         │   │
│  │  输出: Markdown 文本 │    │  输出: 翻译后的 Markdown     │   │
│  └──────────────────────┘    └──────────────────────────────┘   │
│                                                                  │
│  返回: ImageTranslationResult（含两阶段输出和 token 统计）      │
└─────────────────────────────────────────────────────────────────┘
```

**设计理由**：
- **职责分离**：Node 1 专注图像理解（多模态），Node 2 专注文本翻译（高质量 LLM）
- **模型选择**：Qwen VL 在图像识别上表现优异；DeepSeek v4-pro 在学术翻译上质量更高
- **错误隔离**：识别失败时返回空结果；翻译失败时保留识别文本（部分成功）
- **扩展性**：可独立替换任一节点（如换用 GPT-4V 做识别）

### 7.6 图片预处理策略

`image_preprocessor.py` 采用以下预处理策略：

1. **格式校验**：仅支持 png/jpg/jpeg/bmp/webp
2. **大小校验**：默认 20MB 上限（防解压炸弹攻击）
3. **分辨率缩放**：超过 4096px 按比例缩小
4. **统一输出**：始终输出 PNG 格式（确保 MIME 类型一致性）

**设计理由**：
- PNG 格式无损压缩，保留图像细节
- 统一 MIME 类型简化 Qwen VL API 调用（硬编码 `data:image/png;base64`）
- 解压炸弹防护防止恶意大图消耗内存

### 7.7 截图工具设计

`screenshot_tool.py` 使用 **阻塞式事件循环** 设计：

1. `ScreenshotTool.capture()` 创建全屏透明覆盖层
2. 用户在覆盖层上拖拽选择区域
3. `capture()` 进入 `while not completed` 循环，调用 `app.processEvents()` 处理事件
4. 用户释放鼠标或按 Escape 时，信号设置 `completed = True`，循环退出
5. 返回 PNG 字节或 None

**关键设计**：
- `WA_TranslucentBackground = True` 确保覆盖层半透明
- `closeEvent` 重写确保外部关闭时发射 `cancelled` 信号
- `deleteLater()` 清理覆盖层防止内存泄漏

---

## 8. 扩展指南

### 8.1 添加新的翻译风格

1. 在 [`translation_style.py`](translator_app/translation_style.py) 的 `TranslationStyle` Literal 类型中添加新风格名
2. 在 `AVAILABLE_TRANSLATION_STYLES` 元组中追加
3. 在 `_STYLE_INSTRUCTIONS` 字典中添加对应的英文提示词
4. UI 会自动渲染新的风格按钮（`floating_window.py` 动态遍历 `AVAILABLE_TRANSLATION_STYLES`）

### 8.2 切换 LLM 后端

1. 修改 [`constants.py`](translator_app/constants.py) 中的 `DEFAULT_API_URL` 和 `DEFAULT_MODEL`
2. 若新 API 不是 OpenAI 兼容格式，需修改 [`deepseek_client.py`](translator_app/deepseek_client.py) 的 `translate()` 方法中的请求体和 `_extract_content()` 响应解析逻辑

### 8.3 添加新的 UI 功能

- 向 `FloatingTranslatorWindow` 添加新方法，通过信号/槽连接到现有按钮或新按钮
- 样式通过 QSS 字符串集中管理（`_configure_window()` 和组件 `setStyleSheet`）
- 图标通过 `create_line_icon()` 绘制，新图标名称需在函数内添加分支

### 8.4 添加新的持久化数据

1. 在 [`models.py`](translator_app/models.py) 中添加 dataclass（含 `from_dict`/`to_dict`）
2. 创建对应的 Manager 类（参考 `ConfigManager` / `HistoryManager` 模式）
3. 在 `.gitignore` 中排除生成的数据文件

### 8.5 切换图片识别模型（Node 1）

1. 修改 [`constants.py`](translator_app/constants.py) 中的 `DEFAULT_QWEN_API_URL` 和 `DEFAULT_QWEN_MODEL`
2. 若新 API 不是 OpenAI 兼容格式，需修改 [`qwen_client.py`](translator_app/qwen_client.py) 的 `recognize_image()` 方法中的请求体
3. 若新 API 使用不同的多模态格式（如直接上传图片而非 base64），需修改 payload 构造逻辑

### 8.6 切换图片翻译模型（Node 2）

1. 修改 [`image_translation_service.py`](translator_app/image_translation_service.py) 中传递给 `translate_with_prompts()` 的 `model` 参数
2. 当前默认使用 `deepseek-v4-pro`，可改为其他模型

### 8.7 添加新的图片输入方式

1. 在 [`image_input_widget.py`](translator_app/image_input_widget.py) 中添加新的按钮或事件处理
2. 调用 `_load_from_file()` 或 `_load_from_bytes()` 加载图片
3. 发射 `image_loaded` 信号通知主窗口

### 8.8 自定义图片预处理

1. 修改 [`image_preprocessor.py`](translator_app/image_preprocessor.py) 中的常量或逻辑
2. 如需支持新格式，添加到 `SUPPORTED_FORMATS` 集合
3. 如需调整输出格式，修改 `image.save()` 调用的 `format` 参数（注意同步更新 MIME 类型）

### 8.9 添加图片翻译历史记录

当前图片翻译结果不持久化到历史。如需添加：

1. 在 [`models.py`](translator_app/models.py) 中扩展 `HistoryEntry` 或创建新的 `ImageHistoryEntry`
2. 在 [`history_manager.py`](translator_app/history_manager.py) 中添加图片历史的保存/加载逻辑
3. 在 [`image_pipeline.py`](translator_app/image_pipeline.py) 或 `floating_window.py` 中调用保存方法

---

## 9. 注意事项

### 9.1 安全与配置

- **不要将 `config.json` 或 `.env` 提交到 Git**（已在 `.gitignore` 中排除）
- **不要修改 `config.example.json`** 中的 `api_key` 为真实密钥
- **API Key 敏感操作**：`SettingsDialog` 的 `_api_key_input` 和 `_qwen_api_key_input` 使用 `Password` echo mode 掩码显示

### 9.2 环境与依赖

- **pynput 需要系统权限**：在 macOS 上需授予辅助功能权限，Linux 上可能需要 root 或配置 X11
- **Pillow 需要系统图像库**：通常预装在大多数系统上，如遇问题可安装 `libjpeg-dev`、`zlib1g-dev` 等
- **markdown 库可选**：如未安装，`MarkdownOutputWidget` 的预览功能会显示提示信息，不影响源文本显示

### 9.3 代码风格

- **所有 QSS 样式字符串**使用 f-string 和 `TEXT_FONT_STACK` 常量避免字体栈重复
- **所有 dataclass** 使用 `@dataclass(slots=True)` 优化内存
- **所有 public 方法**应有 docstring

### 9.4 图片翻译特殊注意事项

- **图片格式**：预处理器始终输出 PNG 格式，Qwen VL API 请求硬编码 `data:image/png;base64` MIME 类型
- **解压炸弹防护**：`preprocess_image_from_bytes()` 有 `max_size_bytes` 参数限制（默认 20MB），防止恶意大图消耗内存
- **截图工具**：使用阻塞式事件循环，`ScreenshotOverlay` 的 `closeEvent` 确保外部关闭时发射 `cancelled` 信号
- **流水线异常处理**：`ImageTranslationPipeline.execute()` 捕获所有异常并返回 `ImageTranslationResult`（含 error 字段），不会抛出异常到 UI 线程

### 9.5 其他

- **`project/` 目录**是实验性 React/Vite 前端原型，非当前主应用代码，维护主应用时忽略此目录
- **运行测试**：使用 `python -m pytest tests/ -v`（注意是 `python -m pytest` 而非裸 `pytest`）
