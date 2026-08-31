import ctypes
import os
import subprocess
from datetime import datetime

import psutil
import pyautogui
import pyperclip

import threading
import winsound

from skills.base import skill


# ---------- apps ----------
@skill(
    description="Open an application, file, or folder on Windows. Use an app name like "
                "'notepad', 'calc', 'mspaint', 'explorer', 'cmd' or a full path like "
                "'C:/Users/Me/Desktop/report.docx'.",
    parameters={
        "type": "object",
        "properties": {"target": {"type": "string", "description": "App name or full path"}},
        "required": ["target"],
    },
)
def open_app(target: str) -> str:
    try:
        os.startfile(target)
        return f"Opened: {target}"
    except Exception:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", target])
            return f"Opened via shell: {target}"
        except Exception as exc:
            return f"Could not open '{target}': {exc}"


@skill(
    description="Force-close a running Windows application by process name, e.g. 'chrome.exe'.",
    parameters={
        "type": "object",
        "properties": {"process_name": {"type": "string", "description": "e.g. 'chrome.exe'"}},
        "required": ["process_name"],
    },
    dangerous=True,
)
def close_app(process_name: str) -> str:
    proc = subprocess.run(["taskkill", "/IM", process_name, "/F"],
                          capture_output=True, text=True)
    if proc.returncode == 0:
        return f"Closed {process_name}"
    return f"Could not close {process_name}: {proc.stderr or proc.stdout}"


# ---------- screen ----------
@skill(
    description="Take a screenshot of the whole screen and save it on the Desktop "
                "(in the 'Jarvis_Screenshots' folder).",
    parameters={"type": "object", "properties": {}},
)
def take_screenshot() -> str:
    folder = os.path.join(os.path.expanduser("~"), "Desktop", "Jarvis_Screenshots")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"screenshot_{datetime.now():%Y-%m-%d_%H-%M-%S}.png")
    pyautogui.screenshot(path)
    return f"Screenshot saved: {path}"


# ---------- volume ----------
def _volume_interface():
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    speaker = AudioUtilities.GetSpeakers()
    interface = speaker.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))



@skill(
    description="Set the master system volume (0 to 100).",
    parameters={
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "Volume percent 0-100"}},
        "required": ["level"],
    },
)

def _volume_by_keys(level: int) -> int:
    """Fallback: Windows volume keys change volume by 2% per press."""
    old_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0.02
    try:
        for _ in range(50):
            pyautogui.press("volumedown")
        for _ in range(round(level / 2)):
            pyautogui.press("volumeup")
    finally:
        pyautogui.PAUSE = old_pause
    return level


@skill(
    description="Set the master system volume (0 to 100).",
    parameters={
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "Volume percent 0-100"}},
        "required": ["level"],
    },
)
def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    try:
        _volume_interface().SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level}%"
    except Exception as exc:
        try:
            _volume_by_keys(level)
            return f"Volume ≈ {level}% (keyboard fallback — pycaw error: {type(exc).__name__})"
        except Exception as exc2:
            return f"set_volume failed — pycaw: {type(exc).__name__}: {exc} | keyboard: {exc2}"


@skill(
    description="Mute or unmute the system sound.",
    parameters={
        "type": "object",
        "properties": {"mute": {"type": "boolean", "description": "true = mute, false = unmute"}},
        "required": ["mute"],
    },
)

def set_mute(mute: bool) -> str:
    try:
        _volume_interface().SetMute(bool(mute), None)
        return "Muted" if mute else "Unmuted"
    except Exception:
        pyautogui.press("volumemute")
        return "Toggled mute via keyboard (pycaw unavailable)."
def system_status() -> str:
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("C:\\").percent
    battery = psutil.sensors_battery()
    bat = (f"{battery.percent}% ({'charging' if battery.power_plugged else 'on battery'})"
           if battery else "not found")
    return f"CPU: {cpu}% | RAM: {ram}% | Disk C: {disk}% used | Battery: {bat}"


# ---------- power ----------
@skill(description="Lock the Windows session immediately.", parameters={"type": "object", "properties": {}})
def lock_pc() -> str:
    ctypes.windll.user32.LockWorkStation()
    return "PC locked"


