# PRD：图片翻译功能（Qwen 多模态模型）

> **文档版本**：v1.0
> **创建日期**：2026-07-02
> **状态**：Draft
> **作者**：chenbo

---

## 1. 概述

### 1.1 功能目标

为学术英文翻译器新增 **图片翻译** 功能：用户通过上传图片或截图输入，系统利用 Qwen 多模态大模型依次完成「图片内容识别」和「内容翻译」两个处理步骤，最终输出 Markdown 源码格式的翻译结果。

### 1.2 核心价值

| 用户痛点 | 解决方案 |
|----------|----------|
| 论文 PDF / 截图中的文字无法直接复制 | 多模态模型直接识别图片中的文字、公式、表格 |
| 手动 OCR 后格式混乱，公式丢失 | 大模型结构化识别，保留标题层级、列表、公式等格式 |
| OCR 结果需要再次手动翻译 | 识别 + 翻译流水线一体化，端到端输出 |

### 1.3 适用范围

- 学术论文截图（含文字、公式、图表标题、参考文献）
- 教材 / 技术文档截图
- 论文 PDF 页面截图
- 包含中英文混排内容的图片

---

## 2. 用户流程

```
用户操作                      系统处理                         界面反馈
─────────                    ────────                         ────────
点击「图片翻译」入口    →     切换到图片翻译模式          →     显示图片输入区域
                                                          ↓
选择输入方式：                                           
  ├─ 上传文件           →     加载并预览图片              →     缩略图预览 + 文件名
  └─ 截图输入           →     调用系统截图工具            →     截取后自动回填预览
                                                          ↓
点击「开始翻译」        →     Step 1: 内容识别            →     状态提示「正在识别图片内容...」
                            Step 2: 内容翻译              →     状态提示「正在翻译...」
                                                              动态加载标识、实时显示耗时
                                                          ↓
翻译完成                →     输出 Markdown 源码          →     结果区显示 Markdown 源码
                                                          ↓
用户可：
  ├─ 点击「复制」       →     复制 Markdown 源码到剪贴板
  ├─ 点击「预览」       →     渲染 Markdown 为富文本预览
  └─ 点击「导出 .md」   →     保存为 .md 文件到本地
```

---

## 3. 输入模块

### 3.1 图片文件上传

| 项目 | 规格 |
|------|------|
| 支持格式 | `.png` `.jpg` `.jpeg` `.bmp` `.webp` |
| 最大文件大小 | 20 MB（Qwen API 限制） |
| 最小分辨率 | 100 × 100 px |
| 最大分辨率 | 4096 × 4096 px（超出自动等比缩放） |
| 交互方式 | 点击上传按钮触发文件选择器，或拖拽图片到输入区域 |

### 3.2 截图输入

| 项目 | 规格 |
|------|------|
| 触发方式 | 点击「截图」按钮，或使用快捷键 `Ctrl+Shift+S` |
| 截图流程 | 最小化主窗口 → 全屏半透明遮罩 → 鼠标框选区域 → 回车确认 / Esc 取消 |
| 实现方案 | PyQt5 全屏透明窗口 + `QScreen.grabWindow()` 截取选区 |
| 截图后行为 | 自动回填到图片预览区域，恢复主窗口 |

### 3.3 图片预处理

在发送给 API 前，对图片进行预处理：

```python
# 预处理流水线
1. 格式统一    → 转换为 PNG（Qwen API 兼容性最佳）
2. 尺寸校验    → 超出 4096px 自动等比缩放
3. 体积校验    → 超过 20MB 进行质量压缩（quality=85）
4. Base64 编码 → 编码为 base64 字符串，嵌入 API 请求的 image_url 字段
```

---

## 4. 数据处理流水线

### 4.1 架构概览

