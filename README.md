# 学术英文翻译器

一款基于Python和PyQt5构建的桌面浮动翻译工具。该工具专注于中英文学术或专业文本的翻译，并通过兼容OpenAI的聊天补全格式调用DeepSeek API。

## 功能特性

- 集成DeepSeek API，配备学术翻译系统提示词
- 自动识别中英文语言方向
- 支持剪贴板粘贴功能

## 快速开始

1. 配置本地**Python环境或虚拟环境**。

   前往Python官方网站：`https://www.python.org/`

   选择**3.12**版本并下载安装。

2. 安装依赖项：

   运行以下指令

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 翻译模型配置

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




  

# Academic English Translator

A desktop floating translation tool built with Python and PyQt5. The tool focuses on the translation of Chinese–English academic or professional texts and invokes the DeepSeek API using the OpenAI-compatible chat completion format.

## Features

- Integrates the DeepSeek API with a system prompt for academic translation  
- Automatically detects the language direction between Chinese and English  
- Supports clipboard paste functionality  

## Quick Start

1. Configure a **local Python environment or virtual environment**.  

   Visit the official Python website: `https://www.python.org/`  

   Select version **3.12**, download, and install.

2. Install dependencies:  

   Run the following command  

```bash
pip install -r requirements.txt
```

## Running the Program

```bash
python main.py
```

## Translation Model Configuration

Taking DeepSeek as an example, go to the DeepSeek open platform: `https://platform.deepseek.com/usage`  

Top up your balance and obtain an **API key** (sk-xxx...)

**API URL** `https://api.deepseek.com/chat/completions`

Select a model; it is recommended to use the latest DeepSeek v4 models:

**model**

- `deepseek-v4-flash`
- `deepseek-v4-pro`

If you need to use other compatible models, you can change the model parameters in the settings dialog.

Open **Settings** and fill in the corresponding parameters for **API Key**, **API URL**, and **model**.

Example:

> | API Key     | `sk-xxxxxx...`                              |
> | ----------- | ------------------------------------------- |
> | **API URL** | `https://api.deepseek.com/chat/completions` |
> | **model**   | `deepseek-v4-flash`                         |



