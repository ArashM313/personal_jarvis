import sys

from core.agent import Agent
from core.config import Config
from core.device import get_device
from interfaces.terminal import TerminalInterface
from interfaces.voice import VoiceInterface
from skills.base import SKILLS

BANNER = r"""
╔══════════════════════════════════════════════╗
║      J.A.R.V.I.S  —  Phase 3: Voice          ║
╚══════════════════════════════════════════════╝"""


def pick_interface():
    args = sys.argv[1:]
    if "--text" in args:
        return TerminalInterface()
    if "--voice" in args:
        return VoiceInterface()
    # no flag? ask once
    choice = input("Mode — [1] text  [2] voice  (default 1): ").strip()
    return VoiceInterface() if choice == "2" else TerminalInterface()


def main():
    is_local = "localhost" in Config.LLM_BASE_URL or "127.0.0.1" in Config.LLM_BASE_URL
    if not is_local and not Config.LLM_API_KEY:
        print("❌ No API key found! Set LLM_API_KEY in .env")
        sys.exit(1)

    iface = pick_interface()
    agent = Agent(extra_rules=iface.extra_rules)

    print(BANNER)
    print(f"   Chain   : {' → '.join(Config.MODEL_CHAIN)}")
    print(f"   API     : {Config.LLM_BASE_URL}")
    print(f"   Device  : {get_device()}")
    print(f"   Skills  : {len(SKILLS)} loaded")
    print(f"   Mode    : {iface.name}\n")
    iface.run(agent)


if __name__ == "__main__":
    main()