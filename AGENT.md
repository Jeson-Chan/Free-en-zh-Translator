# AGENT.md — Academic Floating Translator

> 本文档为 AI 编码代理（AGENT）生成的项目全面参考手册，涵盖技术栈、架构设计、模块职责、编码规范和扩展指南。所有信息基于 `2026-06-03` 代码库快照。

---

## 1. 项目概述

**项目名称**：Academic Floating Translator（学术英文翻译器）

**核心用途**：一款基于 Python/PyQt5 的桌面浮动翻译工具，专注中英文学术或专业文本翻译，通过 OpenAI 兼容格式调用 DeepSeek API。

**入口文件**：[`main.py`](main.py) — 启动 PyQt 应用，执行初始配置校验，实例化主窗口。

---

## 2. 技术栈

### 2.1 运行时依赖

| 依赖 | 版本范围 | 用途 |
|------|---------|------|
| **PyQt5** | `>=5.15, <6` | 桌面 GUI 框架（浮动窗口、对话框、系统托盘） |
| **requests** | `>=2.31, <3` | HTTP 客户端，向 DeepSeek API 发送 POST 请求 |
| **pynput** | `>=1.7.6, <2` | 全局热键监听（非 Qt 原生快捷键） |

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
- **pytest**：Python 生态标准测试框架，简洁断言语法

---

## 3. 架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────┐
│              UI Layer               │
│  floating_window.py                 │
│  settings_dialog.py                 │
│  TraeIcon / QMenu                   │
└──────────────┬──────────────────────┘
               │ 调用
┌──────────────▼──────────────────────┐
│          Service Layer              │
│  translation_service.py             │  ← 编排层：组装配置、检测语言、创建客户端、持久化历史
└──────┬───────────────┬──────────────┘
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────────┐
│ Client Layer │ │ Persistence Layer│
│ deepseek_    │ │ config_manager   │
│ client.py    │ │ history_manager  │
└──────┬───────┘ └──────────────────┘
       │
       ▼
┌──────────────┐
│ DeepSeek API │ (外部)
└──────────────┘
```

### 3.2 数据流（一次完整翻译）

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
    ├─ ConfigManager.save_config()         → （不在此处）
    └─ HistoryManager.add_entry()          → 持久化翻译记录
    │
    ▼
Worker 发射 succeeded / failed 信号
    │
    ▼
FloatingTranslatorWindow 更新 UI
```

### 3.3 API Key 解析优先级

```
config.json 的 api_key 字段（非空）
  → 环境变量 DEEPSEEK_API_KEY
    → 项目根目录 .env 文件中的 DEEPSEEK_API_KEY=...
      → 空（触发 ConfigurationError）
```

实现位于 [`config_manager.py`](translator_app/config_manager.py) 的 `_apply_env_fallback()` 方法。

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

- **文件**：[`translator_app/constants.py`](translator_app/constants.py)（18 行）
- **职责**：
  - 定义所有硬编码常量：应用名、文件名、默认配置值、系统提示词
- **关键常量**：
  | 常量 | 值 | 说明 |
  |------|-----|------|
  | `APP_NAME` | `"Academic Floating Translator"` | 应用标识 |
  | `CONFIG_FILE_NAME` | `"config.json"` | 配置文件名称 |
  | `HISTORY_FILE_NAME` | `"history.json"` | 历史记录文件名称 |
  | `LOG_FILE_NAME` | `"translator.log"` | 日志文件名称 |
  | `DEFAULT_API_URL` | `"https://api.deepseek.com/chat/completions"` | 默认 API 端点 |
  | `DEFAULT_MODEL` | `"deepseek-chat"` | 默认模型名称 |
  | `DEFAULT_TIMEOUT_SECONDS` | `45` | HTTP 请求超时（秒） |
  | `DEFAULT_TEMPERATURE` | `0.2` | 翻译温度（低=更确定性） |
  | `DEFAULT_HOTKEY` | `"<ctrl>+t"` | 默认全局热键 |
  | `MAX_HISTORY_ITEMS` | `10` | 历史记录上限 |
  | `SYSTEM_PROMPT` | 中文提示词 | 向模型声明"专业翻译专家"角色 |

### 4.4 `translator_app/exceptions.py` — 异常层次结构

