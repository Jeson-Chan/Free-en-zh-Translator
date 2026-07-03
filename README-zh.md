# 学术英文翻译器

一款基于Python和PyQt5构建的桌面浮动翻译工具。该工具专注于中英文学术或专业文本的翻译，并通过兼容OpenAI的聊天补全格式调用DeepSeek API或Qwen API。

## 功能特性

- 集成DeepSeek API（因为便宜）和Qwen api，配备学术翻译系统提示词
- 自动识别中英文语言方向
- 支持剪贴板粘贴功能
- 图片翻译，截图翻译，输出Markdown源码，Latex公式支持
- 翻译结果预览

## 快速开始

1. 克隆仓库

   ```
   git clone https://github.com/Jeson-Chan/Free-en-zh-Translator.git
   cd Free-en-zh-Translator
   ```

   

2. 配置本地**Python环境或虚拟环境**。

   前往Python官方网站：`https://www.python.org/`

   选择**3.12**版本并下载安装。

   创建虚拟环境（可选）（推荐）

   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate   # macOS/Linux
   ```

   

3. 安装依赖项：

   运行以下指令

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 翻译模型配置

首次运行时会弹出设置对话框，要求配置 DeepSeek API Key 和 Qwen API Key（也可以是别的多模态模型）。也可以提前创建 config.json（参考 config.example.json）或设置环境变量 DEEPSEEK_API_KEY 和 QWEN_API_KEY。

#### 文本翻译模型配置

以Deepseek为例，进入Deepseek开放平台：`https://platform.deepseek.com/usage` 

充值额度，获取 **api key**（sk-xxx...)

**api url**	`https://api.deepseek.com/chat/completions`

选择模型，建议使用最新发布的deepseek v4模型：

**model**

- `deepseek-v4-flash`
- `deepseek-v4-pro`

如需使用其他兼容模型，可在设置对话框中更改模型参数。

打开**Settings**，将以上参数分别填写到**API Key ，API URL， model**

示例：

> | API Key     | `sk-xxxxxx....`                             |
> | ----------- | ------------------------------------------- |
> | **API URL** | `https://api.deepseek.com/chat/completions` |
> | **model**   | `deepseek-v4-flash`                         |

#### 多模态视觉模型配置

多模态模型推荐阿里云百炼的**qwen3.6**系列，如qwen3.6-flash，**api key**可进入阿里云百炼平台获取：

`https://bailian.console.aliyun.com/cn-beijing?spm=5176.30260724.0.0.15c732a5CBBIb8&tab=model#/api-key`

其余操作同上。