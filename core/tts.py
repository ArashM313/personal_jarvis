"""Text-to-speech with automatic provider choice:
- gemini: native Gemini TTS — very natural English (used for non-Persian replies)
- edge:   Microsoft Edge voices — best Persian support (Farid/Dilara), also the fallback"""
import asyncio
import io
import os
import tempfile
import time
import wave

from core.config import Config


def looks_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _play(wav_bytes: bytes) -> None:
    import sounddevice as sd
    import soundfile as sf
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    sd.play(data, sr)
    sd.wait()


def _gemini_speak(text: str) -> None:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=Config.GEMINI_TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=Config.GEMINI_TTS_VOICE))),
        ),
    )
    pcm = resp.candidates[0].content.parts[0].inline_data.data  # 16-bit PCM @ 24kHz mono
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    _play(buf.getvalue())


def _edge_speak(text: str) -> None:
    import edge_tts
    import sounddevice as sd
    import soundfile as sf
    voice = Config.VOICE_FA if looks_persian(text) else Config.VOICE_EN
    tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts")
    os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, f"resp_{int(time.time() * 1000)}.mp3")
    asyncio.run(edge_tts.Communicate(text, voice=voice).save(path))
    try:
        data, sr = sf.read(path, dtype="float32")
        sd.play(data, sr)
        sd.wait()
    finally:
        if os.path.exists(path):
            os.remove(path)


def speak(text: str) -> None:
    """Chooses the right provider per reply. Persian -> edge (Gemini TTS has no fa voice)."""
    provider = (Config.TTS_PROVIDER or "gemini").lower()
    if provider == "edge" or looks_persian(text):
        _edge_speak(text)
        return
    try:
        _gemini_speak(text)
    except Exception as exc:
        print(f"   ⚠️ Gemini TTS failed ({type(exc).__name__}: {exc}) — falling back to edge-tts.")
        _edge_speak(text)