```
┌─────────────┐     ┌───────────────────┐     ┌───────────────────┐     ┌──────────────┐
│  图片输入    │ ──→ │  大模型节点 1      │ ──→ │  大模型节点 2      │ ──→ │  结果输出     │
│  (预处理后)  │     │  内容识别 (OCR+)   │     │  学术翻译          │     │  (Markdown)   │
└─────────────┘     └───────────────────┘     └───────────────────┘     └──────────────┘
        │                     │                         │                       │
   base64 图片           识别 Prompt                翻译 Prompt            Markdown 源码
   + 格式信息         + 图片 base64             + 识别结果文本          + 复制/预览/导出
                           ↓                         ↓
                    Qwen VL API                 Qwen VL API
                    (多模态调用)                (纯文本调用)
```

### 4.2 大模型节点 1：图片内容识别

**目标**：从图片中提取所有文字内容，保留文档结构和格式信息。

**API 调用配置**：

| 参数 | 值 |
|------|------|
| 模型 | `qwen3.6-flash-2026-04-16(Qwen3.6)` |
| API 格式 | OpenAI Chat Completions 兼容 |
| 消息类型 | `image_url`（base64）+ `text`（识别指令） |
| temperature | 0.1（低随机性，确保识别准确） |
| max_tokens | 8192 |

**系统提示词（识别节点）**：

```
你是一名精通学术排版的资深期刊编辑
**文本处理规则**
原文内容不变
-   请对Fig. X进行斜体处理
-   示例：*Fig. 2* 

**数学符号与公式处理规则**
如遇到数学符号或数学公式，请将其转换为 Markdown 能够渲染的 LaTeX 公式代码：
-   行内公式使用单美元符号（$）包裹。
-   块级公式使用双美元符号（$$）包裹。

**格式示例**
-   行内公式示例：$E = mc^2$
-   块级公式示例：
    $$
    \int_{a}^{b} f(x) \, dx
    $$

**输出格式强制要求**
1. 绝对禁止对反斜杠进行额外转义。
   - LaTeX 命令如 \in、\mathbb、\text、\sum、\beta 必须保持单反斜杠。
   - 严禁输出 \\in、\\mathbb 等双反斜杠形式。

2. 绝对禁止输出字面字符串 "\n"。
   - 换行必须使用真实的换行符，不是反斜杠加字母 n 两个字符。
   - 每句话结束直接回车换行，不要写 \n。

3. 代码块标记 ``` 必须出现在行首，前后各留一个空行。

4. 公式块 $$ 必须出现在行首，前后各留一个空行。

5. 输出内容必须是可直接复制到 .md 文件中渲染的最终 Markdown 源码。
   不需要二次转义，不需要二次解析。
```

**用户消息格式**：

```json
{
  "role": "user",
  "content": [
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/png;base64,{base64_string}"
      }
    },
    {
      "type": "text",
      "text": "请识别这张图片中的所有文字内容，按照文档结构输出 Markdown 格式。"
    }
  ]
}
```

**输出**：结构化的 Markdown 文本（保留标题、列表、公式、表格等）。

### 4.3 大模型节点 2：学术翻译

**目标**：将识别结果翻译为目标语言，保持学术风格，输出 Markdown 源码。

**API 调用配置**：

| 参数 | 值 |
|------|------|
| 模型 | `deepseek-v4-pro`|
| API 格式 | OpenAI Chat Completions 兼容 |
| 消息类型 | `text`（纯文本，不含图片） |
| temperature | 0.2（与现有翻译功能一致） |
| max_tokens | 8192 |

**系统提示词（翻译节点）**：

```
**翻译任务指令**

你是一位专业的英汉互译专家。翻译时必须遵守以下规则：

1.  **术语保留原则（英译中）**
    当从英语翻译到中文时，必须保留所有英文技术术语（如 neural network、API、blockchain、DNA polymerase、CRISPR-Cas9 等）、专有名词、缩写词和学术概念不翻译，保持英文原样。

    普通学术词汇（如 raw features、low-level feature maps、noise domain）译为自然流畅的中文术语。

    术语译法保持一致（如 "feature maps" 统一译为"特征图"）

    图片标识不翻译，如Fig. 2。

