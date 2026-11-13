#!/usr/bin/env python3
"""Updates of we-always-need-cats, from the git clone it was installed with.

    python3 updates.py           check, then update if a new version is there
    python3 updates.py --check   check only

The cats use the same functions: an automatic check once a day, and an
"Updates" submenu in their right-click menu (state, what changed, check now,
update and restart).

The Windows cats have their own releases, tagged win-vX.Y.Z on the windows
branch (which carries the Windows-specific code), kept apart from the vX.Y.Z
releases of main. Only these Windows releases are offered, not every change
pushed to the branch between two of them.

An update never overwrites anything: it is a fast-forward of the clone to the
latest Windows release. With local changes or local commits, it stops and says
so. After an update, the running cats restart by themselves on the new version
(see restart_wanted).
"""

import json
import os
import re
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "we-always-need-cats")
STATE = os.path.join(CACHE, "updates.json")  # result of the last check
UPDATED = os.path.join(CACHE, "updated")  # touched after an update: restart
CHECK_EVERY = 24 * 3600  # automatic check, in seconds
GIT_TIMEOUT = 30
RELEASE = re.compile(r"^win-v(\d+)\.(\d+)\.(\d+)$")  # Windows release tags: win-v1.2.3
TAG_GLOB = "win-v[0-9]*.[0-9]*.[0-9]*"  # the same, as a git describe/tag pattern
# On Windows, keep git from flashing a console window at every call.
_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0  # CREATE_NO_WINDOW


def version_name(tag):
    """Human version from a release tag: 'win-v1.2.3' -> '1.2.3'."""
    match = RELEASE.match(tag or "")
    return ".".join(match.groups()) if match else (tag or "")

TEXTS = {
    "fr": {
        "menu": "Mises à jour",
        "never": "Jamais vérifié",
        "checking": "Vérification…",
        "updating": "Mise à jour…",
        "version": "Version {version}",
        "dev_version": "Version de développement",
        "up_to_date": "À jour (vérifié à {when})",
        "no_release": "Aucune version publiée (vérifié à {when})",
        "available": "Version {latest} disponible : {count} changement{s}",
        "failed": "Vérification impossible : {error}",
        "blocked": "Mise à jour à faire à la main : {error}",
        "check": "Vérifier les mises à jour",
        "update": "Mettre à jour et redémarrer",
        "changes": "Nouveautés",
        "bubble": "mise à jour disponible (clic droit)",
        "no_git": "installé sans git",
        "dirty": "modifications locales",
        "ahead": "commits locaux",
    },
    "en": {
        "menu": "Updates",
        "never": "Never checked",
        "checking": "Checking…",
        "updating": "Updating…",
        "version": "Version {version}",
        "dev_version": "Development version",
        "up_to_date": "Up to date (checked at {when})",
        "no_release": "No release yet (checked at {when})",
        "available": "Version {latest} available: {count} change{s}",
        "failed": "Check failed: {error}",
        "blocked": "Update by hand: {error}",
        "check": "Check for updates",
        "update": "Update and restart",
        "changes": "What changed",
        "bubble": "update available (right click)",
        "no_git": "installed without git",
        "dirty": "local changes",
        "ahead": "local commits",
    },
}


def texts(lang):
    return TEXTS.get(str(lang).lower(), TEXTS["fr"])


# --- git --------------------------------------------------------------------


class UpdateError(Exception):
    """A check or an update that could not be done; the message is a text key
    of TEXTS (no_git, dirty, ahead) or git's own message."""


def git(*args, timeout=GIT_TIMEOUT):
    try:
        result = subprocess.run(
            ["git", "-C", BASE_DIR, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C"),
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError(str(error)) from error
    if result.returncode != 0:
        lines = (result.stderr or result.stdout).strip().splitlines()
        raise UpdateError(lines[-1] if lines else f"git {args[0]} failed")
    return result.stdout.strip()


def is_clone():
    return os.path.isdir(os.path.join(BASE_DIR, ".git"))


def releases():
    """Windows release tags known to the clone, newest first (win-vX.Y.Z)."""
    tags = [t for t in git("tag", "--list", "win-v*").splitlines() if RELEASE.match(t)]
    return sorted(tags, key=lambda t: tuple(int(n) for n in RELEASE.match(t).groups()), reverse=True)


def installed_version():
    """(Windows release the clone is on or after, commits since it):
    ("win-v1.2.3", 0), or (None, 0) before any release."""
    try:
        described = git("describe", "--tags", "--long", "--match", TAG_GLOB)
    except UpdateError:
        return None, 0
    tag, since, _hash = described.rsplit("-", 2)
    return tag, int(since)


def check():
    """Fetch the releases and compare. Saves and returns the state:
    {"checked", "version", "latest", "behind", "ahead", "dirty", "changes",
    "error"}; behind counts the commits up to the latest release."""
    state = {
        "checked": time.time(),
        "version": None,
        "since": 0,
        "latest": None,
        "behind": 0,
        "ahead": 0,
        "dirty": False,
        "changes": [],
        "error": None,
    }
    try:
        if not is_clone():
            raise UpdateError("no_git")
        git("fetch", "--quiet", "--tags", "--force")
        state["version"], state["since"] = installed_version()
        tags = releases()
        if tags:
            latest = state["latest"] = tags[0]
            state["behind"] = int(git("rev-list", "--count", f"HEAD..{latest}"))
            if state["behind"]:
                state["changes"] = git("log", "--no-merges", "--format=%s", f"HEAD..{latest}").splitlines()
        # Local commits GitHub does not have: they block a fast-forward.
        state["ahead"] = int(git("rev-list", "--count", "HEAD", "--not", "--remotes"))
        # Untracked files (and config.json, ignored) do not block an update.
        state["dirty"] = bool(git("status", "--porcelain", "--untracked-files=no"))
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
    """Fast-forward to the latest release, then ask the cats to restart.
    Returns the list of changes applied."""
    state = check()
    if state["error"]:
        raise UpdateError(state["error"])
    if not state["behind"]:
        return []
    reason = blocker(state)
    if reason:
        raise UpdateError(reason)
    git("merge", "--ff-only", "--quiet", state["latest"])
    version, since = installed_version()
    save_state(dict(state, version=version, since=since, behind=0, changes=[]))
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
        count = len(state.get("changes") or []) or state["behind"]
        line = t["available"].format(
            latest=version_name(state.get("latest")), count=count, s="s" if count > 1 else ""
        )
        reason = blocker(state)
        return t["blocked"].format(error=t[reason]) if reason else line
    when = time.strftime("%H:%M", time.localtime(state["checked"]))
    return t["up_to_date" if state.get("latest") else "no_release"].format(when=when)


def describe_version(state, lang):
    """The installed version, for a menu."""
    t = texts(lang)
    version = state.get("version")
    if not version:
        return t["dev_version"]
    # "+": past that release (branch pulled by hand beyond the tag)
    return t["version"].format(version=version_name(version) + ("+" if state.get("since") else ""))


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
        for text in (describe_version(self.state, self.lang), describe(self.state, self.lang, self.busy)):
            line = sub.addAction(text)
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
    print(describe_version(state, lang))
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
    print(describe(read_state(), lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
