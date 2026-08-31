"""Voice interface: push-to-talk mic -> STT (pluggable) -> agent -> edge-tts (spoken).

- Empty Enter = record (auto-stops after silence). Typed text = normal chat.
- Replies are printed AND spoken (Persian voice for Persian replies, English otherwise).
- Future: wake-word (Porcupine), full hands-free — planned after the GUI."""
import asyncio
import os
import re
import tempfile
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

from core.agent import VOICE_RULES
from core.config import Config
from interfaces.base import BaseInterface

SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE * 0.1)   # 100 ms frames
SPEECH_RMS = 350.0               # int16 RMS threshold: above = someone is talking
START_TIMEOUT = 7.0              # give up if no speech starts within this
SILENCE_SECS = 1.2               # stop after this much trailing silence
MAX_SECS = 25                    # hard cap per utterance


class VoiceInterface(BaseInterface):
    name = "voice"

    def __init__(self):
        super().__init__()
        self.extra_rules = VOICE_RULES
        self._stt = None  # lazy: loaded on first use
        self._tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts")
        os.makedirs(self._tmp, exist_ok=True)

    def run(self, agent) -> None:
        print("🎙  Voice mode — press ENTER and speak, or just type. Ctrl+C or /exit to quit.\n")
        while True:
            try:
                typed = input("🎤 [ENTER=speak | type=chat] ▶ ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye! 👋")
                return
            if typed == "/exit":
                return
            if typed == "/new":
                agent.reset()
                print("🆕 New session started.")
                continue

            if typed:
                user_text = typed
            else:
                user_text = self._listen_and_transcribe()
                if not user_text:
                    continue
                print(f"You 🗣 ▶ {user_text}")

            try:
                answer = agent.send(user_text)
            except Exception as exc:
                print(f"\n⚠️  Error: {exc}\n")
                continue
            print(f"\nJARVIS ▶ {answer}\n")
            self._speak(answer)

    # ---------- input: mic -> text ----------
    def _listen_and_transcribe(self) -> str:
        audio = self._record()
        if audio is None:
            return ""
        print("   🧠 transcribing...")
        try:
            if self._stt is None:
                from core.stt import get_stt
                self._stt = get_stt()
            return self._stt.transcribe(audio)
        except Exception as exc:
            print(f"   ⚠️ STT failed: {type(exc).__name__}: {exc}")
            return ""

    def _record(self):
        """Records until silence; returns float32 mono @16kHz (1-D) or None."""
        frames, speech_started, silent_chunks = [], False, 0
        started = time.time()
        print("   🔴 listening... speak now")
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="int16", blocksize=CHUNK)
        stream.start()
        try:
            while True:
                data, _ = stream.read(CHUNK)
                frames.append(data.copy())
                rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
                if not speech_started:
                    if rms > SPEECH_RMS:
                        speech_started, silent_chunks = True, 0
                    elif time.time() - started > START_TIMEOUT:
                        print("   (no speech detected)")
                        return None
                else:
                    silent_chunks = 0 if rms > SPEECH_RMS else silent_chunks + 1
                    if silent_chunks >= int(SILENCE_SECS / 0.1):
                        break
                    if sum(len(f) for f in frames) / SAMPLE_RATE > MAX_SECS:
                        break
        finally:
            stream.stop()
            stream.close()
        if not speech_started:
            return None
        return np.concatenate(frames).astype(np.float32).flatten() / 32768.0

    # ---------- output: text -> speech ----------
    def _speak(self, text: str) -> None:
        clean = re.sub(r"[*_`#>|]", "", text)  # strip markdown-ish symbols
        if not clean.strip():
            return
        voice = Config.VOICE_FA if self._looks_persian(clean) else Config.VOICE_EN
        path = os.path.join(self._tmp, f"resp_{int(time.time() * 1000)}.mp3")
        try:
            import edge_tts
            asyncio.run(edge_tts.Communicate(clean, voice=voice).save(path))
            data, sr = sf.read(path, dtype="float32")
            sd.play(data, sr)
            sd.wait()
        except Exception as exc:
            print(f"   ⚠️ TTS failed ({type(exc).__name__}: {exc}) — text only.")
        finally:
            if os.path.exists(path):
                os.remove(path)

    @staticmethod
    def _looks_persian(text: str) -> bool:
        return any("\u0600" <= ch <= "\u06FF" for ch in text)