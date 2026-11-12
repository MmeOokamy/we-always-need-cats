#!/usr/bin/env python3
"""Claude Code status line command: feeds the usage cat.

Claude Code runs this script at every status line refresh and gives it, on
standard input, a JSON document that holds the rate limits of the account
(`rate_limits`: 5-hour session and 7-day windows). The script saves them for
usage_cat.py, starts that program when it is not running, and prints a short
usage summary as the status line.
"""

import fcntl
import json
import os
import sys
import time

import usage_common as common


def to_epoch(value):
    """Reset time as seconds since the epoch (Claude Code sends seconds)."""
    if isinstance(value, (int, float)):
        return value / 1000 if value > 1e11 else value
    if isinstance(value, str):
        from datetime import datetime

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


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


def program_is_running():
    """The program holds a lock for as long as it lives."""
    try:
        with open(common.LOCK, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    return False


def start_program():
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return
    import subprocess

    os.makedirs(common.CACHE, exist_ok=True)
    with open(os.path.join(common.CACHE, "start.log"), "ab") as logfile:
        subprocess.Popen(
            ["/usr/bin/env", "python3", os.path.join(common.BASE_DIR, "usage_cat.py")],
            stdin=subprocess.DEVNULL,
            stdout=logfile,
            stderr=logfile,
            cwd=common.BASE_DIR,
            start_new_session=True,
        )


def update_state(event, now):
    state = common.read_state()
    limits = event.get("rate_limits")
    if isinstance(limits, dict):
        for name in common.WINDOWS:
            data = limits.get(name)
            if isinstance(data, dict) and data.get("used_percentage") is not None:
                state[name] = {
                    "pct": float(data["used_percentage"]),
                    "resets_at": to_epoch(data.get("resets_at")),
                }
    # Without rate limits (start of a session), the last known values are kept.
    state["ts"] = now
    state["pid"] = claude_pid()
    common.write_state(state)
    return state


def status_text(state, now):
    """One line: 🐱 Session 42 % ↻ 14:00 · Semaine 12 %"""
    parts = []
    for name in common.WINDOWS:
        pct, reset = common.window(state, name, now)
        if pct is None:
            continue
        color = {"ok": 32, "warn": 33}.get(common.level_of(pct), 31)
        text = common.TEXT["status"].format(label=common.TEXT[name], pct=pct)
        if reset and name == "five_hour":
            text += f" ↻ {common.format_reset(reset, now)}"
        parts.append(f"\033[{color}m{text}\033[0m")
    return "🐱 " + (" · ".join(parts) if parts else common.TEXT["waiting"])


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    now = time.time()
    state = update_state(event, now)
    # The figures are saved in any case (other displays read them), but the
    # cat only starts when it has not been hidden (setting usage_cat).
    if common.file_setting("usage_cat") is not False and not program_is_running():
        start_program()
    if common.SETTINGS["statusline"]:
        print(status_text(state, now))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
