import json

from openai import OpenAI

import skills  # noqa: F401  (importing registers all skills)
from skills.base import execute_skill, get_tools, is_dangerous
from core.config import Config
from core.memory import Memory

SYSTEM_PROMPT = """You are JARVIS, a desktop assistant running on the user's Windows PC.

Rules:
- Complete the user's tasks using the available tools whenever an action is needed. You may chain several tools in a row.
- If a tool returns an error, read the error and try a smarter approach (e.g. fix the path) instead of giving up immediately.
- Destructive actions are confirmed by the system automatically; never repeat the confirmation, just briefly explain what the action does.
- Match the user's language: if they write in Persian, answer in Persian; if English, answer in English.
- After finishing, report briefly what you did.
- If a task is impossible with your tools, say so clearly and suggest the closest alternative.
- Keep answers concise and friendly, like a calm and competent butler."""


class Agent:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.LLM_API_KEY or "not-needed",
            base_url=Config.LLM_BASE_URL,
        )
        self.model = Config.LLM_MODEL
        self.tools = get_tools()
        self.memory = Memory(Config.HISTORY_FILE)
        # System prompt is always fresh (not persisted), rest of history is loaded
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.messages += self.memory.load()
        self.max_tool_rounds = 8

    def send(self, user_text: str) -> str:
        """Process one user message and return JARVIS's final text answer."""
        self.messages.append({"role": "user", "content": user_text})
        final_text = self._run_tool_loop()
        self.messages.append({"role": "assistant", "content": final_text})
        self.memory.save(self._persistable())
        return final_text

    def _run_tool_loop(self) -> str:
        for _ in range(self.max_tool_rounds):
            msg = self._chat(use_tools=True).choices[0].message
            if not msg.tool_calls:
                return (msg.content or "").strip() or "(no text response)"

            self.messages.append(self._serialize_assistant(msg))
            for tc in msg.tool_calls:
                result = self._execute(tc)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # Round limit reached: force a plain-text answer without tools
        msg = self._chat(use_tools=False).choices[0].message
        return (msg.content or "").strip() or "(The model kept calling tools — try /new.)"

    def _chat(self, use_tools: bool):
        kwargs = {"model": self.model, "messages": self.messages, "temperature": 0.3}
        if use_tools:
            kwargs["tools"] = self.tools
        return self.client.chat.completions.create(**kwargs)

    @staticmethod
    def _serialize_assistant(msg) -> dict:
        """Convert a response message into a storable/replayable dict."""
        return {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in msg.tool_calls
            ],
        }

    def _execute(self, tc) -> str:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            return "Error: the model produced invalid arguments (invalid JSON)."
        print(f"   🔧 {tc.function.name}({args})")
        if is_dangerous(tc.function.name) and not self._confirm(tc.function.name, args):
            return "USER_DENIED: the user did not allow this action."
        return execute_skill(tc.function.name, args)

    @staticmethod
    def _confirm(name: str, args: dict) -> bool:
        print(f"   ⚠️  Dangerous action: {name}({args})")
        answer = input("      Allow? [y/N] ").strip().lower()
        return answer == "y"

    def _persistable(self) -> list:
        """History without the system prompt (it is re-injected on startup)."""
        return [m for m in self.messages if m.get("role") != "system"]

    def reset(self) -> None:
        """Start a fresh conversation."""
        self.memory.reset()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]