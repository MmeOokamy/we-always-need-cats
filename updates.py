#!/usr/bin/env python3
"""Updates of we-always-need-cats, from the git clone it was installed with.

    python3 updates.py           check, then update if a new version is there
    python3 updates.py --check   check only

The cats use the same functions: an automatic check once a day, and an
"Updates" submenu in their right-click menu (state, what changed, check now,
update and restart).

An update never overwrites anything: it is a fast-forward of the clone. With
local changes or local commits, it stops and says so. After an update, the
running cats restart by themselves on the new version (see restart_wanted).
"""

import json
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "we-always-need-cats")
STATE = os.path.join(CACHE, "updates.json")  # result of the last check
UPDATED = os.path.join(CACHE, "updated")  # touched after an update: restart
CHECK_EVERY = 24 * 3600  # automatic check, in seconds
GIT_TIMEOUT = 30

TEXTS = {
    "fr": {
        "menu": "Mises à jour",
        "never": "Jamais vérifié",
        "checking": "Vérification…",
        "updating": "Mise à jour…",
        "up_to_date": "À jour (vérifié à {when})",
        "available": "Mise à jour disponible : {count} changement{s}",
        "failed": "Vérification impossible : {error}",
        "blocked": "Mise à jour à faire à la main : {error}",
        "check": "Vérifier les mises à jour",
        "update": "Mettre à jour et redémarrer",
        "changes": "Nouveautés",
        "bubble": "mise à jour disponible (clic droit)",
        "no_git": "installé sans git",
        "dirty": "modifications locales",
        "ahead": "commits locaux",
        "no_upstream": "pas de branche suivie",
    },
    "en": {
        "menu": "Updates",
        "never": "Never checked",
        "checking": "Checking…",
        "updating": "Updating…",
        "up_to_date": "Up to date (checked at {when})",
        "available": "Update available: {count} change{s}",
        "failed": "Check failed: {error}",
        "blocked": "Update by hand: {error}",
        "check": "Check for updates",
        "update": "Update and restart",
        "changes": "What changed",
        "bubble": "update available (right click)",
        "no_git": "installed without git",
        "dirty": "local changes",
        "ahead": "local commits",
        "no_upstream": "no tracked branch",
    },
}


def texts(lang):
    return TEXTS.get(str(lang).lower(), TEXTS["fr"])


# --- git --------------------------------------------------------------------


class UpdateError(Exception):
    """A check or an update that could not be done; the message is a text key
    of TEXTS (no_git, dirty, ahead, no_upstream) or git's own message."""


