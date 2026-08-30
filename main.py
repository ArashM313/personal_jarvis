import sys

from core.agent import Agent
from core.config import Config
from core.device import get_device
from skills.base import SKILLS

BANNER = r"""
╔══════════════════════════════════════════════╗
║      J.A.R.V.I.S  —  Phase 1: Text (Qwen)    ║
╚══════════════════════════════════════════════╝"""


def main():
    is_local = "localhost" in Config.LLM_BASE_URL or "127.0.0.1" in Config.LLM_BASE_URL
    if not is_local and not Config.LLM_API_KEY:
        print("❌ No API key found!")
        print("   Get a FREE Qwen key: https://bailian.console.alibabacloud.com")
        print("   (or switch provider in .env — alternatives are commented there)")
        sys.exit(1)

    agent = Agent()
    print(BANNER)
    print(f"   Model : {Config.LLM_MODEL}")
    print(f"   API   : {Config.LLM_BASE_URL}")
    print(f"   Device: {get_device()}")
    print(f"   Skills: {len(SKILLS)} loaded")
    print("   Commands: /new (fresh session)   /exit (quit)\n")

    while True:
        try:
            user = input("You ▶ ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! 👋")
            break

        if not user:
            continue
        if user == "/exit":
            break
        if user == "/new":
            agent.reset()
            print("🆕 New session started.")
            continue

        try:
            answer = agent.send(user)
            print(f"\nJARVIS ▶ {answer}\n")
        except Exception as exc:
            print(f"\n⚠️  Error: {exc}\n")


if __name__ == "__main__":
    main()