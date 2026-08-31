"""Developer skills: search inside file contents, run Python, read-only Git, VS Code."""
import os
import subprocess

from skills.base import skill

SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "env",
             "site-packages", "appdata"}


@skill(
    description="Search for text INSIDE file contents (like grep/VS Code search). "
                "Optionally restrict with extensions like '.py,.js'. Returns file:line matches.",
    parameters={"type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string", "description": "Folder to search (default: home)"},
                    "extensions": {"type": "string", "description": "e.g. '.py,.txt'"},
                }, "required": ["query"]},
)
def search_in_files(query: str, path: str = "", extensions: str = "") -> str:
    path = os.path.expanduser(path or "~")
    exts = {e.strip().lower() for e in extensions.split(",") if e.strip()}
    matches, stop = [], False
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs
                   if d.lower() not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if exts and not name.lower().endswith(tuple(exts)):
                continue
            full = os.path.join(root, name)
            try:
                if os.path.getsize(full) > 2_000_000:
                    continue
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if query.lower() in line.lower():
                            matches.append(f"{full}:{i}: {line.strip()[:150]}")
                            if len(matches) >= 25:
                                stop = True
                                break
            except OSError:
                continue
            if stop:
                break
        if stop:
            break
    if not matches:
        return f"No matches for '{query}' under {path}"
    return f"Found {len(matches)} match(es):\n" + "\n".join(matches)


@skill(
    description="Run a Python script with the system Python and return its output. "
                "Useful for executing code, quick computations, automation scripts.",
    parameters={"type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "args": {"type": "string", "description": "Optional CLI arguments"},
                }, "required": ["script_path"]},
    dangerous=True,
)
def run_python(script_path: str, args: str = "") -> str:
    script_path = os.path.expanduser(script_path)
    if not os.path.isfile(script_path):
        return f"Script not found: {script_path}"
    cmd = ["python", script_path] + (args.split() if args else [])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                          cwd=os.path.dirname(script_path) or ".")
    out = (proc.stdout + "\n" + proc.stderr).strip()
    header = f"exit code {proc.returncode}"
    return f"{header}\n{out[:3000]}" if out else f"{header} (no output)"


GIT_READONLY = {"status", "log", "diff", "branch", "show", "remote", "tag", "blame"}


@skill(
    description="Run a READ-ONLY git command (status, log, diff, branch, show, blame) "
                "inside a repository and return the output.",
    parameters={"type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "subcommand": {"type": "string", "description": "e.g. 'status' or 'log --oneline -5'"},
                }, "required": ["repo_path", "subcommand"]},
)
def git_command(repo_path: str, subcommand: str) -> str:
    parts = subcommand.split()
    if not parts or parts[0] not in GIT_READONLY:
        return f"Only read-only commands are allowed here: {sorted(GIT_READONLY)}"
    proc = subprocess.run(["git"] + parts, cwd=os.path.expanduser(repo_path),
                          capture_output=True, text=True, timeout=30)
    out = (proc.stdout + proc.stderr).strip()
    return out[:3000] or "(no output)"


@skill(
    description="Open a file or folder in Visual Studio Code.",
    parameters={"type": "object",
                "properties": {"target": {"type": "string"}}, "required": ["target"]},
)
def open_in_vscode(target: str) -> str:
    target = os.path.expanduser(target)
    try:
        subprocess.Popen(["code", target])
        return f"Opened in VS Code: {target}"
    except FileNotFoundError:
        return "'code' is not on PATH — open VS Code → F1 → 'Shell Command: Install " \
               "code command in PATH', then try again."