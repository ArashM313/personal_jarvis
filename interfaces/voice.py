"""Terminal voice mode — a thin wrapper over the core VoiceEngine."""
import threading

from core.agent import VOICE_RULES
from core.voice_engine import VoiceEngine
from interfaces.base import BaseInterface


class VoiceInterface(BaseInterface):
    name = "voice"

    def __init__(self):
        super().__init__()
        self.extra_rules = VOICE_RULES
        self.engine = None

    def run(self, agent) -> None:
        from core.events import EventBus
        self.engine = VoiceEngine(EventBus())
        self.engine.bus.subscribe(lambda e: None)  # terminal shows prints already
        self.engine.start(agent)

        auto = threading.Thread(target=self._autosleep_loop, daemon=True)
        auto.start()

        print("🎙  Continuous voice mode — say 'Jarvis wake up'. Type /exit to quit.\n")
        while True:
            try:
                typed = input().strip()
            except (KeyboardInterrupt, EOFError):
                self.engine.stop()
                print("\nGoodbye! 👋")
                return
            if typed == "/exit":
                self.engine.stop()
                return
            if typed == "/new":
                agent.reset()
                print("🆕 New session started.")
                continue
            if typed:
                self.engine.submit_text(typed)

    def _autosleep_loop(self):
        import time
        while True:
            time.sleep(1)
            self.engine.auto_sleep_check()