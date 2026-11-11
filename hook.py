#!/usr/bin/env python3
"""Claude Code hook: forwards every event to the desktop cats.

Reads the event on standard input, keeps the essentials and sends them to
cats.py over a local socket. If the program is not running, it is started.
This script writes nothing and always exits without an error, so that it never
gets in Claude Code's way.
"""

import json
import os
import sys

import compat

APP_NAME = "we-always-need-cats"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def start_program():
    if not compat.has_display():
        return False
    log = os.path.join(os.path.expanduser("~"), ".cache", APP_NAME, "start.log")
    compat.spawn_detached(os.path.join(BASE_DIR, "cats.py"), log)
    return True


def main():
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
        "pid": compat.claude_pid(),
    }
    data = json.dumps(message).encode()
    if compat.instance_running(compat.SESSION_PORT):
        compat.send(compat.SESSION_PORT, data)
        return
    if event == "SessionEnd" or not start_program():
        return
    import time

    # Wait for the program to take the port, then send it the event.
    for _ in range(50):
        time.sleep(0.1)
        if compat.instance_running(compat.SESSION_PORT):
            compat.send(compat.SESSION_PORT, data)
            return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
