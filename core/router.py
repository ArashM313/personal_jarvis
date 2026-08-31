"""Automatic model router.

An ordered chain of models (in .env: MODEL_CHAIN=m1,m2,m3,...):
- Failover:    API / rate-limit / quota errors bench a model for 5 minutes and move on.
- Escalation:  repeated weak answers (empty, invalid tool calls) also move to the next model.
- Every new user turn starts with the strongest model that is not benched.
"""
import time

COOLDOWN_SECONDS = 300


class ModelRouter:
    def __init__(self, chain: list):
        chain = [m.strip() for m in chain if m and m.strip()]
        if not chain:
            raise ValueError("Model chain is empty — set MODEL_CHAIN or LLM_MODEL in .env")
        self.chain = chain
        self.index = 0
        self.banned_until = {}

    @property
    def current(self) -> str:
        return self.chain[self.index]

    def pick_best_available(self) -> str:
        """Start of a user turn: prefer the strongest healthy model."""
        now = time.time()
        for i, name in enumerate(self.chain):
            if now >= self.banned_until.get(name, 0):
                if i != self.index:
                    print(f"   🧠 Using model: {name}")
                self.index = i
                return name
        # everything is benched — try the primary anyway
        self.index = 0
        return self.chain[0]

    def advance(self, reason: str):
        """Bench the current model and move to the next healthy one."""
        self.banned_until[self.current] = time.time() + COOLDOWN_SECONDS
        now = time.time()
        for i, name in enumerate(self.chain):
            if i != self.index and now >= self.banned_until.get(name, 0):
                old = self.current
                self.index = i
                print(f"   🔀 {old} → {self.current}   ({reason})")
                return self.current
        return None  # no other model available