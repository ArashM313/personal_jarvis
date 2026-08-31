from interfaces.base import BaseInterface


class TerminalInterface(BaseInterface):
    name = "text"

    def run(self, agent) -> None:
        while True:
            try:
                user = input("You ▶ ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye! 👋")
                return
            if not user:
                continue
            if user == "/exit":
                return
            if user == "/new":
                agent.reset()
                print("🆕 New session started.")
                continue
            try:
                print(f"\nJARVIS ▶ {agent.send(user)}\n")
            except Exception as exc:
                print(f"\n⚠️  Error: {exc}\n")