2.  **正常翻译原则（中译英）**
    当从中文翻译到英语时，将中文内容正常翻译为对应的英文表达。

3.  **格式与语境保持**
    严格保持原文的格式、段落结构和上下文含义的完整性。

4.  **风格遵循**
    严格遵循用户选择的翻译风格。

示例（英译中）：
    原文: The CRISPR-Cas9 system enables precise DNA editing.
    正确: CRISPR-Cas9 系统能够实现精确的 DNA 编辑。
    错误: 成簇规律间隔短回文重复序列及其相关蛋白9系统能够实现精确的脱氧核糖核酸编辑。

    原文:
**翻译风格要求**
采用学术性语调。在英译中时，保留英文技术术语和专业词汇的原貌。使用符合研究或专业写作预期的正式措辞与结构。

**数学符号与公式处理规则**
如遇到数学符号或数学公式，请将其转换为 Markdown 能够渲染的 LaTeX 公式代码：
-   行内公式使用单美元符号（$）包裹。
-   块级公式使用双美元符号（$$）包裹。

**格式示例**
-   行内公式示例：$E = mc^2$
-   块级公式示例：
    $$
    \int_{a}^{b} f(x) \, dx
    $$

**输出格式强制要求**
1. 绝对禁止对反斜杠进行额外转义。
   - LaTeX 命令如 \in、\mathbb、\text、\sum、\beta 必须保持单反斜杠。
   - 严禁输出 \\in、\\mathbb 等双反斜杠形式。

2. 绝对禁止输出字面字符串 "\n"。
   - 换行必须使用真实的换行符，不是反斜杠加字母 n 两个字符。
   - 每句话结束直接回车换行，不要写 \n。

3. 代码块标记 ``` 必须出现在行首，前后各留一个空行。

4. 公式块 $$ 必须出现在行首，前后各留一个空行。

5. 输出内容必须是可直接复制到 .md 文件中渲染的最终 Markdown 源码。
   不需要二次转义，不需要二次解析。

**输出格式**
以markdown源码的格式输出
```

**用户消息格式**：

```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "请将以下学术内容翻译为目标语言，保持 Markdown 格式不变：\n\n{recognized_text}"
    }
  ]
}
```

**输出**：翻译后的 Markdown 源码。

### 4.4 错误处理与降级

| 失败场景 | 处理策略 |
|----------|----------|
| 节点 1 识别失败（API 超时/错误） | 重试 1 次，仍失败则提示用户「图片识别失败，请检查图片清晰度后重试」 |
| 节点 1 识别结果为空 | 提示「未检测到文字内容，请确认图片包含可读文字」 |
| 节点 2 翻译失败 | 保留节点 1 的识别结果输出，提示「翻译失败，已为您展示识别结果」 |
| 图片格式不支持 | 上传前校验，不支持格式弹出提示 |
| 图片过大 | 自动压缩，若仍超限则提示用户 |
| API Key 无效 / 余额不足 | 复用现有的认证错误处理逻辑（401 特殊处理） |

---

## 5. 输出模块

### 5.1 Markdown 源码展示

| 项目 | 规格 |
|------|------|
| 展示方式 | 等宽字体（Consolas / Source Code Pro）的 QTextEdit，只读模式 |
| 语法高亮 | 可选：使用 `pygments` 或自定义 QSS 实现基础 Markdown 高亮 |
| 行号 | 显示行号栏，便于定位长文档 |

### 5.2 操作按钮

| 按钮 | 功能 |
|------|------|
| 复制 | 将 Markdown 源码复制到系统剪贴板 |
| 预览 | 切换为 Markdown 渲染视图（富文本），再次点击切回源码 |
| 导出 .md | 弹出文件保存对话框，将结果保存为 `.md` 文件 |
| 重新翻译 | 使用相同图片重新执行流水线 |

