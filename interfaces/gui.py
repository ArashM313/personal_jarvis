"""Web GUI: FastAPI + WebSocket live events + browser mic + wake-word engine."""
import asyncio
import io
import os
import queue
import threading
import webbrowser

import soundfile as sf
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.config import Config

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class GuiInterface:
    name = "gui"

    def __init__(self, bus):
        self.extra_rules = ""
        self.bus = bus
        self.engine = None
        self.app = None

    def run(self, agent) -> None:
        from core.voice_engine import VoiceEngine
        self.engine = VoiceEngine(self.bus)
        self.engine.start(agent)
        threading.Thread(target=self._autosleep, daemon=True).start()

        self.app = self._build(agent)
        url = f"http://127.0.0.1:{Config.GUI_PORT}"
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        print(f"🖥  GUI running at {url}  (wake-word engine active — say "
              f"'{Config.WAKE_WORDS[0]} wake up')\n")
        uvicorn.run(self.app, host="127.0.0.1", port=Config.GUI_PORT, log_level="warning")

    def _autosleep(self):
        import time
        while True:
            time.sleep(1)
            self.engine.auto_sleep_check()

    # ─────────────── FastAPI app ───────────────
    def _build(self, agent) -> FastAPI:
        app = FastAPI()
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/")
        async def index():
            return FileResponse(os.path.join(WEB_DIR, "index.html"))

        @app.websocket("/ws")
        async def ws(sock: WebSocket):
            await sock.accept()
            q: queue.Queue = queue.Queue()
            self.bus.subscribe(q.put)
            try:
                await sock.send_json({"type": "state",
                                      "value": "awake" if self.engine.awake else "sleeping"})
                while True:
                    evt = await asyncio.to_thread(q.get)
                    await sock.send_json(evt)
            except WebSocketDisconnect:
                pass
            finally:
                self.bus.unsubscribe(q.put)

        @app.post("/api/message")
        async def message(req: Request):
            body = await req.json()
            text = (body.get("text") or "").strip()
            if not text:
                return JSONResponse({"error": "empty"}, status_code=400)
            self.bus.publish("user_text", text=text, origin="typed")
            self.engine.submit_text(text)
            return {"queued": True}

        @app.post("/api/audio")
        async def audio(req: Request):
            data = await req.body()
            try:
                clip, _sr = sf.read(io.BytesIO(data), dtype="float32")
                text = self.engine.transcribe_blocking(clip).strip()
            except Exception as exc:
                return JSONResponse({"error": f"STT failed: {type(exc).__name__}"}, status_code=500)
            if not text:
                return {"text": ""}
            self.bus.publish("user_text", text=text, origin="mic")
            self.engine.submit_text(text)
            return {"text": text}

        @app.post("/api/wake")
        async def wake(req: Request):
            body = await req.json()
            self.engine.set_awake(bool(body.get("awake", True)))
            return {"ok": True}

        @app.post("/api/new")
        async def new_session():
            agent.reset()
            return {"ok": True}

        return app