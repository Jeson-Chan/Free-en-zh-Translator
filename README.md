# Academic English Translator

A desktop floating translation tool built with Python and PyQt5. This tool specializes in translating Chinese and English academic or professional texts, and utilizes the DeepSeek API or Qwen API through an OpenAI-compatible chat completion format.

## Features

- Integrated DeepSeek API (due to cost-effectiveness) and Qwen API, equipped with academic translation system prompts
- Automatic detection of Chinese-English language direction
- Clipboard paste functionality
- Image translation, screenshot translation, Markdown source code output, LaTeX formula support
- Translation result preview

## Quick Start

1. Clone the repository

   ```
   git clone https://github.com/Jeson-Chan/Free-en-zh-Translator.git
   cd Free-en-zh-Translator
   ```

2. Configure a local **Python environment or virtual environment**.

   Visit the official Python website: `https://www.python.org/`

   Select **version 3.12** and download/install it.

   Create a virtual environment (optional) (recommended)

   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate   # macOS/Linux
   ```

3. Install dependencies:

   Run the following command:

```bash
pip install -r requirements.txt
```

## Running the Program

```bash
python main.py
```

## Translation Model Configuration

Upon first run, a settings dialog will appear, requiring configuration of the DeepSeek API Key and Qwen API Key (other multimodal models are also acceptable). Alternatively, you can create a config.json file in advance (refer to config.example.json) or set the environment variables DEEPSEEK_API_KEY and QWEN_API_KEY.

#### Text Translation Model Configuration

Using DeepSeek as an example, navigate to the DeepSeek open platform: `https://platform.deepseek.com/usage`

Recharge credits and obtain the **API key** (sk-xxx...)

**API URL** `https://api.deepseek.com/chat/completions`

Select a model; it is recommended to use the latest released DeepSeek v4 model:

**Model**

- `deepseek-v4-flash`
- `deepseek-v4-pro`

To use other compatible models, modify the model parameters in the settings dialog.

Open **Settings** and fill in the above parameters under **API Key**, **API URL**, and **Model**, respectively.

Example:

> | API Key     | `sk-xxxxxx....`                             |
> | ----------- | ------------------------------------------- |
> | **API URL** | `https://api.deepseek.com/chat/completions` |
> | **Model**   | `deepseek-v4-flash`                         |

#### Multimodal Vision Model Configuration

For multimodal models, the Alibaba Cloud Bailian **qwen3.6** series is recommended, such as qwen3.6-flash. The **API key** can be obtained from the Alibaba Cloud Bailian platform:

`https://bailian.console.aliyun.com/cn-beijing?spm=5176.30260724.0.0.15c732a5CBBIb8&tab=model#/api-key`

The remaining steps are identical to those described above.