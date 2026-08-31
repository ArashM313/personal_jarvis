import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # --- brain (LLM) ---
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL",
                             "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
    # Ordered chain: first = primary, rest = fallbacks (router handles switching)
    MODEL_CHAIN = ([m.strip() for m in os.getenv("MODEL_CHAIN", "").split(",") if m.strip()]
                   or [LLM_MODEL])

    # --- storage ---
    HISTORY_FILE = str(BASE_DIR / "data" / "history.json")
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "")

    # --- ears (STT) ---
    STT_PROVIDER = os.getenv("STT_PROVIDER", "local")             # local | groq
    STT_GROQ_API_KEY = os.getenv("STT_GROQ_API_KEY", "")
    STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")  # model name on Groq
    VOICE_STT_MODEL = os.getenv("VOICE_STT_MODEL", "large-v3-turbo")  # local whisper size
    VOICE_LANG = os.getenv("VOICE_LANG", "fa")                    # fa | en | auto

    # --- mouth (TTS) ---
    VOICE_FA = os.getenv("VOICE_FA", "fa-IR-FaridNeural")
    VOICE_EN = os.getenv("VOICE_EN", "en-US-GuyNeural")