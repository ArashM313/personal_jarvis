import ctypes
import os
import subprocess
from datetime import datetime

import psutil
import pyautogui
import pyperclip

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
def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    _volume_interface().SetMasterVolumeLevelScalar(level / 100.0, None)
    return f"Volume set to {level}%"


@skill(
    description="Mute or unmute the system sound.",
    parameters={
        "type": "object",
        "properties": {"mute": {"type": "boolean", "description": "true = mute, false = unmute"}},
        "required": ["mute"],
    },
)
def set_mute(mute: bool) -> str:
    _volume_interface().SetMute(bool(mute), None)
    return "Muted" if mute else "Unmuted"


# ---------- system info ----------
@skill(
    description="Get a health report of the PC: CPU load, RAM usage, disk usage, battery.",
    parameters={"type": "object", "properties": {}},
)
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