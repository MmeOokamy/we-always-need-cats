#!/usr/bin/env python3
"""Installs (or removes) what feeds the desktop cats in Claude Code.

Two things are registered: the hooks, for the session cats (hook.py), and the
status line, for the usage cat (usage_statusline.py).

    python3 install.py                 install into ~/.claude/settings.json
    python3 install.py --uninstall     remove the hooks and the status line again
    python3 install.py --settings FILE use another settings file
                                       (e.g. .claude/settings.json of a project)
    python3 install.py --no-usage      session cats only, no usage cat
    python3 install.py --force         replace a status line that is already set

The settings file is copied to <name>.backup-we-always-need-cats before the
first change, and only the `hooks` entries and the `statusLine` entry of this
project are touched.
"""

import argparse
import json
import os
import shutil
import sys

APP_NAME = "we-always-need-cats"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(BASE_DIR, "hook.py")
STATUS_LINE = os.path.join(BASE_DIR, "usage_statusline.py")
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


def interpreter():
    """How to run a script in a hook command, per platform.

    On Windows `python3` does not exist (it opens the Microsoft Store), so the
    current interpreter is used, preferring pythonw.exe to avoid a console flash.
    """
    if not sys.platform.startswith("win"):
        return "python3"
    executable = sys.executable
    pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
    if os.path.exists(pythonw):
        executable = pythonw
    return f'"{executable}"'


def command():
    return f'{interpreter()} "{HOOK}"'


def is_ours(entry):
    """True for a hook entry pointing at this project's hook.py.

    The script path may sit in `command` (python3 "…/hook.py") or in `args`
    (pythonw.exe + ["…/hook.py"]), so both are scanned; "chat-bureau" is the
    old name, matched so that an earlier install is migrated cleanly.
    """
    if not isinstance(entry, dict):
        return False
    for hook in entry.get("hooks") or []:
        if not isinstance(hook, dict):
            continue
        path = " ".join([str(hook.get("command", ""))] + [str(a) for a in hook.get("args") or []])
        if "hook.py" in path and (HOOK in path or APP_NAME in path or "chat-bureau" in path):
            return True
    return False


def is_our_status_line(status_line):
    """True for a status line pointing at this project's usage_statusline.py."""
    if not isinstance(status_line, dict):
        return False
    path = str(status_line.get("command", ""))
    # Second form: the usage cat when it was a separate tool.
    return "usage_statusline.py" in path or ("usage-cat" in path and "statusline.py" in path)


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


def install_status_line(settings, force):
    """Registers the usage cat; returns the message to print."""
    current = settings.get("statusLine")
    if current and not is_our_status_line(current) and not force:
        return (
            "Usage cat not installed: a status line is already set "
            f"({json.dumps(current, ensure_ascii=False)}).\n"
            "Run again with --force to replace it."
        )
    settings["statusLine"] = {"type": "command", "command": f'{interpreter()} "{STATUS_LINE}"'}
    return "Status line installed: the usage cat shows up at its next refresh."


def install(path, usage=True, force=False):
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
    usage_message = install_status_line(settings, force) if usage else ""
    save(path, settings)
    print(f"{len(EVENTS)} hooks installed in {path}")
    print("The cats show up on the next Claude Code event (new session or prompt).")
    if usage_message:
        print(usage_message)


def uninstall(path):
    settings = load(path)
    dropped = strip_ours(settings)
    status_line = is_our_status_line(settings.get("statusLine"))
    if status_line:
        del settings["statusLine"]
    if not dropped and not status_line:
        print(f"No {APP_NAME} hook or status line found in {path}")
        return
    save(path, settings)
    print(f"{dropped} hooks removed from {path}")
    if status_line:
        print(f"Status line removed from {path}")


def main():
    parser = argparse.ArgumentParser(description=f"Install the {APP_NAME} hooks and status line.")
    parser.add_argument(
        "--uninstall", action="store_true", help="remove the hooks and the status line"
    )
    parser.add_argument(
        "--no-usage", action="store_true", help="do not install the usage cat (status line)"
    )
    parser.add_argument("--force", action="store_true", help="replace an existing status line")
    parser.add_argument(
        "--settings", default=DEFAULT_SETTINGS, help=f"settings file (default: {DEFAULT_SETTINGS})"
    )
    args = parser.parse_args()
    path = os.path.abspath(os.path.expanduser(args.settings))
    if args.uninstall:
        uninstall(path)
    else:
        install(path, usage=not args.no_usage, force=args.force)


if __name__ == "__main__":
    main()
