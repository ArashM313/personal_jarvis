"""Tiny thread-safe pub/sub so the agent & voice engine can feed any UI."""
import threading


class EventBus:
    def __init__(self):
        self._subs = []
        self._lock = threading.Lock()

    def subscribe(self, fn) -> None:
        with self._lock:
            self._subs.append(fn)

    def unsubscribe(self, fn) -> None:
        with self._lock:
            if fn in self._subs:
                self._subs.remove(fn)

    def publish(self, type_: str, **data) -> None:
        evt = {"type": type_, **data}
        with self._lock:
            subs = list(self._subs)
        for fn in subs:
            try:
                fn(evt)
            except Exception as exc:
                print(f"[bus] subscriber error: {type(exc).__name__}: {exc}")