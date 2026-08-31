import sys

from core.agent import Agent
from core.config import Config
from core.device import get_device
from core.events import EventBus
from interfaces.base import BaseInterface
from skills.base import SKILLS

BANNER = r"""
╔══════════════════════════════════════════════╗
║                J.A.R.V.I.S                   ║
╚══════════════════════════════════════════════╝"""


def pick_interface() -> BaseInterface:
    args = sys.argv[1:]
    if "--text" in args:
        from interfaces.terminal import TerminalInterface
        return TerminalInterface()
    if "--voice" in args:
        from interfaces.voice import VoiceInterface
        return VoiceInterface()
    if "--gui" in args:
        from interfaces.gui import GuiInterface
        return GuiInterface(EventBus())
    choice = input("Mode — [1] text  [2] voice  [3] GUI (default 1): ").strip()
    if choice == "2":
        from interfaces.voice import VoiceInterface
        return VoiceInterface()
    if choice == "3":
        from interfaces.gui import GuiInterface
        return GuiInterface(EventBus())
    from interfaces.terminal import TerminalInterface
    return TerminalInterface()


def main():
    is_local = "localhost" in Config.LLM_BASE_URL or "127.0.0.1" in Config.LLM_BASE_URL
    if not is_local and not Config.LLM_API_KEY:
        print("❌ No API key found! Set LLM_API_KEY in .env")
        sys.exit(1)

    bus = EventBus()
    iface = pick_interface()
    if hasattr(iface, "bus") and getattr(iface, "bus") is None:
        iface.bus = bus
    agent = Agent(extra_rules=iface.extra_rules, bus=bus)

    print(BANNER)
    print(f"   Chain   : {' → '.join(Config.MODEL_CHAIN)}")
    print(f"   API     : {Config.LLM_BASE_URL}")
    print(f"   Device  : {get_device()}")
    print(f"   Skills  : {len(SKILLS)} loaded")
    print(f"   Mode    : {iface.name}\n")
    iface.run(agent)


if __name__ == "__main__":
    main()