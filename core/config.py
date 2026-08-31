import json
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _parse_extra_body(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"[config] Ignoring invalid LLM_EXTRA_BODY (not valid JSON): {raw[:80]}")
        return {}


class Config:
    # --- brain (LLM) ---
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL",
                             "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
    MODEL_CHAIN = ([m.strip() for m in os.getenv("MODEL_CHAIN", "").split(",") if m.strip()]
                   or [LLM_MODEL])
    # Speed: cap how much history is sent per request; extra provider options
    # (e.g. disable hidden "thinking") are injected into the raw request body.
    LLM_MAX_CONTEXT_MESSAGES = int(os.getenv("LLM_MAX_CONTEXT_MESSAGES", "24"))
    LLM_EXTRA_BODY = _parse_extra_body(os.getenv("LLM_EXTRA_BODY", ""))

    # --- storage ---
    HISTORY_FILE = str(BASE_DIR / "data" / "history.json")
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "")

    # --- ears (STT) ---
    STT_PROVIDER = os.getenv("STT_PROVIDER", "local")             # local | groq
    STT_GROQ_API_KEY = os.getenv("STT_GROQ_API_KEY", "")
    STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
    VOICE_STT_MODEL = os.getenv("VOICE_STT_MODEL", "large-v3-turbo")
    VOICE_LANG = os.getenv("VOICE_LANG", "en")                    # en | fa | auto
    VOICE_SILENCE_SECS = float(os.getenv("VOICE_SILENCE_SECS", "3.0"))

    # --- mouth (TTS) ---
    VOICE_FA = os.getenv("VOICE_FA", "fa-IR-FaridNeural")
    VOICE_EN = os.getenv("VOICE_EN", "en-US-GuyNeural")