"""Shared by the status line script and the desktop cat: paths, settings, texts.

This module must stay light (no Qt import): the status line script loads it on
every refresh.
"""

import json
import os
import time

# The demo uses its own files, so that it never touches the real usage data.
APP_NAME = "usage-cat" + ("-demo" if os.environ.get("USAGE_CAT_DEMO") else "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
LOCK = os.path.join(RUNTIME, f"{APP_NAME}.lock")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", APP_NAME)
STATE = os.path.join(CACHE, "state.json")
POSITION = os.path.join(CACHE, "position.json")

# --- Settings (overridable in config.json, next to this file; the file is
# shared with cats.py, which reads its own keys) ----------------------------

SETTINGS = {
    "scale": 4,  # size of one drawing pixel, in screen pixels
    "lang": "fr",  # language of the bubble and of the status line: fr or en
    "coat": "ginger",  # ginger, grey, black, cream, brown or blue
    "warn": 50,  # usage (%) from which the gauge turns yellow
    "alert": 80,  # usage (%) from which the cat meows
    "critical": 95,  # usage (%) from which the cat panics
    "notify_seconds": 12,  # how long the bubble stays up when a threshold is crossed
    "keep_alive": False,  # keep the cat on screen after the last Claude Code session ends
    "statusline": True,  # also print the usage in the Claude Code status line
}
try:
    with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as _f:
        SETTINGS.update(json.load(_f))
except (OSError, ValueError):
    pass

# Rate limit windows reported by Claude Code, as named in its status line data.
WINDOWS = ("five_hour", "seven_day")

# Levels, from the calmest to the worst.
LEVELS = ("none", "ok", "warn", "alert", "critical", "full")
LEVEL_COLOR = {
    "none": "#868E96",
    "ok": "#2F9E44",
    "warn": "#F2B01E",
    "alert": "#E8590C",
    "critical": "#E03131",
    "full": "#E03131",
}

_TEXTS = {
    "fr": {
        "title": "Usage Claude Code",
        "renewed_title": "Session rechargée !",
        "five_hour": "Session",
        "seven_day": "Semaine",
        "line": "{label} : {pct} % · reset {when} ({delay})",
        "full": "{label} : épuisée · reprise {when} ({delay})",
        "renewed": "{label} : 0 % (réinitialisée)",
        "delay": "dans {delay}",
        "waiting": "en attente de Claude Code…",
        "days": ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."],
        "day_unit": "j",
        "status": "{label} {pct} %",
        "menu_home": "Remettre le chat à sa place",
        "menu_quit": "Quitter usage-cat",
    },
    "en": {
        "title": "Claude Code usage",
        "renewed_title": "Session refilled!",
        "five_hour": "Session",
        "seven_day": "Week",
        "line": "{label}: {pct}% · resets {when} ({delay})",
        "full": "{label}: limit reached · back {when} ({delay})",
        "renewed": "{label}: 0% (reset)",
        "delay": "in {delay}",
        "waiting": "waiting for Claude Code…",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "day_unit": "d",
        "status": "{label} {pct}%",
        "menu_home": "Send the cat home",
        "menu_quit": "Quit usage-cat",
    },
}
TEXT = _TEXTS.get(str(SETTINGS["lang"]).lower(), _TEXTS["fr"])


# --- Usage data -------------------------------------------------------------


def read_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def write_state(state):
    os.makedirs(CACHE, exist_ok=True)
    temporary = f"{STATE}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(temporary, STATE)


def window(state, name, now):
    """(used percentage, reset time) of a rate limit window.

    Returns (None, None) when nothing is known. A window whose reset time has
    passed is empty again, whatever the last value received: (0, None).
    """
    data = state.get(name)
    if not isinstance(data, dict) or data.get("pct") is None:
        return None, None
    reset = data.get("resets_at")
    if reset and now >= reset:
        return 0, None
    return min(100, max(0, int(data["pct"]))), reset


def level_of(pct):
    if pct is None:
        return "none"
    if pct >= 100:
        return "full"
    for name in ("critical", "alert", "warn"):
        if pct >= SETTINGS[name]:
            return name
    return "ok"


def worst_level(state, now):
    """Level of the most used window."""
    levels = [level_of(window(state, name, now)[0]) for name in WINDOWS]
    return max(levels, key=LEVELS.index)


# --- Texts ------------------------------------------------------------------


def format_reset(reset, now):
    """Clock time of a reset, with the day when it is not today."""
    then, today = time.localtime(reset), time.localtime(now)
    clock = time.strftime("%H:%M", then)
    if (then.tm_year, then.tm_yday) == (today.tm_year, today.tm_yday):
        return clock
    return f"{TEXT['days'][then.tm_wday]} {clock}"


def format_delay(seconds):
    minutes = max(1, int(seconds // 60))
    if minutes < 60:
        duration = f"{minutes} min"
    elif minutes < 48 * 60:
        duration = f"{minutes // 60} h {minutes % 60:02d}"
    else:
        duration = f"{minutes // (24 * 60)} {TEXT['day_unit']}"
    return TEXT["delay"].format(delay=duration)


def window_line(state, name, now):
    """Sentence describing one window, or None when nothing is known about it."""
    pct, reset = window(state, name, now)
    if pct is None:
        return None
    label = TEXT[name]
    if reset is None:
        return TEXT["renewed"].format(label=label)
    template = TEXT["full"] if pct >= 100 else TEXT["line"]
    return template.format(
        label=label,
        pct=pct,
        when=format_reset(reset, now),
        delay=format_delay(reset - now),
    )


def window_lines(state, now):
    lines = [window_line(state, name, now) for name in WINDOWS]
    return [line for line in lines if line] or [TEXT["waiting"]]
