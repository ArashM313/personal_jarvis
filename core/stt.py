"""Speech-to-text with pluggable providers (set in .env):
- local: faster-whisper on CPU — offline, private, free forever (recommended for Iran)
- groq:  whisper-large-v3-turbo via Groq API — best speed/accuracy (currently filtered in Iran)"""
import os

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import tempfile

from core.config import Config


class STT:
    def transcribe(self, audio) -> str:
        raise NotImplementedError


class GroqSTT(STT):
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=Config.STT_GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = Config.STT_MODEL
        self._tmp = tempfile.gettempdir()

    def transcribe(self, audio) -> str:
        import soundfile as sf
        path = os.path.join(self._tmp, f"jarvis_mic_{os.getpid()}.wav")
        sf.write(path, audio, 16000)
        try:
            with open(path, "rb") as f:
                tr = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language=None if Config.VOICE_LANG == "auto" else Config.VOICE_LANG,
                )
            return (tr.text or "").strip()
        finally:
            if os.path.exists(path):
                os.remove(path)


class LocalSTT(STT):
    def __init__(self):
        from faster_whisper import WhisperModel
        print(f"   (loading Whisper '{Config.VOICE_STT_MODEL}' — first run downloads ~1.6GB)")
        self.model = WhisperModel(Config.VOICE_STT_MODEL, device="cpu", compute_type="int8")

    def transcribe(self, audio) -> str:
        segments, _ = self.model.transcribe(
            audio,
            language=None if Config.VOICE_LANG == "auto" else Config.VOICE_LANG,
            vad_filter=True,
            condition_on_previous_text=False,
            beam_size=1,  # fast on CPU; accuracy for short commands is the same
            initial_prompt="گفتگو با دستیار صوتی فارسی‌زبان." if Config.VOICE_LANG == "fa" else None,
        )
        return " ".join(s.text.strip() for s in segments).strip()


def get_stt() -> STT:
    provider = (Config.STT_PROVIDER or "local").lower()
    if provider == "groq":
        if not Config.STT_GROQ_API_KEY:
            raise ValueError("STT_PROVIDER=groq but STT_GROQ_API_KEY is missing in .env")
        return GroqSTT()
    return LocalSTT()