@skill(
    description="Shut down the PC after a delay.",
    parameters={
        "type": "object",
        "properties": {"seconds": {"type": "integer", "description": "Delay in seconds (default 30)"}},
    },
    dangerous=True,
)
def shutdown_pc(seconds: int = 30) -> str:
    subprocess.run(["shutdown", "/s", "/t", str(int(seconds))])
    return f"Shutdown scheduled in {seconds} seconds (cancel with cancel_shutdown)."


@skill(
    description="Restart the PC after a delay.",
    parameters={
        "type": "object",
        "properties": {"seconds": {"type": "integer", "description": "Delay in seconds (default 30)"}},
    },
    dangerous=True,
)
def restart_pc(seconds: int = 30) -> str:
    subprocess.run(["shutdown", "/r", "/t", str(int(seconds))])
    return f"Restart scheduled in {seconds} seconds (cancel with cancel_shutdown)."


@skill(description="Cancel a scheduled shutdown/restart.", parameters={"type": "object", "properties": {}})
def cancel_shutdown() -> str:
    subprocess.run(["shutdown", "/a"])
    return "Scheduled shutdown cancelled."


# ---------- clipboard & media ----------
@skill(description="Read the current text content of the clipboard.", parameters={"type": "object", "properties": {}})
def read_clipboard() -> str:
    text = pyperclip.paste()
    return text[:2000] if text else "(clipboard is empty)"


@skill(
    description="Put text into the clipboard.",
    parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
)
def write_clipboard(text: str) -> str:
    pyperclip.copy(text)
    return "Copied to clipboard."


@skill(
    description="Control media playback in any running player: 'playpause', 'next', 'previous'.",
    parameters={
        "type": "object",
        "properties": {"action": {"type": "string", "enum": ["playpause", "next", "previous"]}},
        "required": ["action"],
    },
)
def media_control(action: str) -> str:
    keys = {"playpause": "playpause", "next": "nexttrack", "previous": "prevtrack"}
    pyautogui.press(keys.get(action, "playpause"))
    return f"Media: {action}"


# ---------- escape hatch ----------
@skill(
    description="Run any PowerShell command for advanced tasks not covered by other tools. "
                "Prefer dedicated tools when they exist. Returns the command output.",
    parameters={
        "type": "object",
        "properties": {"command": {"type": "string", "description": "PowerShell command"}},
        "required": ["command"],
    },
    dangerous=True,
)
def run_command(command: str) -> str:
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", command],
                          capture_output=True, text=True, timeout=60)
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return output[:3000] if output else "(command finished with no output)"

# ---------- timer / brightness ----------
@skill(
    description="Start a countdown timer/reminder. When time is up, JARVIS beeps and shows "
                "a popup with the message. Timers live only while JARVIS is running.",
    parameters={
        "type": "object",
        "properties": {
            "minutes": {"type": "number", "description": "Minutes (e.g. 1.5 = 90 seconds)"},
            "seconds": {"type": "integer", "description": "Extra seconds (optional)"},
            "message": {"type": "string", "description": "What to remind (optional)"},
        },
    },
)
def set_timer(minutes: float = 0, seconds: int = 0, message: str = "Time's up!") -> str:
    total = int(float(minutes) * 60 + int(seconds))
    if total <= 0:
        return "Please provide a duration greater than zero."

    def ring():
        for _ in range(3):
            winsound.Beep(1200, 350)
        ctypes.windll.user32.MessageBoxW(0, f"⏰ {message}", "JARVIS Timer", 0x40000 | 0x40)

    threading.Timer(total, ring).start()
    nice = f"{total // 60}m {total % 60}s" if total >= 60 else f"{total}s"
    return f"⏳ Timer set for {nice}: {message}"


@skill(
    description="Set the screen brightness (0 to 100). Works on laptop built-in displays.",
    parameters={
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "Brightness percent 0-100"}},
        "required": ["level"],
    },
)
def set_brightness(level: int) -> str:
    try:
        import screen_brightness_control as sbc
    except ImportError:
        return "screen-brightness-control is not installed."
    level = max(0, min(100, int(level)))
    try:
        sbc.set_brightness(level)
        return f"Brightness set to {level}%"
    except Exception as exc:
        return f"Could not change brightness (external monitor?): {type(exc).__name__}: {exc}"