- **文件**：[`translator_app/exceptions.py`](translator_app/exceptions.py)（22 行）
- **职责**：定义所有应用级异常类型，实现清晰错误分类
- **异常树**：
  ```
  TranslatorAppError (基类)
    ├── ConfigurationError   — 配置缺失/无效
    ├── DeepSeekAPIError     — API 请求失败
    ├── HistoryError         — 历史记录加载/保存失败
    └── HotkeyError          — 全局热键注册失败
  ```

### 4.5 `translator_app/models.py` — 数据模型

- **文件**：[`translator_app/models.py`](translator_app/models.py)（97 行）
- **职责**：定义三个核心 dataclass，使用 `slots=True` 优化内存
- **模型清单**：

  | 模型 | 字段 | 说明 |
  |------|------|------|
  | `AppConfig` | `api_key`, `api_url`, `model`, `hotkey`, `timeout_seconds`, `temperature` | 运行时配置，含 `from_dict()`/`to_dict()` 序列化 |
  | `HistoryEntry` | `timestamp`, `source_text`, `translated_text`, `source_language`, `target_language`, `style` | 单条翻译历史记录 |
  | `TranslationResult` | `source_text`, `translated_text`, `source_language`, `target_language`, `model`, `style` | 一次翻译的完整结果（传回 UI） |

### 4.6 `translator_app/logging_config.py` — 日志配置

- **文件**：[`translator_app/logging_config.py`](translator_app/logging_config.py)（24 行）
- **职责**：配置双输出日志（文件 + stderr），格式为 `时间 | 级别 | 模块名 | 消息`
- **日志文件位置**：`{项目根目录}/translator.log`

### 4.7 `translator_app/config_manager.py` — 配置管理

- **文件**：[`translator_app/config_manager.py`](translator_app/config_manager.py)（115 行）
- **职责**：
  - 从 `config.json` 加载/保存 `AppConfig`
  - 实现三层 API Key 回退机制（config.json → 环境变量 → .env）
  - 静态方法 `_read_dotenv()` 解析 `.env` 文件（K=V 格式，忽略注释和空行）
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `load_config()` | 读 config.json，反序列化为 AppConfig，调用 `_apply_env_fallback` |
  | `save_config(config)` | 序列化 AppConfig 写入 config.json |
  | `_apply_env_fallback(config)` | 若 api_key 为空，依次尝试环境变量和 .env 文件 |
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

### 4.10 `translator_app/deepseek_client.py` — API 客户端

- **文件**：[`translator_app/deepseek_client.py`](translator_app/deepseek_client.py)（193 行）
- **职责**：
  - 构造 OpenAI 兼容的 chat completions 请求
  - 验证 API Key（占位符检测、空白字符检测）
  - 解析 API 响应，提取翻译文本
  - 将 HTTP 错误转换为用户友好的 `DeepSeekAPIError`
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `translate(text, source, target, style)` | 发送翻译请求，返回翻译文本 |
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

- **文件**：[`translator_app/settings_dialog.py`](translator_app/settings_dialog.py)（277 行）
- **职责**：
  - 提供 API Key、API URL、Model、Hotkey、Timeout、Temperature 的编辑界面
  - 分两区：Connectivity（连接配置）和 Experience（体验设置）
  - 输入验证：保存前检查必填字段非空
  - 淡入动画（`showEvent` 重写）
- **关键方法**：
  | 方法 | 说明 |
  |------|------|
  | `build_config()` | 从表单控件提取值构建 AppConfig |
  | `_validate_before_accept()` | 校验必填字段，通过后调用 `accept()` |
  | `_build_card(title, hint, fields)` | 构建分组卡片 |

### 4.16 `translator_app/floating_window.py` — 主浮动窗口

