import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL",
                             "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
    # Ordered chain: first = primary (strongest), rest = fallbacks
    MODEL_CHAIN = ([m.strip() for m in os.getenv("MODEL_CHAIN", "").split(",") if m.strip()]
                   or [LLM_MODEL])
    HISTORY_FILE = str(BASE_DIR / "data" / "history.json")
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "")