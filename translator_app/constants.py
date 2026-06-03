"""Application-wide constants."""

APP_NAME = "Academic Floating Translator"
CONFIG_FILE_NAME = "config.json"
HISTORY_FILE_NAME = "history.json"
LOG_FILE_NAME = "translator.log"

DEFAULT_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_TEMPERATURE = 0.2
DEFAULT_HOTKEY = "<ctrl>+t"
MAX_HISTORY_ITEMS = 10

SYSTEM_PROMPT = (
    "你是一位专业的翻译专家，请将以下英文或中文内容准确翻译为目标语言，"
    "保留关键术语、原文格式与上下文含义，并遵循用户选择的翻译风格。"
)
