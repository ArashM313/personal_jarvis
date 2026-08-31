"""Records 5 seconds and transcribes with the configured STT provider."""
import numpy as np
import sounddevice as sd
from core.config import Config
from core.stt import get_stt

SR = 16000
print(f"Provider: {Config.STT_PROVIDER} | local model: {Config.VOICE_STT_MODEL} | lang: {Config.VOICE_LANG}")
print("🎙  Speak in Persian for ~5 seconds...")
audio = sd.rec(int(SR * 5), samplerate=SR, channels=1, dtype="int16")
sd.wait()
audio = audio.astype(np.float32).flatten() / 32768.0
print("Transcribing...")
print("RESULT:", get_stt().transcribe(audio))