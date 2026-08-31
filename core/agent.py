import json
import time

from openai import OpenAI

import skills  # noqa: F401  (importing registers all skills)
from skills.base import execute_skill, get_tools, is_dangerous
from core.config import Config
from core.memory import Memory
from core.router import ModelRouter

SYSTEM_PROMPT = """You are JARVIS, a desktop assistant running on the user's Windows PC.

Rules:
- Complete the user's tasks using the available tools whenever an action is needed. You may chain several tools in a row.
- If a tool returns an error, read the error and try a smarter approach (e.g. fix the path) instead of giving up immediately.
- Destructive actions are confirmed by the system automatically; never repeat the confirmation, just briefly explain what the action does.
- Match the user's language: if they write in Persian, answer in Persian; if English, answer in English.
- After finishing, report briefly what you did.
- If a task is impossible with your tools, say so clearly and suggest the closest alternative.
- Keep answers concise and friendly, like a calm and competent butler.
- When a task needs several tools, call as many of them as possible in a single response (batch tool calls) instead of one per turn."""

VOICE_RULES = """
- VOICE MODE: the user speaks ENGLISH commands by voice. Reply in English, spoken aloud. After finishing any tool work, reply with ONE short natural sentence (under 20 words) — never lists, bullets, steps, markdown, emojis, or code blocks. If the request was transcribed imperfectly, make your best guess from context instead of asking about typos."""


class Agent:
    def __init__(self, extra_rules: str = ""):
        self.client = OpenAI(
            api_key=Config.LLM_API_KEY or "not-needed",
            base_url=Config.LLM_BASE_URL,
        )
        self.tools = get_tools()
        self.router = ModelRouter(Config.MODEL_CHAIN)
        self.memory = Memory(Config.HISTORY_FILE)
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT + extra_rules}]
        self.messages += self.memory.load()
        self.max_tool_rounds = 8
        self.quality_fails = 0

    def send(self, user_text: str) -> str:
        """Process one user message and return JARVIS's final text answer."""
        self.router.pick_best_available()
        self.messages.append({"role": "user", "content": user_text})
        t0 = time.perf_counter()
        final_text = self._run_tool_loop()
        print(f"   ⏱ total LLM time: {time.perf_counter() - t0:.1f}s")
        self.messages.append({"role": "assistant", "content": final_text})
        self.memory.save(self._persistable())
        return final_text

    def _run_tool_loop(self) -> str:
        self.quality_fails = 0
        for _ in range(self.max_tool_rounds):
            msg = self._chat(use_tools=True).choices[0].message

            if not msg.tool_calls and not (msg.content or "").strip():
                if self._escalate("empty response"):
                    continue
                return "(model returned an empty response — try rephrasing or /new)"

            if not msg.tool_calls:
                return (msg.content or "").strip() or "(no text response)"

            self.messages.append(self._serialize_assistant(msg))
            for tc in msg.tool_calls:
                ok, result = self._execute(tc)
                if not ok:
                    self.quality_fails += 1
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            if self.quality_fails >= 3 and self._escalate("repeated invalid tool calls"):
                continue

        if self._escalate("max rounds reached"):
            return self._run_tool_loop()
        msg = self._chat(use_tools=False).choices[0].message
        return (msg.content or "").strip() or "(no progress — try /new)"

    def _view(self) -> list:
        """System prompt + a trimmed recent window (starts on a 'user' boundary
        so we never send a broken tool-call sequence)."""
        limit = Config.LLM_MAX_CONTEXT_MESSAGES
        if len(self.messages) <= limit:
            return self.messages
        window = self.messages[-limit:]
        i = 0
        while i < len(window) and window[i].get("role") != "user":
            i += 1  # skip a partial tool exchange at the cut point
        if i >= len(window):
            return self.messages
        return [self.messages[0]] + window[i:]

    def _chat(self, use_tools: bool):
        kwargs = {
            "model": self.router.current,
            "messages": self._view(),
            "temperature": 0.3,
        }
        if Config.LLM_EXTRA_BODY:
            kwargs["extra_body"] = Config.LLM_EXTRA_BODY
        if use_tools:
            kwargs["tools"] = self.tools
        t0 = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            nxt = self.router.advance(f"API error: {type(exc).__name__}")
            if nxt is None:
                raise
            return self._chat(use_tools)
        print(f"   ⏱ {self.router.current}: {time.perf_counter() - t0:.1f}s")
        return resp

    def _escalate(self, reason: str) -> bool:
        nxt = self.router.advance(reason)
        if nxt is None:
            return False
        self.quality_fails = 0
        return True

    @staticmethod
    def _serialize_assistant(msg) -> dict:
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

    def _execute(self, tc) -> tuple:
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            print(f"   🔧 {name}(invalid JSON arguments)")
            return False, "Error: the arguments were not valid JSON. Call the tool again with correct JSON."
        print(f"   🔧 {name}({args})")
        if is_dangerous(name) and not self._confirm(name, args):
            return True, "USER_DENIED: the user did not allow this action."
        result = execute_skill(name, args)
        print(f"      ↳ {result[:150]}")
        return (not result.startswith("Error")), result

    @staticmethod
    def _confirm(name: str, args: dict) -> bool:
        print(f"   ⚠️  Dangerous action: {name}({args})")
        answer = input("      Allow? [y/N] ").strip().lower()
        return answer == "y"

    def _persistable(self) -> list:
        return [m for m in self.messages if m.get("role") != "system"]

    def reset(self) -> None:
        self.memory.reset()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]