### 5.3 Markdown 预览渲染

使用 Python Markdown 库将源码渲染为 HTML，在 PyQt5 的 `QTextBrowser` 中展示：

```
依赖：markdown >= 3.6（含 tables、fenced_code、md_in_html 扩展）
数学公式：使用 MathJax CDN 或 KaTeX 在 QTextBrowser 中渲染
```

---

## 6. 技术设计

### 6.1 新增 / 修改模块

```
translator_app/
├── qwen_client.py              # 新增：Qwen VL API 客户端（OpenAI 兼容格式）
├── image_preprocessor.py       # 新增：图片预处理（格式校验、缩放、压缩、base64 编码）
├── image_recognition_service.py # 新增：节点 1 — 图片内容识别服务
├── image_translation_service.py # 新增：节点 2 — 识别结果翻译服务
├── image_pipeline.py           # 新增：流水线编排（节点 1 → 节点 2，状态回调）
├── screenshot_tool.py          # 新增：截图工具（全屏透明窗口 + 区域选取）
├── image_input_widget.py       # 新增：图片输入组件（上传按钮 + 截图按钮 + 预览）
├── markdown_output_widget.py   # 新增：Markdown 输出组件（源码/预览切换 + 复制 + 导出）
├── image_worker.py             # 新增：QThread 后台线程（运行流水线，不阻塞 UI）
├── floating_window.py          # 修改：新增图片翻译入口，切换文本/图片翻译模式
├── settings_dialog.py          # 修改：新增 Qwen API 配置项（API Key / URL / Model）
├── models.py                   # 修改：新增 ImageTranslationResult 数据模型
├── constants.py                # 修改：新增 Qwen 相关常量（默认模型、提示词）
├── config_manager.py           # 修改：支持保存/读取 Qwen API 配置
└── hotkey_manager.py           # 修改：注册截图快捷键 Ctrl+Shift+S
```

### 6.2 Qwen API 客户端

复用现有的 OpenAI 兼容请求模式，新增 `QwenClient` 类：

```python
class QwenClient:
    """Qwen VL (视觉语言模型) API 客户端，OpenAI Chat Completions 兼容格式。"""

    def __init__(self, api_key: str, api_url: str, model: str, timeout: int):
        ...

    def recognize_image(self, image_base64: str, system_prompt: str, user_prompt: str) -> str:
        """发送图片 + 文本指令，返回识别结果（多模态调用）。"""
        ...

    def translate_text(self, system_prompt: str, user_prompt: str) -> str:
        """发送纯文本翻译请求（复用 chat completions）。"""
        ...
```

### 6.3 流水线编排

```python
class ImageTranslationPipeline:
    """图片翻译流水线：识别 → 翻译，两阶段串行执行。"""

    def __init__(self, qwen_client: QwenClient, on_progress: Callable):
        ...

    def execute(self, image_base64: str) -> ImageTranslationResult:
        """
        执行流水线：
        1. 调用识别节点 → 返回 Markdown 格式的识别结果
        2. 调用翻译节点 → 返回翻译后的 Markdown
        3. 通过 on_progress 回调通知 UI 当前阶段
        """
        ...
```

### 6.4 数据模型扩展

```python
@dataclass
class ImageTranslationResult:
    """图片翻译结果"""
    source_image_path: str          # 原始图片路径（或 "screenshot"）
    recognized_text: str            # 节点 1 输出：识别结果（Markdown）
    translated_text: str            # 节点 2 输出：翻译结果（Markdown）
    source_language: str            # 检测到的源语言
    target_language: str            # 目标语言
    recognition_tokens: int         # 识别消耗的 token 数
    translation_tokens: int         # 翻译消耗的 token 数
    timestamp: str                  # 完成时间
    error: Optional[str] = None     # 错误信息（如有）
```

