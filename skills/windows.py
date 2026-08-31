import subprocess

import pyautogui
import pygetwindow as gw

from skills.base import skill


@skill(
    description="List all open windows with titles and state (minimized/maximized/normal). "
                "Useful to see what the user is doing — e.g. the currently playing YouTube "
                "video appears in the browser window title.",
    parameters={"type": "object", "properties": {}},
)
def list_open_windows() -> str:
    windows = [w for w in gw.getAllWindows() if w.title.strip()]
    if not windows:
        return "(no open windows found)"
    lines = []
    for i, w in enumerate(windows, 1):
        state = ("minimized" if w.isMinimized else
                 "maximized" if w.isMaximized else "normal")
        lines.append(f"{i}. [{state}] {w.title}")
    return "\n".join(lines)


@skill(
    description="Bring a window to the front and focus it by matching part of its title "
                "(case-insensitive). Example: title='youtube' or title='visual studio'.",
    parameters={
        "type": "object",
        "properties": {"title": {"type": "string", "description": "Part of the window title"}},
        "required": ["title"],
    },
)
def focus_window(title: str) -> str:
    w = _find_window(title)
    if w.isMinimized:
        w.restore()
    w.activate()
    return f"Focused: {w.title}"


@skill(
    description="Minimize ALL windows and show the desktop (like pressing Win+D).",
    parameters={"type": "object", "properties": {}},
)
def minimize_all_windows() -> str:
    pyautogui.hotkey("win", "d")
    return "All windows minimized (desktop shown)."


@skill(
    description="Minimize one window by matching part of its title.",
    parameters={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
)
def minimize_window(title: str) -> str:
    w = _find_window(title)
    w.minimize()
    return f"Minimized: {w.title}"


@skill(
    description="Maximize one window by matching part of its title.",
    parameters={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
)
def maximize_window(title: str) -> str:
    w = _find_window(title)
    w.maximize()
    return f"Maximized: {w.title}"


@skill(
    description="Close a window by matching part of its title (like clicking its X button).",
    parameters={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
    dangerous=True,
)
def close_window(title: str) -> str:
    w = _find_window(title)
    w.close()
    return f"Closed: {w.title}"


@skill(
    description="List running processes that own a visible window (open apps) with their "
                "process names. Use it to discover process names, e.g. before close_app.",
    parameters={"type": "object", "properties": {}},
)
def list_processes() -> str:
    cmd = ("Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
           "Select-Object -First 30 Id,ProcessName,MainWindowTitle | Format-Table -AutoSize")
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, timeout=30)
    return proc.stdout.strip() or "(no windowed processes found)"


def _find_window(title: str):
    matches = [w for w in gw.getAllWindows()
               if title.lower() in w.title.lower() and w.title.strip()]
    if not matches:
        raise LookupError(f"No window title contains '{title}'. "
                          f"Use list_open_windows to see exact titles.")
    return matches[0]