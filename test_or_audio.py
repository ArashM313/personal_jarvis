"""Does OpenRouter accept AUDIO inside chat completions? (workaround STT test)"""
import base64
import io

import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from core.config import Config

MODEL = "google/gemini-2.5-flash"   # multimodal — costs a few cents or less
SR = 16000

print("🎙  Speak Persian for ~5 seconds...")
a = sd.rec(int(SR * 5), samplerate=SR, channels=1, dtype="int16")
sd.wait()
a = a.astype(np.float32).flatten() / 32768.0

buf = io.BytesIO()
sf.write(buf, a, SR, format="WAV")
b64 = base64.b64encode(buf.getvalue()).decode()

client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Transcribe the audio exactly. Output only the transcript text."},
            {"type": "input_audio", "input_audio": {"data": b64, "format": "wav"}},
        ]}],
    )
    print("RESULT ✅:", r.choices[0].message.content)
except Exception as e:
    print("FAILED ❌:", type(e).__name__, str(e)[:300])