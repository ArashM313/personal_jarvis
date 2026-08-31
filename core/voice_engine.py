"""Continuous hands-free voice engine (wake word, command queue, TTS).
Runs server-side so it works with ANY interface (terminal or GUI)."""
import asyncio
import os
import queue
import random
import re
import tempfile
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

from core.config import Config

SR = 16000
CHUNK = int(SR * 0.1)
SPEECH_RMS = 350.0
MAX_SECS = 25
MIN_SECS = 0.4

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF\u2B00-\u2BFF\uFE0F\u200D]+"
)

GREETINGS = ["At your service, Sir.", "Yes, Sir?", "Standing by, Sir.", "Sir?"]
ACKS = ["On it, Sir.", "Right away, Sir.", "Consider it done, Sir."]
SLEEP_REPLY = "Very good, Sir."
AUTO_SLEEP_REPLY = "Going quiet, Sir. Say my name when you need me."
ALREADY_AWAKE = "I'm awake, Sir."
SLEEP_PHRASES = ("go to sleep", "go to bed", "that's all", "that will be all",
                 "goodbye jarvis", "goodbye jervis")
WAKE_UP_SUFFIXES = ("wake up", "wake", "get up", "are you awake")


class VoiceEngine:
    def __init__(self, bus):
        self.bus = bus
        self._tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts")
        os.makedirs(self._tmp, exist_ok=True)

        self._audio_q: queue.Queue = queue.Queue()
        self._cmd_q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._mic_muted = threading.Event()
        self._speak_lock = threading.Lock()

        self.awake = False
        self._agent = None
        self._last_activity = time.time()
        self._worker_busy = False
        self._ambient = None   # tiny.en wake listener
        self._main_stt = None  # full STT

    # ═══ lifecycle ═══
    def start(self, agent) -> None:
        self._agent = agent
        threading.Thread(target=self._warmup, daemon=True).start()
        for t in (self._mic_loop, self._stt_loop, self._worker_loop):
            threading.Thread(target=t, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _warmup(self):
        try:
            from faster_whisper import WhisperModel
            t0 = time.perf_counter()
            self._ambient = WhisperModel(Config.AMBIENT_STT_MODEL, device="cpu",
                                         compute_type="int8")
            from core.stt import get_stt
            self._main_stt = get_stt()
            print(f"   🎧 STT ready ({time.perf_counter() - t0:.0f}s) — "
                  f"say '{Config.WAKE_WORDS[0]} wake up'")
        except Exception as exc:
            print(f"   ⚠️ STT warmup failed: {type(exc).__name__}: {exc}")

    # ═══ public API for interfaces ═══
    def submit_text(self, text: str) -> None:
        self._last_activity = time.time()
        if self._worker_busy:
            self._speak(random.choice(ACKS))
        self._cmd_q.put(text)

    def transcribe_blocking(self, audio) -> str:
        if self._main_stt is None:
            from core.stt import get_stt
            self._main_stt = get_stt()
        return self._main_stt.transcribe(audio).strip()

    def set_awake(self, value: bool) -> None:
        if value and not self.awake:
            self._wake()
        elif not value and self.awake:
            self._sleep()

    # ═══ mic thread ═══
    def _mic_loop(self):
        while not self._stop.is_set():
            try:
                self._mic_session()
            except Exception as exc:
                print(f"   ⚠️ mic error ({type(exc).__name__}: {exc}) — retrying in 2s")
                time.sleep(2)

    def _mic_session(self):
        stream = sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=CHUNK)
        stream.start()
        seg, seg_silence = None, 0
        try:
            while not self._stop.is_set():
                data, _ = stream.read(CHUNK)
                if self._mic_muted.is_set():
                    seg, seg_silence = None, 0
                    continue
                rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
                if seg is None:
                    if rms > SPEECH_RMS:
                        seg, seg_silence = [data.copy()], 0
                else:
                    seg.append(data.copy())
                    seg_silence = 0 if rms > SPEECH_RMS else seg_silence + 1
                    dur = sum(len(f) for f in seg) / SR
                    if seg_silence >= int(Config.VOICE_SILENCE_SECS / 0.1) or dur > MAX_SECS:
                        if dur >= MIN_SECS:
                            audio = np.concatenate(seg).astype(np.float32).flatten() / 32768.0
                            self._audio_q.put(audio)
                        seg, seg_silence = None, 0
        finally:
            stream.stop()
            stream.close()

    # ═══ stt thread ═══
    def _stt_loop(self):
        while not self._stop.is_set():
            try:
                audio = self._audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if self._ambient is None or self._main_stt is None:
                continue
            self._last_activity = time.time()

            if not self.awake:
                text = self._tiny(audio).lower()
                hit = next((w for w in Config.WAKE_WORDS if w in text), None)
                if not hit:
                    continue
                rest = text.split(hit, 1)[1].strip(" ,.!?")
                self._wake()
                if any(s in rest for s in WAKE_UP_SUFFIXES):
                    rest = ""   # "jarvis wake up" = just wake, not a command
                if rest:
                    self.bus.publish("user_text", text=rest, origin="voice")
                    self.submit_text(rest)
                continue

            try:
                text = self._main_stt.transcribe(audio).strip()
            except Exception as exc:
                print(f"   ⚠️ STT failed: {type(exc).__name__}: {exc}")
                continue
            if not text:
                continue
            low = text.lower()
            if any(p in low for p in SLEEP_PHRASES):
                self._sleep()
                continue
            for w in Config.WAKE_WORDS:
                if low.startswith(w):
                    text = text[len(w):].strip(" ,.!?")
                    break
            if not text:
                continue
            print(f"You 🗣 ▶ {text}")
            self.bus.publish("user_text", text=text, origin="voice")
            self.submit_text(text)

    def _tiny(self, audio) -> str:
        segments, _ = self._ambient.transcribe(audio, vad_filter=True,
                                               condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segments).strip()

    # ═══ worker thread ═══
    def _worker_loop(self):
        while not self._stop.is_set():
            try:
                text = self._cmd_q.get(timeout=0.5)
            except queue.Empty:
                continue
            self._worker_busy = True
            self.bus.publish("state", value="thinking")
            try:
                answer = self._agent.send(text)
            except Exception as exc:
                print(f"\n⚠️  Error: {exc}\n")
                self.bus.publish("error", message=str(exc)[:200])
                self._worker_busy = False
                continue
            self._last_activity = time.time()
            print(f"\nJARVIS ▶ {answer}\n")
            self.bus.publish("answer", text=answer, spoken=True)
            self._speak(answer)
            self._worker_busy = False

    # ═══ state + speech ═══
    def _wake(self):
        self.awake = True
        self._last_activity = time.time()
        print("   🟢 awake")
        self.bus.publish("state", value="awake")
        g = random.choice(GREETINGS)
        self.bus.publish("answer", text=g, spoken=True)
        self._speak(g)

    def _sleep(self, auto: bool = False):
        self.awake = False
        print("   🔴 asleep")
        self.bus.publish("state", value="sleeping")
        msg = AUTO_SLEEP_REPLY if auto else SLEEP_REPLY
        self.bus.publish("answer", text=msg, spoken=True)
        self._speak(msg)

    def auto_sleep_check(self) -> None:
        if (self.awake and not self._worker_busy
                and time.time() - self._last_activity > Config.AUTO_SLEEP_SECS):
            self._sleep(auto=True)

    def _speak(self, text: str) -> None:
        clean = EMOJI_RE.sub(" ", re.sub(r"[*_`#>|]", "", text)).strip()
        if not clean.strip():
            return
        voice = Config.VOICE_FA if self._looks_persian(clean) else Config.VOICE_EN
        path = os.path.join(self._tmp, f"resp_{int(time.time() * 1000)}.mp3")
        with self._speak_lock:
            self._mic_muted.set()
            self.bus.publish("state", value="speaking")
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
                self._mic_muted.clear()
                self.bus.publish("state", value="awake" if self.awake else "sleeping")

    @staticmethod
    def _looks_persian(text: str) -> bool:
        return any("\u0600" <= ch <= "\u06FF" for ch in text)