### 6.5 配置扩展

`config.json` 新增 Qwen 相关字段：

```json
{
  "qwen_api_key": "",
  "qwen_api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
  "qwen_model": "qwen-vl-max",
  "image_max_size_mb": 20,
  "screenshot_hotkey": "<ctrl>+<shift>+s"
}
```

配置 UI 中新增一个分组卡片 **Multimodal**：
- Qwen API Key（密码掩码输入）
- Qwen API URL
- Qwen Model（下拉选择或手动输入）

### 6.6 主窗口模式切换

在现有浮动窗口中新增切换入口：

```
底部导航栏（修改后）：
[Translate] [Image] [History] [Settings] [⤢]

点击 [Image] 切换到图片翻译模式：
- 输入区变为图片输入组件（上传 + 截图 + 预览）
- 翻译按钮改为「开始翻译」
- 结果区变为 Markdown 输出组件（源码/预览切换）

点击 [Translate] 切回文本翻译模式：
- 恢复原有的文本输入 + 翻译结果布局
```

---

## 7. UI 设计

### 7.1 图片翻译模式布局

```
┌───────────────────────────────────────────┐
│  "translator"                             │  ← 标题（不变）
│  "Image Translation · Qwen VL"            │  ← 副标题（更新）
├───────────────────────────────────────────┤
│  SOURCE IMAGE          [Upload] [Capture] │  ← 图片输入卡片标题行
│  ┌─────────────────────────────────────┐  │
│  │                                     │  │
│  │     [图片预览区域]                    │  │  ← 缩略图预览（居中）
│  │     或                               │  │
│  │     拖拽图片到此处 / 点击上传          │  │  ← 空状态提示
│  │                                     │  │
│  └─────────────────────────────────────┘  │
│  📄 screenshot_20260702.png  1920×1080    │  ← 文件信息栏
├───────────────────────────────────────────┤
│              [  开始翻译  ]                │  ← 主操作按钮
├───────────────────────────────────────────┤
│  ⏳ 正在识别图片内容... (1/2)              │  ← 进度状态栏（两阶段）
│  ━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░    │  ← 进度条（可选）
├───────────────────────────────────────────┤
│  TRANSLATED (MARKDOWN)   [Copy] [Preview] │  ← 结果卡片标题行
│  ┌─────────────────────────────────────┐  │
│  │  # 第三章 方法论                     │  │  ← Markdown 源码（等宽字体）
│  │                                     │  │
│  │  本研究采用 **transformer** 架构...   │  │
│  │                                     │  │
│  │  $$                                 │  │
│  │  \text{Attention}(Q,K,V) = ...      │  │
│  │  $$                                 │  │
│  │                                     │  │
│  └─────────────────────────────────────┘  │
├───────────────────────────────────────────┤
│  [Export .md]                             │  ← 导出按钮
├───────────────────────────────────────────┤
│  [Translate] [Image] [History] [Settings] [⤢] │ ← 底部导航栏
└───────────────────────────────────────────┘
```

### 7.2 交互状态

| 状态 | 输入区 | 翻译按钮 | 结果区 | 进度栏 |
|------|--------|----------|--------|--------|
| 空闲（无图片） | 空状态提示 | 禁用 | 空 | 隐藏 |
| 已加载图片 | 缩略图预览 | 可用 | 空 | 隐藏 |
| 识别中 | 缩略图 + 半透明遮罩 | 禁用 + 加载动画 | 空 | 「正在识别图片内容... (1/2)」 |
| 翻译中 | 缩略图 + 半透明遮罩 | 禁用 + 加载动画 | 空 | 「正在翻译... (2/2)」 |
| 完成 | 缩略图预览 | 可用（重新翻译） | Markdown 输出 | 隐藏 |
| 失败 | 缩略图预览 | 可用（重试） | 错误提示 | 红色错误信息 |

---

## 8. 非功能性需求

