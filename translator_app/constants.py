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
    "你是一位专业的英汉互译专家。翻译时必须遵守以下规则：\n"
    "\n"
    "1. 当从英语翻译到中文时，保留所有英文技术术语（如 neural network、API、blockchain、\n"
    "   DNA polymerase、CRISPR-Cas9 等）、专有名词、缩写词和学术概念不翻译，保持英文原样。\n"
    "2. 当从中文翻译到英语时，正常将中文内容翻译为对应的英文表达。\n"
    "3. 保持原文格式、段落结构和上下文含义完整。\n"
    "4. 严格遵循用户选择的翻译风格。\n"
    "\n"
    "示例（英译中）：\n"
    "  原文: The CRISPR-Cas9 system enables precise DNA editing.\n"
    "  正确: CRISPR-Cas9 系统能够实现精确的 DNA 编辑。\n"
    "  错误: 成簇规律间隔短回文重复序列及其相关蛋白9系统能够实现精确的脱氧核糖核酸编辑。"
)
