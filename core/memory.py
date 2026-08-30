import json
from pathlib import Path


class Memory:
    """Persists the conversation as plain OpenAI-style message dicts."""

    def __init__(self, path: str, max_messages: int = 80):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_messages = max_messages

    def load(self) -> list:
        if not self.path.exists():
            return []
        try:
            messages = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(messages, list):
                return []
            messages = messages[-self.max_messages:]
            # Drop a dangling tool exchange (assistant tool_calls without their results)
            while messages and (
                messages[-1].get("role") == "tool" or messages[-1].get("tool_calls")
            ):
                messages.pop()
            return messages
        except Exception:
            return []

    def save(self, messages: list) -> None:
        try:
            self.path.write_text(
                json.dumps(messages[-self.max_messages:],
                           ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[memory] could not save history: {exc}")

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()