### 8.1 性能

| 指标 | 目标 |
|------|------|
| 图片预处理耗时 | < 500ms（20MB 以内图片） |
| 节点 1（识别）响应时间 | < 30s（默认超时 60s） |
| 节点 2（翻译）响应时间 | < 30s（默认超时 60s） |
| 端到端耗时 | < 60s（常规学术论文截图） |
| UI 响应性 | 流水线运行期间 UI 不卡顿（QThread 后台执行） |

### 8.2 可靠性

- API 调用失败自动重试 1 次（指数退避 2s）
- 流水线中途失败保留已完成阶段的结果（识别成功但翻译失败时，展示识别结果）
- 截图工具异常时优雅降级（提示用户使用文件上传）

### 8.3 安全性

- Qwen API Key 采用与现有 DeepSeek Key 相同的三层安全机制（config.json > 环境变量 > .env）
- 图片数据仅在 API 调用期间存在内存中，不持久化到磁盘（除非用户主动导出）
- 截图数据不写入临时文件，直接在内存中 base64 编码

### 8.4 可访问性

- 截图快捷键 `Ctrl+Shift+S` 可在设置中自定义
- 上传按钮和截图按钮均支持键盘 Tab 导航和 Enter 触发
- 进度状态栏同时提供文字描述和视觉进度指示

---

## 9. 依赖清单

### 9.1 新增 Python 依赖

```
# requirements.txt 追加
Pillow>=10.0,<11          # 图片预处理（格式转换、缩放、压缩）
markdown>=3.6,<4          # Markdown → HTML 渲染（预览功能）
```

### 9.2 可选依赖

```
Pygments>=2.16,<3         # Markdown 源码语法高亮（可选增强）
```

### 9.3 API 依赖

| 服务 | 用途 | 备注 |
|------|------|------|
| 阿里云 DashScope（Qwen VL） | 图片识别 + 翻译 | 需用户自行提供 API Key |
| DashScope API URL | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | OpenAI 兼容格式 |

---

## 10. 测试计划

