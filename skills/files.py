import fnmatch
import os
import shutil

from skills.base import skill


@skill(
    description="List the contents of a folder. Use '' for the user's home folder.",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}},
)
def list_directory(path: str = "") -> str:
    path = path or os.path.expanduser("~")
    if not os.path.isdir(path):
        return f"Not a folder: {path}"
    entries = sorted(os.listdir(path))
    lines = []
    for name in entries[:100]:
        full = os.path.join(path, name)
        lines.append(("[D] " if os.path.isdir(full) else "[F] ") + name)
    if len(entries) > 100:
        lines.append(f"... and {len(entries) - 100} more")
    return "\n".join(lines) if lines else "(empty folder)"


@skill(
    description="Search files/folders by name pattern (supports * wildcards). "
                "Example: pattern='*.pdf', path='C:/Users/Me/Documents'.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "Folder to search in (default: home)"},
        },
        "required": ["pattern"],
    },
)
def search_files(pattern: str, path: str = "") -> str:
    path = path or os.path.expanduser("~")
    matches, checked = [], 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d.lower() not in
                   ("appdata", "node_modules", ".git", "$recycle.bin", "windows")]
        for name in dirs + files:
            checked += 1
            if fnmatch.fnmatch(name.lower(), pattern.lower()):
                matches.append(os.path.join(root, name))
                if len(matches) >= 25:
                    break
        if len(matches) >= 25 or checked > 50000:
            break
    if not matches:
        return f"No matches for '{pattern}' under {path}"
    return f"Found {len(matches)} match(es):\n" + "\n".join(matches)


@skill(
    description="Create a folder (including parent folders).",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
)
def create_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return f"Folder ready: {path}"


@skill(
    description="Copy a file or folder to a new location.",
    parameters={
        "type": "object",
        "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
        "required": ["source", "destination"],
    },
)
def copy_path(source: str, destination: str) -> str:
    if os.path.isdir(source):
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
    return f"Copied {source} -> {destination}"


@skill(
    description="Move or rename a file/folder.",
    parameters={
        "type": "object",
        "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
        "required": ["source", "destination"],
    },
)
def move_path(source: str, destination: str) -> str:
    shutil.move(source, destination)
    return f"Moved {source} -> {destination}"


@skill(
    description="Permanently delete a file or folder. Be careful!",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    dangerous=True,
)
def delete_path(path: str) -> str:
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    return f"Deleted: {path}"


@skill(
    description="Read a text file (first 4000 characters).",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
)
def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(4000)
    return content or "(file is empty)"


@skill(
    description="Write text to a file (creates or overwrites it). Use for notes and small files.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}, "text": {"type": "string"}},
        "required": ["path", "text"],
    },
)
def write_text_file(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return f"Written: {path}"