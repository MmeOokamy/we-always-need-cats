#!/usr/bin/env python3
"""Claude Code hook: forwards every event to the desktop cats.

Reads the event on standard input, keeps the essentials and sends them to
cats.py over a local socket. If the program is not running, it is started.
This script writes nothing and always exits without an error, so that it never
gets in Claude Code's way.
"""

import json
import os
import socket
import sys

APP_NAME = "we-always-need-cats"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
SOCKET = os.path.join(RUNTIME, f"{APP_NAME}.sock")


def short(text, length=60):
    text = " ".join(str(text or "").split())
    return text if len(text) <= length else text[: length - 1] + "…"


def tool_detail(tool_input):
    """Short summary of what the tool does (file, command, search)."""
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "notebook_path", "path"):
        if tool_input.get(key):
            return os.path.basename(str(tool_input[key]).rstrip("/"))
    for key in ("description", "command", "pattern", "query", "url", "skill", "prompt"):
        if tool_input.get(key):
            return short(tool_input[key], 40)
    return ""


def claude_pid():
    """Walks up the parent processes to Claude Code, to know when it stops."""
    pid = os.getppid()
    for _ in range(8):
        try:
            with open(f"/proc/{pid}/comm") as f:
                name = f.read().strip()
            with open(f"/proc/{pid}/stat") as f:
                parent = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return 0
        if name in ("claude", "node"):
            return pid
        if parent <= 1:
            return 0
        pid = parent
    return 0


def send(data):
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.sendto(data, SOCKET)


def start_program():
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    import subprocess

    cache = os.path.join(os.path.expanduser("~"), ".cache", APP_NAME)
    os.makedirs(cache, exist_ok=True)
    with open(os.path.join(cache, "start.log"), "ab") as logfile:
        subprocess.Popen(
            ["/usr/bin/env", "python3", os.path.join(BASE_DIR, "cats.py")],
            stdin=subprocess.DEVNULL,
            stdout=logfile,
            stderr=logfile,
            cwd=BASE_DIR,
            start_new_session=True,
        )
    return True


def session_cats_enabled():
    """Setting session_cats of config.json (false: usage cat only)."""
    try:
        with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as f:
            return json.load(f).get("session_cats", True) is not False
    except (OSError, ValueError, AttributeError):
        return True


def main():
    if not session_cats_enabled():
        return
    try:
        e = json.load(sys.stdin)
    except ValueError:
        return
    event = e.get("hook_event_name") or ""
    session = e.get("session_id") or ""
    if not event or not session:
        return
    message = {
        "ev": event,
        "sid": session,
        "cwd": e.get("cwd") or "",
        "tool": e.get("tool_name") or "",
        "detail": tool_detail(e.get("tool_input")),
        "agent_id": e.get("agent_id") or "",
        "agent_type": e.get("agent_type") or "",
        "notif": e.get("notification_type") or "",
        "message": short(e.get("message"), 80),
        "pid": claude_pid(),
    }
    data = json.dumps(message).encode()
    try:
        send(data)
        return
    except OSError:
        pass
    if event == "SessionEnd" or not start_program():
        return
    import time

    for _ in range(30):
        time.sleep(0.1)
        try:
            send(data)
            return
        except OSError:
            continue


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
