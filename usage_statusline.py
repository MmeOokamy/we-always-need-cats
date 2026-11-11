#!/usr/bin/env python3
"""Claude Code status line command: feeds the usage cat.

Claude Code runs this script at every status line refresh and gives it, on
standard input, a JSON document that holds the rate limits of the account
(`rate_limits`: 5-hour session and 7-day windows). The script saves them for
usage_cat.py, starts that program when it is not running, and prints a short
usage summary as the status line.
"""

import json
import os
import sys
import time

import compat
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


def program_is_running():
    """The program holds its port for as long as it lives."""
    return compat.instance_running(common.LOCK_PORT)


def start_program():
    if not compat.has_display():
        return
    log = os.path.join(common.CACHE, "start.log")
    compat.spawn_detached(os.path.join(common.BASE_DIR, "usage_cat.py"), log)


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
    state["pid"] = compat.claude_pid()
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
    # The status line carries a 🐱 emoji; on Windows stdout defaults to cp1252
    # and would fail to encode it, so UTF-8 is forced.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    now = time.time()
    state = update_state(event, now)
    if not program_is_running():
        start_program()
    if common.SETTINGS["statusline"]:
        print(status_text(state, now))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
