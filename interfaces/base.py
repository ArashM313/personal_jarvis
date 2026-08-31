"""I/O layer: how JARVIS talks to the user.
Terminal today — GUI tomorrow — without touching the agent."""


class BaseInterface:
    name = "base"

    def __init__(self):
        self.extra_rules = ""  # injected into the agent's system prompt

    def run(self, agent) -> None:
        raise NotImplementedError