- **文件**：[`translator_app/floating_window.py`](translator_app/floating_window.py)（1124 行）
- **职责**：核心 UI 模块，包含以下子组件：
  - **`create_line_icon()`**：用 QPainter 绘制自定义 SVG 风格图标（paste/copy/clear/swap/translate/history/settings/home，24x24）
  - **`DraggableHeaderFrame`**：无边框窗口拖拽移动
  - **`ClickToCopyTextEdit`**：点击即复制翻译结果
  - **`_make_copy_button(text)`**：创建 Copy 按钮（点击变 "Copied!" 1.5 秒后恢复）
  - **`HistoryCard`**：单条历史记录的卡片组件（含 SOURCE/TRANSLATION 各一个 Copy 按钮）
  - **`HistoryDialog`**：历史记录弹窗（ScrollArea + 卡片列表 + Clear History 按钮 + 淡入动画）
  - **`FloatingTranslatorWindow`**：主窗口类（~1124 行）
- **系统托盘**：`_create_tray_icon()` 创建系统托盘，含 Show/Hide、History、Settings、Quit 菜单项
- **布局结构**：
  ```
  ┌───────────────────────────────────┐
  │  [titleLabel] "translator"        │  ← DraggableHeaderFrame
  │  [subtitleLabel]                  │
  │  [Academic] [Casual] [Business] [Literary] │ ← 风格选择
  ├───────────────────────────────────┤
  │  SOURCE TEXT        [Clear] [Paste]│  ← _build_input_card
  │  ┌─────────────────────────────┐  │
  │  │  QTextEdit (可编辑)          │  │
  │  └─────────────────────────────┘  │
  ├───────────────────────────────────┤
  │           [Swap]                   │
  ├───────────────────────────────────┤
  │         [ Translate ]              │  ← primaryButton
  ├───────────────────────────────────┤
  │  TRANSLATED TEXT         [Copy]   │  ← _build_result_card
  │  ┌─────────────────────────────┐  │
  │  │  ClickToCopyTextEdit (只读) │  │
  │  └─────────────────────────────┘  │
  ├───────────────────────────────────┤
  │   [statusLabel]                    │  ← statusToast
  ├───────────────────────────────────┤
  │  [Translate] [History] [Settings] [⤢] │ ← bottom nav + size grip
  └───────────────────────────────────┘
  ```
- **动画系统**：
  - 结果卡片淡入（`_animate_result_card`）
  - 状态提示淡入（`_show_status`）
  - 窗口显隐动画（位置 + 透明度同时变化，`_start_visibility_animation`）
  - 设置/历史对话框淡入（`showEvent` 重写）

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
├── translator_app/            # 主包（15 个模块）
│   ├── __init__.py
│   ├── models.py
│   ├── constants.py
│   ├── exceptions.py
│   ├── config_manager.py
│   ├── logging_config.py
│   ├── language.py
│   ├── translation_style.py
│   ├── deepseek_client.py
│   ├── translation_service.py
│   ├── worker.py
│   ├── history_manager.py
│   ├── hotkey_manager.py
│   ├── settings_dialog.py
│   └── floating_window.py
├── tests/                     # pytest 测试集（14 个测试）
│   ├── test_language.py
│   ├── test_deepseek_client.py
│   └── test_translation_style.py
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

### 6.2 运行测试

```bash
pytest tests/ -v
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
2. 支持环境变量 `DEEPSEEK_API_KEY`（最高灵活性，CI/CD 友好）
3. 支持 `.env` 文件（开发者友好，`.gitignore` 已排除）

### 7.3 QThread 异步翻译

翻译 API 调用不阻塞 UI 主线程，通过 `TranslationWorker(QThread)` 实现。Worker 通过 pyqtSignal 将结果传回 UI 层，异常也通过信号传递。

### 7.4 历史记录上限

`MAX_HISTORY_ITEMS = 10`，新记录插入 `history.json` 数组头部，超出上限的旧记录被裁剪丢弃。

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

---

## 9. 注意事项

- **不要将 `config.json` 或 `.env` 提交到 Git**（已在 `.gitignore` 中排除）
- **不要修改 `config.example.json`** 中的 `api_key` 为真实密钥
- **`project/` 目录**是实验性 React/Vite 前端原型，非当前主应用代码，维护主应用时忽略此目录
- **pynput 需要系统权限**：在 macOS 上需授予辅助功能权限，Linux 上可能需要 root 或配置 X11
- **所有 QSS 样式字符串**使用 f-string 和 `TEXT_FONT_STACK` 常量避免字体栈重复
- **API Key 敏感操作**：`SettingsDialog` 的 `_api_key_input` 使用 `Password` echo mode 掩码显示
