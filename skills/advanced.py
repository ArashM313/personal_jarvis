"""Advanced system skills: archives, recycle bin, network diagnostics."""
import os
import shutil
import socket
import subprocess

import requests

from skills.base import skill


@skill(
    description="Compress a file or folder into a .zip archive.",
    parameters={"type": "object",
                "properties": {"source": {"type": "string"},
                               "destination_zip": {"type": "string"}},
                "required": ["source", "destination_zip"]},
)
def zip_path(source: str, destination_zip: str) -> str:
    source = os.path.expanduser(source)
    base = os.path.splitext(os.path.expanduser(destination_zip))[0]
    if os.path.isdir(source):
        shutil.make_archive(base, "zip", source)
    else:
        shutil.make_archive(base, "zip", root_dir=os.path.dirname(source),
                            base_dir=os.path.basename(source))
    return f"Archive created: {base}.zip"


@skill(
    description="Extract a .zip archive into a destination folder (created if needed).",
    parameters={"type": "object",
                "properties": {"zip_file": {"type": "string"},
                               "destination_dir": {"type": "string"}},
                "required": ["zip_file", "destination_dir"]},
)
def unzip_archive(zip_file: str, destination_dir: str) -> str:
    destination_dir = os.path.expanduser(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)
    shutil.unpack_archive(os.path.expanduser(zip_file), destination_dir)
    return f"Extracted {zip_file} → {destination_dir}"


@skill(
    description="Move a file or folder to the Recycle Bin — RECOVERABLE, so prefer this "
                "over delete_path for user-requested deletions.",
    parameters={"type": "object",
                "properties": {"path": {"type": "string"}}, "required": ["path"]},
)
def trash_path(path: str) -> str:
    from send2trash import send2trash
    send2trash(os.path.expanduser(path))
    return f"Sent to Recycle Bin: {path}"


@skill(
    description="Get network info: hostname, local IP, public IP.",
    parameters={"type": "object", "properties": {}},
)
def get_ip_info() -> str:
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except OSError:
        local_ip = "?"
    try:
        public_ip = requests.get("https://api.ipify.org", timeout=10).text
    except Exception:
        public_ip = "(unavailable)"
    return f"Hostname: {hostname} | Local IP: {local_ip} | Public IP: {public_ip}"


@skill(
    description="Ping a host (4 packets) to check connectivity and latency.",
    parameters={"type": "object",
                "properties": {"host": {"type": "string"}}, "required": ["host"]},
)
def ping_host(host: str) -> str:
    proc = subprocess.run(["ping", "-n", "4", host], capture_output=True,
                          text=True, timeout=30)
    out = (proc.stdout + proc.stderr).strip()
    return out[-800:] if len(out) > 800 else out