### 10.1 单元测试

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_image_preprocessor.py` | 格式校验、尺寸缩放、体积压缩、base64 编码、边界情况 |
| `test_qwen_client.py` | API 请求构造、多模态消息格式、错误处理、认证失败 |
| `test_image_recognition_service.py` | 提示词拼接、响应解析、空结果处理 |
| `test_image_translation_service.py` | 翻译提示词、格式保持验证、语言方向判断 |
| `test_image_pipeline.py` | 流水线编排、阶段回调、部分失败处理 |
| `test_screenshot_tool.py` | 区域选取坐标计算、快捷键触发 |

### 10.2 集成测试

| 场景 | 验证点 |
|------|--------|
| 上传英文论文截图 | 端到端：识别 → 翻译 → Markdown 输出 |
| 上传含公式的图片 | 公式识别正确性（LaTeX 语法保留） |
| 上传含表格的图片 | 表格 Markdown 语法正确性 |
| 上传中文论文截图 | 自动检测为中文 → 翻译为英文 |
| 截图 → 翻译完整流程 | 截图工具 + 流水线集成 |
| 大图片（>10MB） | 自动压缩后正常处理 |
| API 超时 / 失败 | 错误提示正确，UI 不崩溃 |

### 10.3 手动验证

| 验证项 | 方法 |
|--------|------|
| Markdown 渲染效果 | 复制输出到 Typora / VS Code 验证渲染 |
| 公式渲染 | 在支持 LaTeX 的 Markdown 编辑器中验证 |
| UI 响应性 | 流水线运行期间拖动窗口、切换 Tab |
| 截图准确性 | 截取小区域文字，对比识别结果 |

---

## 11. 里程碑

| 阶段 | 内容 | 预计工作量 |
|------|------|------------|
| **M1：基础流水线** | Qwen 客户端 + 图片预处理 + 识别/翻译服务 + 流水线编排 + CLI 可运行 | 3-4 天 |
| **M2：UI 集成** | 图片输入组件 + Markdown 输出组件 + 模式切换 + 主窗口集成 | 3-4 天 |
| **M3：截图功能** | 截图工具 + 快捷键注册 + 截图回填 | 1-2 天 |
| **M4：完善与测试** | 错误处理 + 边界情况 + 单元测试 + 集成测试 | 2-3 天 |
| **M5：增强（可选）** | Markdown 预览渲染 + 语法高亮 + 历史记录集成 | 1-2 天 |

---

## 12. 开放问题

| # | 问题 | 备选方案 | 建议 |
|---|------|----------|------|
| 1 | Qwen VL 模型版本选择：`qwen-vl-max` vs `qwen-vl-plus` | max 更准确但更贵更慢；plus 更快更便宜但复杂公式/表格识别可能不佳 | 默认 max，设置中允许切换 |
| 2 | 是否支持批量图片（一次上传多张） | v1 仅支持单张；v2 可扩展为多图拼接识别 | v1 单张，留扩展接口 |
| 3 | 识别结果是否需要人工编辑后再翻译 | 可在节点 1 和节点 2 之间插入编辑步骤 | v1 不插入，自动流水线；v2 可增加可选编辑步骤 |
| 4 | 翻译结果是否纳入翻译历史 | 现有历史记录仅支持文本，图片翻译结果更长 | 保存元数据（图片路径 + 时间戳），不保存全文 |
| 5 | Qwen API 和 DeepSeek API 是否可以共用配置 | 两者都是 OpenAI 兼容格式，但模型和 URL 不同 | 独立配置，复用客户端基类 |

---

## 附录 A：Qwen VL API 请求示例

### 多模态请求（节点 1：识别）

```bash
curl -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer ${QWEN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-vl-max",
    "messages": [
      {
        "role": "system",
        "content": "你是一个专业的文档内容识别助手..."
      },
      {
        "role": "user",
        "content": [
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/png;base64,iVBORw0KGgo..."
            }
          },
          {
            "type": "text",
            "text": "请识别这张图片中的所有文字内容，按照文档结构输出 Markdown 格式。"
          }
        ]
      }
    ],
    "temperature": 0.1,
    "max_tokens": 8192
  }'
```

### 纯文本请求（节点 2：翻译）

```bash
curl -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer ${QWEN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-vl-max",
    "messages": [
      {
        "role": "system",
        "content": "你是一个专业的学术翻译专家..."
      },
      {
        "role": "user",
        "content": "请将以下学术内容翻译为目标语言...\n\n# Chapter 3\n..."
      }
    ],
    "temperature": 0.2,
    "max_tokens": 8192
  }'
```

---

## 附录 B：与现有架构的关系

```
                    ┌─────────────────────────────┐
                    │       floating_window.py     │
                    │  (新增模式切换 + UI 容器)      │
                    └──────┬──────────┬───────────┘
                           │          │
              ┌────────────┘          └────────────┐
              ▼                                    ▼
   ┌─────────────────────┐             ┌──────────────────────┐
   │  文本翻译模式（现有）  │             │  图片翻译模式（新增）   │
   │                     │             │                      │
   │  QTextEdit 输入      │             │  image_input_widget  │
   │  translation_service │             │  image_pipeline      │
   │  deepseek_client     │             │  qwen_client         │
   │  worker (QThread)    │             │  image_worker        │
   │  ClickToCopyTextEdit │             │  markdown_output     │
   └─────────────────────┘             └──────────────────────┘
              │                                    │
              ▼                                    ▼
   ┌─────────────────────┐             ┌──────────────────────┐
   │   DeepSeek API       │             │   Qwen VL API        │
   │   (deepseek-chat)    │             │   (qwen-vl-max)      │
   └─────────────────────┘             └──────────────────────┘
```