def git(*args, timeout=GIT_TIMEOUT):
    try:
        result = subprocess.run(
            ["git", "-C", BASE_DIR, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C"),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError(str(error)) from error
    if result.returncode != 0:
        lines = (result.stderr or result.stdout).strip().splitlines()
        raise UpdateError(lines[-1] if lines else f"git {args[0]} failed")
    return result.stdout.strip()


def is_clone():
    return os.path.isdir(os.path.join(BASE_DIR, ".git"))


def check():
    """Fetch the tracked branch and compare. Saves and returns the state:
    {"checked", "behind", "ahead", "dirty", "changes", "error"}."""
    state = {"checked": time.time(), "behind": 0, "ahead": 0, "dirty": False, "changes": [], "error": None}
    try:
        if not is_clone():
            raise UpdateError("no_git")
        try:
            git("rev-parse", "--abbrev-ref", "@{upstream}")
        except UpdateError:
            raise UpdateError("no_upstream") from None
        git("fetch", "--quiet")
        state["behind"] = int(git("rev-list", "--count", "HEAD..@{upstream}"))
        state["ahead"] = int(git("rev-list", "--count", "@{upstream}..HEAD"))
        # Untracked files (and config.json, ignored) do not block an update.
        state["dirty"] = bool(git("status", "--porcelain", "--untracked-files=no"))
        if state["behind"]:
            state["changes"] = git("log", "--format=%s", "HEAD..@{upstream}").splitlines()
    except UpdateError as error:
        state["error"] = str(error)
        state["checked"] = None  # a failed check is not a check: retried
    save_state(state)
    return state


def blocker(state):
    """Why an available update cannot be done from the menu, or None."""
    if state.get("dirty"):
        return "dirty"
    if state.get("ahead"):
        return "ahead"
    return None


def update():
    """Fast-forward to the tracked branch, then ask the cats to restart.
    Returns the list of changes applied."""
    state = check()
    if state["error"]:
        raise UpdateError(state["error"])
    if not state["behind"]:
        return []
    reason = blocker(state)
    if reason:
        raise UpdateError(reason)
    git("merge", "--ff-only", "--quiet", "@{upstream}")
    save_state(dict(state, behind=0, changes=[]))
    ask_restart()
    return state["changes"]


# --- Shared state -----------------------------------------------------------


def save_state(state):
    try:
        os.makedirs(CACHE, exist_ok=True)
        temporary = f"{STATE}.{os.getpid()}.tmp"
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(temporary, STATE)
    except OSError:
        pass


def read_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def check_due(state=None):
    state = read_state() if state is None else state
    return time.time() - (state.get("checked") or 0) > CHECK_EVERY


def ask_restart():
    os.makedirs(CACHE, exist_ok=True)
    with open(UPDATED, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def restart_wanted(started):
    """True when an update was made after this program started (time.time())."""
    try:
        return os.path.getmtime(UPDATED) > started
    except OSError:
        return False


def restart():
    """Replace the running program with its new version (same arguments).
    Files and sockets opened by Python are closed on exec: the lock is freed."""
    os.execv(sys.executable, [sys.executable, *sys.argv])


# --- Texts ------------------------------------------------------------------


def describe(state, lang, busy=None):
    """One line about the update state, for a menu."""
    t = texts(lang)
    if busy:
        return t[busy]
    if state.get("error"):
        error = state["error"]
        return t["failed"].format(error=t.get(error, error))
    if not state.get("checked"):
        return t["never"]
    if state.get("behind"):
        count = state["behind"]
        line = t["available"].format(count=count, s="s" if count > 1 else "")
        reason = blocker(state)
        return t["blocked"].format(error=t[reason]) if reason else line
    return t["up_to_date"].format(when=time.strftime("%H:%M", time.localtime(state["checked"])))


# --- Qt part (imported only by the cats) ------------------------------------


class Updater:
    """Checks and updates in a background thread, for a Qt program.

    Call tick() regularly (a QTimer): it starts the daily check, and restarts
    the program after an update (made here, from the other cat, or by hand
    with updates.py)."""

    def __init__(self, lang):
        self.lang = lang
        self.started = time.time()
        self.busy = None  # "checking" or "updating"
        self.thread = None
        self.state = read_state()

    def available(self):
        return bool(self.state.get("behind")) and not blocker(self.state) and not self.state.get("error")

    def run(self, work, busy):
        import threading

        if self.thread and self.thread.is_alive():
            return
        self.busy = busy

        def target():
            try:
                work()
            except UpdateError:
                pass
            finally:
                self.state = read_state()
                self.busy = None

        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()

    def check(self):
        self.run(check, "checking")

    def update(self):
        self.run(update, "updating")

    def tick(self):
        """Returns True when the program should restart (then quit it and
        call restart() once Qt has finished)."""
        if self.busy is None:
            self.state = read_state()
            if check_due(self.state):
                self.check()
        return restart_wanted(self.started)

    def add_menu(self, menu):
        """The Updates submenu: state, what changed, check, update."""
        t = texts(self.lang)
        sub = menu.addMenu(t["menu"])
        line = sub.addAction(describe(self.state, self.lang, self.busy))
        line.setEnabled(False)
        changes = self.state.get("changes") or []
        if changes and not self.busy:
            news = sub.addMenu(t["changes"])
            for change in changes[:12]:
                item = news.addAction(change)
                item.setEnabled(False)
            if len(changes) > 12:
                more = news.addAction(f"… (+{len(changes) - 12})")
                more.setEnabled(False)
        sub.addSeparator()
        check_action = sub.addAction(t["check"], self.check)
        check_action.setEnabled(self.busy is None)
        update_action = sub.addAction(t["update"], self.update)
        update_action.setEnabled(self.busy is None and self.available())
        return sub


def main():
    lang = "fr"
    try:
        import usage_common

        lang = usage_common.SETTINGS["lang"]
    except Exception:
        pass
    t = texts(lang)
    state = check()
    print(describe(state, lang))
    for change in state["changes"]:
        print(f"  - {change}")
    if "--check" in sys.argv or state["error"] or not state["behind"] or blocker(state):
        return 1 if state["error"] else 0
    try:
        update()
    except UpdateError as error:
        print(t["failed"].format(error=t.get(str(error), str(error))))
        return 1
    print(texts(lang)["up_to_date"].format(when=time.strftime("%H:%M")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
