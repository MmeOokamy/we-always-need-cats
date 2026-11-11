#!/usr/bin/env python3
"""Installs (or removes) the Claude Code hooks that feed the desktop cats.

    python3 install.py                 install into ~/.claude/settings.json
    python3 install.py --uninstall     remove the hooks again
    python3 install.py --settings FILE use another settings file
                                       (e.g. .claude/settings.json of a project)

The settings file is copied to <name>.backup-we-always-need-cats before the
first change, and only the `hooks` entries of this project are touched.
"""

import argparse
import json
import os
import shutil
import sys

APP_NAME = "we-always-need-cats"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(BASE_DIR, "hook.py")
DEFAULT_SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")

# Events the program reacts to. A matcher is only meaningful for tool events.
EVENTS_WITH_MATCHER = ("PreToolUse", "PostToolUse", "PostToolUseFailure")
EVENTS = EVENTS_WITH_MATCHER + (
    "UserPromptSubmit",
    "Notification",
    "Stop",
    "StopFailure",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "SessionStart",
    "SessionEnd",
)


def command():
    return f'python3 "{HOOK}"'


def is_ours(entry):
    """True for a hook entry pointing at this project's hook.py."""
    if not isinstance(entry, dict):
        return False
    for hook in entry.get("hooks") or []:
        if isinstance(hook, dict) and "hook.py" in str(hook.get("command", "")):
            path = str(hook["command"])
            if HOOK in path or APP_NAME in path or "chat-bureau" in path:  # old name
                return True
    return False


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        return {}
    except ValueError as error:
        sys.exit(f"{path} is not valid JSON ({error}); fix it first.")
    if not isinstance(settings, dict):
        sys.exit(f"{path} does not hold a JSON object.")
    return settings


def save(path, settings, backup=True):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    copy = f"{path}.backup-{APP_NAME}"
    if backup and os.path.exists(path) and not os.path.exists(copy):
        shutil.copy2(path, copy)
        print("Backup:", copy)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")


def strip_ours(settings):
    """Removes this project's entries; returns how many were dropped."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    dropped = 0
    for event, entries in list(hooks.items()):
        if not isinstance(entries, list):
            continue
        kept = [e for e in entries if not is_ours(e)]
        dropped += len(entries) - len(kept)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks:
        del settings["hooks"]
    return dropped


def install(path):
    if not os.path.exists(HOOK):
        sys.exit(f"hook.py not found next to this script ({HOOK}).")
    settings = load(path)
    strip_ours(settings)
    hooks = settings.setdefault("hooks", {})
    for event in EVENTS:
        entry = {"hooks": [{"type": "command", "command": command()}]}
        if event in EVENTS_WITH_MATCHER:
            entry = {"matcher": "*", **entry}
        hooks.setdefault(event, []).append(entry)
    save(path, settings)
    print(f"{len(EVENTS)} hooks installed in {path}")
    print("The cats show up on the next Claude Code event (new session or prompt).")


def uninstall(path):
    settings = load(path)
    dropped = strip_ours(settings)
    if not dropped:
        print(f"No {APP_NAME} hook found in {path}")
        return
    save(path, settings)
    print(f"{dropped} hooks removed from {path}")


def main():
    parser = argparse.ArgumentParser(description=f"Install the {APP_NAME} hooks.")
    parser.add_argument("--uninstall", action="store_true", help="remove the hooks")
    parser.add_argument(
        "--settings", default=DEFAULT_SETTINGS, help=f"settings file (default: {DEFAULT_SETTINGS})"
    )
    args = parser.parse_args()
    path = os.path.abspath(os.path.expanduser(args.settings))
    if args.uninstall:
        uninstall(path)
    else:
        install(path)


if __name__ == "__main__":
    main()
