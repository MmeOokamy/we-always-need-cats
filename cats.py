#!/usr/bin/env python3
"""we-always-need-cats: one pixel art cat per Claude Code session.

The program stays above every other window and receives Claude Code events
(sent by hook.py) over a local socket. Each session gets its own cat; each
running subagent gets a kitten.

Normal start: automatic, from hook.py, on the first event.
Manual start: python3 cats.py
"""

import os
import sys

# Under Wayland, only an X11 window (XWayland) can place itself freely and stay
# above the others, so that mode is forced before Qt is loaded.
if os.environ.get("DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

import fcntl
import json
import math
import signal
import socket
import time
import zlib

from PyQt6.QtCore import QObject, QPoint, QPointF, QRect, QSocketNotifier, Qt, QTimer, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusInterface
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
    QPolygon,
    QRegion,
)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

import sprites
import usage_common

APP_NAME = "we-always-need-cats"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
SOCKET = os.path.join(RUNTIME, f"{APP_NAME}.sock")
LOCK = os.path.join(RUNTIME, f"{APP_NAME}.lock")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", APP_NAME)
KWIN_SCRIPT = f"{APP_NAME}-cursor"
DBUS_SERVICE = "org.weneedcats"
DBUS_PATH = "/Cursor"
DBUS_INTERFACE = "org.weneedcats.Cursor"

# --- Settings (overridable in config.json, next to this file) ---------------

SETTINGS = {
    "scale": 4,  # size of one drawing pixel, in screen pixels
    "follow_mouse": True,  # default of the two settings below
    "follow_on_question": None,  # follow the mouse when Claude needs you (None: follow_mouse)
    "follow_on_done": None,  # follow the mouse when a task is finished (None: follow_mouse)
    "follow_after_done": 30,  # seconds spent following the mouse after a finished task
    "sleep_delay": 180,  # seconds of idling before the cat falls asleep
    "speed": 800,  # running speed, in pixels per second
    "log": False,  # write received events to ~/.cache/we-always-need-cats/cats.log
}
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
try:
    with open(CONFIG_FILE, encoding="utf-8") as _f:
        SETTINGS.update(json.load(_f))
except (OSError, ValueError):
    pass
for _key in ("follow_on_question", "follow_on_done"):
    if SETTINGS[_key] is None:
        SETTINGS[_key] = bool(SETTINGS["follow_mouse"])

# Cat state -> setting deciding whether the cat follows the mouse in that state.
FOLLOW_SETTING = {"question": "follow_on_question", "done": "follow_on_done"}


def save_setting(key, value):
    """Change one setting and write it to config.json, keeping the other values
    (the file is shared with the usage cat)."""
    SETTINGS[key] = value
    try:
        usage_common.save_setting(key, value)
    except OSError as error:
        log("settings not saved:", error)

S = max(1, int(SETTINGS["scale"]))  # cat scale
S2 = max(1, S // 2)  # kitten scale
CAT_W, CAT_H = sprites.CELL_W * S, sprites.CELL_H * S
KITTEN_W, KITTEN_H = sprites.CELL_W * S2 + 2, sprites.CELL_H * S2
# Kittens sit on the right of the cat, in rows of KITTEN_COLUMNS, up to
# KITTEN_ROWS rows stacked a little over each other. With more kittens than
# that, they squeeze together on their rows: every subagent keeps its kitten.
KITTEN_COLUMNS = 3
KITTEN_ROWS = 3
KITTEN_ROW_STEP = KITTEN_H * 5 // 6
SYMBOLS_H = 7 * S
BUBBLE_H = 64
WIDTH = CAT_W + 4 + KITTEN_COLUMNS * KITTEN_W
HEIGHT = BUBBLE_H + SYMBOLS_H + CAT_H
CAT_TOP = HEIGHT - CAT_H



def kitten_places(count):
    """(index, x, row) of each kitten: rows filled from the bottom, left to
    right; past KITTEN_ROWS full rows, more columns, closer together."""
    if not count:
        return []
    rows = min(KITTEN_ROWS, -(-count // KITTEN_COLUMNS))
    columns = max(KITTEN_COLUMNS, -(-count // rows))
    room = KITTEN_COLUMNS * KITTEN_W - KITTEN_W  # left edge of the last column
    step = min(KITTEN_W, room / (columns - 1)) if columns > 1 else 0
    return [
        (i, CAT_W + 4 + int((i % columns) * step), i // columns)
        for i in range(count)
    ]


# Frames per second of each animation.
FPS = {"idle": 3, "question": 3, "done": 4, "work": 4, "think": 5, "run": 9, "sleep": 1.5}

# While thinking, the cat alternates between crepes and its laptop: two crepe
# flips, then the laptop for as long, and so on. Successive thinking periods
# start one way, then the other.
THINK_PERIOD = 2 * len(sprites.ANIMATIONS["think"]) / FPS["think"]  # seconds

BUBBLE_COLOR = {"question": "#E8590C", "done": "#2F9E44"}


def log(*parts):
    if not SETTINGS["log"]:
        return
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(os.path.join(CACHE, "cats.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + " ".join(str(p) for p in parts) + "\n")
    except OSError:
        pass


def pick(items, key):
    """Stable choice of one item of the list from a text key."""
    return items[zlib.crc32(key.encode()) % len(items)]


_pixmaps = {}


def pixmap(name, coat, activity, mirror, scale):
    key = (name, coat["name"], activity, mirror, scale)
    if key not in _pixmaps:
        image = sprites.draw(sprites.IMAGES[name], sprites.palette(coat, activity), mirror)
        _pixmaps[key] = QPixmap.fromImage(
            image.scaled(image.width() * scale, image.height() * scale)
        )
    return _pixmaps[key]


def new_kitten(agent_type, number):
    """A kitten that starts thinking. number shifts its crepes/laptop turns, so
    that neighbouring kittens do not toss their crepes all at once."""
    return {
        "type": agent_type,
        "activity": "think",
        "think_since": time.monotonic(),
        "think_count": number,
    }


def set_kitten_activity(kitten, activity):
    if activity == "think" and kitten["activity"] != "think":
        kitten["think_count"] += 1
        kitten["think_since"] = time.monotonic()
    kitten["activity"] = activity


def kitten_frame(kitten, number, now):
    """(sprite, crepe in the air or None) of a kitten: like the cat, a thinking
    kitten swaps its laptop for a frying pan now and then."""
    if kitten["activity"] == "think":
        elapsed = now - kitten["think_since"]
        if (kitten["think_count"] + int(elapsed / THINK_PERIOD)) % 2 == 1:
            frames = sprites.ANIMATIONS["think"]
            index = int(elapsed * FPS["think"])
            return frames[index % len(frames)], sprites.CREPE_FLIGHT[index % len(sprites.CREPE_FLIGHT)]
    frames = sprites.ANIMATIONS["work"]
    return frames[(int(now * FPS["work"]) + number) % len(frames)], None


def describe_tool(tool, detail):
    """Bubble text and activity (screen color) for a tool."""
    if tool in ("Edit", "Write", "NotebookEdit"):
        return f"writing {detail}".strip(), "write"
    if tool == "Read":
        return f"reading {detail}".strip(), "read"
    if tool in ("Grep", "Glob", "ToolSearch"):
        return f"searching {detail}".strip(), "read"
    if tool == "Bash":
        return f"running: {detail}" if detail else "running a command", "shell"
    if tool in ("Agent", "Task", "Workflow"):
        return "delegating to an agent", "agent"
    if tool in ("WebSearch", "WebFetch"):
        return "browsing the web", "web"
    if tool == "Skill":
        return f"loading {detail}".strip(), "think"
    if tool.startswith("mcp__"):
        parts = tool.split("__")
        return f"using {parts[1] if len(parts) > 1 else 'a service'}", "web"
    return f"using {tool}" if tool else "working", "think"


class Cat(QWidget):
    """Window of one cat: one Claude Code session."""

    def __init__(self, app, session, rank, coat):
        super().__init__()
        self.app = app
        self.session = session
        self.rank = rank
        self.coat = coat
        self.project = ""
        self.pid = 0
        self.state = "idle"  # idle, sleep, work, question, done
        self.text = ""
        self.activity = "think"
        self.kittens = {}  # agent id -> {"type", "activity"}
        self.since = time.monotonic()
        self.think_count = 0  # thinking periods so far (crepes or laptop first)
        self.think_since = self.since  # start of the current thinking period
        self.seen = time.monotonic()
        self.follows = False  # follows the mouse
        self.running = False
        self.mirror = False
        self.home = None  # hand-picked position, otherwise the default spot
        self.area = None  # screen area holding the default spot
        self.hovered = False
        self.grab = None
        self.dragged = False
        self.signature = None

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.X11BypassWindowManagerHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(WIDTH, HEIGHT)
        self.font_body = QFont()
        self.font_body.setPixelSize(12)
        self.font_title = QFont(self.font_body)
        self.font_title.setBold(True)

        start = self.home_position()
        self.px, self.py = start.x(), start.y()
        self.move(int(self.px), int(self.py))
        self.refresh(force=True)
        self.show()

    # --- State --------------------------------------------------------------

    def set_state(self, state, text="", activity="think"):
        thinking = state == "work" and activity == "think"
        if thinking and not self.thinking():
            self.think_count += 1
            self.think_since = time.monotonic()
        if state != self.state:
            self.since = time.monotonic()
            setting = FOLLOW_SETTING.get(state)
            self.follows = bool(setting and SETTINGS[setting])
        self.state, self.text, self.activity = state, text, activity

    def thinking(self):
        return self.state == "work" and self.activity == "think"

    def flipping_crepes(self):
        """While thinking: crepes or laptop, alternately (see THINK_PERIOD)."""
        turns = int((time.monotonic() - self.think_since) / THINK_PERIOD)
        return (self.think_count + turns) % 2 == 1

    def acknowledge(self):
        """Click on the cat: it stops following the mouse and goes back home."""
        self.follows = False
        if self.state == "done":
            self.set_state("idle")

    # --- Position -----------------------------------------------------------

    def home_position(self):
        if self.home is not None:
            return self.home
        if self.area is None:
            # The screen kept is the one active when the cat shows up.
            if not self.app.kwin_area and time.monotonic() - self.since < 1:
                area = self.app.usable_area()
                return QPointF(area.right() - 16 - (self.rank + 1) * WIDTH, area.bottom() - 4 - HEIGHT)
            self.area = self.app.usable_area()
        return QPointF(
            self.area.right() - 16 - (self.rank + 1) * WIDTH,
            self.area.bottom() - 4 - HEIGHT,
        )

    def target(self):
        if self.follows:
            mouse = self.app.mouse()
            order = self.app.follower_order(self)
            lines = self.bubble_lines()
            top = self.bubble_rect(lines).top() if lines else CAT_TOP
            x = mouse.x() + 18 + order * (CAT_W + 10)
            y = mouse.y() + 18 - top
            whole = QGuiApplication.primaryScreen().virtualGeometry()
            x = min(max(x, whole.left()), whole.right() - WIDTH)
            y = min(max(y, whole.top() - CAT_TOP), whole.bottom() - HEIGHT)
            return QPointF(x, y)
        return self.home_position()

    def advance(self, dt):
        if self.grab is not None:
            return
        target = self.target()
        dx, dy = target.x() - self.px, target.y() - self.py
        distance = math.hypot(dx, dy)
        if not self.running:
            # While following, the cat only sets off if the mouse really moved away.
            if distance > (70 if self.follows else 3):
                self.running = True
        if self.running:
            step = SETTINGS["speed"] * dt
            if distance <= max(step, 3):
                self.px, self.py = target.x(), target.y()
                self.running = False
            else:
                self.px += dx / distance * step
                self.py += dy / distance * step
                if abs(dx) > 2:
                    self.mirror = dx < 0
            self.move(int(self.px), int(self.py))

    # --- Drawing ------------------------------------------------------------

    def animation(self):
        if self.running:
            return "run"
        if self.thinking() and self.flipping_crepes():
            return "think"  # thinking: the cat flips a crepe (or types, alternately)
        return self.state

    def bubble_lines(self):
        """Text lines of the bubble, or an empty list when there is nothing to say."""
        if self.running and self.state in ("idle", "sleep"):
            return []
        if self.state in ("idle", "sleep") and not self.hovered:
            return []
        label = {"idle": "idle", "sleep": "asleep"}.get(self.state, self.text)
        lines = [self.project or "Claude Code", label]
        if self.kittens:
            types = sorted({k["type"] or "agent" for k in self.kittens.values()})
            count = len(self.kittens)
            lines.append(f"{count} agent{'s' if count > 1 else ''}: {', '.join(types)}")
        return lines

    def bubble_rect(self, lines):
        title_metrics = QFontMetrics(self.font_title)
        metrics = QFontMetrics(self.font_body)
        width = max(
            [title_metrics.horizontalAdvance(lines[0])]
            + [metrics.horizontalAdvance(line) for line in lines[1:]]
        )
        width = min(width + 16, WIDTH - 2)
        height = 8 + 16 * len(lines)
        return QRect(1, BUBBLE_H - 8 - height, width, height)

    def refresh(self, force=False):
        """Redraw the window when what it shows has changed."""
        animation = self.animation()
        frames = sprites.ANIMATIONS[animation]
        if animation == "think":
            # Counted from the start of the thinking period: every series of
            # crepes starts with a throw, never in the middle of a flight.
            index = int((time.monotonic() - self.think_since) * FPS[animation])
        else:
            index = int(time.monotonic() * FPS[animation])
        lines = self.bubble_lines()
        now = time.monotonic()
        signature = (
            animation,
            index,
            self.mirror,
            self.activity,
            tuple(lines),
            tuple(
                (k["type"], k["activity"], kitten_frame(k, i, now))
                for i, k in enumerate(self.kittens.values())
            ),
        )
        if signature == self.signature and not force:
            return
        self.signature = signature
        self.image = frames[index % len(frames)]
        self.index = index
        self.lines = lines
        # The window is drawn into a buffer, then masked with that drawing:
        # clicks pass through everything that is transparent.
        buffer = QPixmap(WIDTH, HEIGHT)
        buffer.fill(Qt.GlobalColor.transparent)
        painter = QPainter(buffer)
        self.paint(painter)
        painter.end()
        self.buffer = buffer
        self.setMask(QRegion(buffer.mask()))
        self.update()

    def draw_symbol(self, painter, name, x, y, color, scale):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        for j, line in enumerate(sprites.SYMBOLS[name]):
            for i, char in enumerate(line):
                if char == "K":
                    painter.drawRect(x + i * scale, y + j * scale, scale, scale)

    def paintEvent(self, _event):
        QPainter(self).drawPixmap(0, 0, self.buffer)

    def paint(self, painter):
        animation = self.animation()
        even = self.index % 2 == 0

        # The cat
        image = pixmap(self.image, self.coat, self.activity, self.mirror, S)
        jump = 2 * S if (animation == "done" and even) else 0
        x = (CAT_W - image.width()) // 2
        y = HEIGHT - image.height() - jump
        painter.drawPixmap(x, y, image)

        # The flying crepe (thinking)
        if animation == "think":
            flight = sprites.CREPE_FLIGHT[self.index % len(sprites.CREPE_FLIGHT)]
            if flight:
                name, column, line, flipped = flight
                width = len(sprites.IMAGES[name][0])
                if self.mirror:  # the cat looks the other way
                    column = (image.width() // S - 2) - column - width
                    flipped = not flipped
                crepe = pixmap(name, self.coat, self.activity, flipped, S)
                painter.drawPixmap(x + column * S, y + line * S, crepe)

        # The symbols above the cat
        top = CAT_TOP
        if animation == "sleep":
            self.draw_symbol(painter, "z", CAT_W - 5 * S, top + (3 if even else 2) * S, "#FFFFFF", S2)
            if even:
                self.draw_symbol(painter, "z", CAT_W - 2 * S, top - S, "#FFFFFF", S2)
        elif animation == "question":
            self.draw_symbol(painter, "?", CAT_W - 4 * S, top - (6 if even else 5) * S, "#E8590C", S)
        elif animation == "done":
            for i, (sx, sy) in enumerate(((1, -4), (15, -6), (9, -7))):
                if (self.index + i) % 3:
                    self.draw_symbol(painter, "star", sx * S, top + sy * S + jump // 2, "#FFD43B", S)
        elif animation == "work":
            color = sprites.SCREENS.get(self.activity, sprites.SCREENS["think"])
            for i in range(3):
                phase = (self.index + i * 2) % 6
                if phase < 5:
                    self.draw_symbol(painter, "!", (6 + i * 3) * S, top - phase * S, color, S2)

        # The kittens (one per running subagent), back rows first so that the
        # front ones sit over them
        kittens = list(self.kittens.values())
        now = time.monotonic()
        for i, x, row in reversed(kitten_places(len(kittens))):
            kitten = kittens[i]
            coat = pick(sprites.KITTEN_COATS, kitten["type"] or "agent")
            name, flight = kitten_frame(kitten, i, now)
            small = pixmap(name, coat, kitten["activity"], False, S2)
            y = HEIGHT - small.height() - row * KITTEN_ROW_STEP
            painter.drawPixmap(x, y, small)
            if flight:  # the kitten's crepe, in the air
                crepe, column, line, flipped = flight
                crepe = pixmap(crepe, coat, kitten["activity"], flipped, S2)
                painter.drawPixmap(x + column * S2, y + line * S2, crepe)

        # The bubble
        if self.lines:
            rect = self.bubble_rect(self.lines)
            border = QColor(BUBBLE_COLOR.get(self.state, sprites.OUTLINE))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(border, 2))
            painter.setBrush(QColor("#FFFDF5"))
            painter.drawRoundedRect(rect, 7, 7)
            bottom = rect.bottom()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(
                QPolygon([QPoint(18, bottom), QPoint(30, bottom), QPoint(22, bottom + 8)])
            )
            painter.setPen(QPen(border, 2))
            painter.drawLine(18, bottom + 1, 22, bottom + 8)
            painter.drawLine(22, bottom + 8, 30, bottom + 1)
            painter.setPen(QColor(sprites.OUTLINE))
            for i, line in enumerate(self.lines):
                font = self.font_title if i == 0 else self.font_body
                painter.setFont(font)
                text = QFontMetrics(font).elidedText(
                    line, Qt.TextElideMode.ElideRight, rect.width() - 14
                )
                painter.drawText(rect.left() + 8, rect.top() + 17 + 16 * i, text)

    # --- Mouse --------------------------------------------------------------

    def enterEvent(self, _event):
        self.hovered = True

    def leaveEvent(self, _event):
        self.hovered = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.grab = event.globalPosition() - QPointF(self.px, self.py)
            self.dragged = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.grab is None:
            return
        position = event.globalPosition() - self.grab
        if not self.dragged and math.hypot(position.x() - self.px, position.y() - self.py) < 6:
            return
        self.dragged = True
        self.px, self.py = position.x(), position.y()
        self.move(int(self.px), int(self.py))

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.grab is None:
            return
        self.grab = None
        if self.dragged:
            # The cat has been moved: this is its new home.
            self.home = QPointF(self.px, self.py)
            self.follows = False
            self.running = False
        else:
            self.acknowledge()

    def menu(self, position):
        menu = QMenu()
        menu.addAction("Send this cat home", self.reset_home)
        menu.addAction("Dismiss this cat", lambda: self.app.remove(self.session))
        menu.addSeparator()
        follow = menu.addMenu("Follow the mouse")
        for state, label in (
            ("question", "When Claude needs you"),
            ("done", "When a task is finished"),
        ):
            action = follow.addAction(label)
            action.setCheckable(True)
            action.setChecked(bool(SETTINGS[FOLLOW_SETTING[state]]))
            action.toggled.connect(lambda checked, state=state: self.app.set_follow(state, checked))
        menu.addSeparator()
        usage = menu.addAction("Usage cat")
        usage.setCheckable(True)
        usage.setChecked(usage_common.file_setting("usage_cat") is not False)
        usage.toggled.connect(self.app.set_usage_cat)
        menu.addAction("Usage cat only (hide session cats)", self.app.usage_only)
        menu.addAction("Quit we-always-need-cats", QApplication.instance().quit)
        menu.exec(position)

    def reset_home(self):
        self.home = None
        self.area = None
        self.follows = False


class CursorReceiver(QObject):
    """Receives over D-Bus the mouse position sent by the KWin script."""

    def __init__(self, app):
        super().__init__()
        self.app = app

    @pyqtSlot(str)
    def Position(self, message):
        try:
            values = [float(v) for v in message.split(",")]
            x, y, width, height = values[:4]
        except ValueError:
            return
        if width > 0 and height > 0:
            self.app.kwin_cursor = (x, y, width, height)
            if len(values) >= 8 and values[6] > 0 and values[7] > 0:
                self.app.kwin_area = tuple(values[4:8])


class App(QObject):
    def __init__(self):
        super().__init__()
        self.cats = {}
        self.kwin_cursor = None
        self.kwin_area = None
        self.empty_since = time.monotonic() + 45  # grace period at start-up
        self.last_tick = time.monotonic()

        if os.path.exists(SOCKET):
            os.unlink(SOCKET)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(SOCKET)
        os.chmod(SOCKET, 0o600)
        self.socket.setblocking(False)
        self.listener = QSocketNotifier(self.socket.fileno(), QSocketNotifier.Type.Read, self)
        self.listener.activated.connect(self.read)

        self.connect_cursor()

        self.tick = QTimer(self)
        self.tick.timeout.connect(self.animate)
        self.tick.start(33)
        self.housekeeping = QTimer(self)
        self.housekeeping.timeout.connect(self.clean_up)
        self.housekeeping.start(2000)

    # --- Mouse position -----------------------------------------------------

    def connect_cursor(self):
        """Load the KWin script that reports the mouse position."""
        self.bus = QDBusConnection.sessionBus()
        self.receiver = CursorReceiver(self)
        try:
            if not self.bus.registerService(DBUS_SERVICE):
                return
            self.bus.registerObject(
                DBUS_PATH,
                DBUS_INTERFACE,
                self.receiver,
                QDBusConnection.RegisterOption.ExportAllSlots,
            )
            kwin = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", self.bus)
            if not kwin.isValid():
                return
            kwin.call("unloadScript", KWIN_SCRIPT)
            answer = kwin.call("loadScript", os.path.join(BASE_DIR, "kwin_cursor.js"), KWIN_SCRIPT)
            arguments = answer.arguments()
            if not arguments or int(arguments[0]) < 0:
                log("KWin script not loaded:", answer.errorMessage())
                return
            script = QDBusInterface(
                "org.kde.KWin",
                f"/Scripting/Script{int(arguments[0])}",
                "org.kde.kwin.Script",
                self.bus,
            )
            script.call("run")
        except Exception as error:  # no KWin: fall back on the position seen by X11
            log("KWin cursor unavailable:", error)

    def disconnect_cursor(self):
        try:
            kwin = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", self.bus)
            if kwin.isValid():
                kwin.call("unloadScript", KWIN_SCRIPT)
        except Exception:
            pass

    def mouse(self):
        if self.kwin_cursor:
            x, y, width, height = self.kwin_cursor
            whole = QGuiApplication.primaryScreen().virtualGeometry()
            return QPointF(
                whole.left() + x * whole.width() / width,
                whole.top() + y * whole.height() / height,
            )
        return QPointF(QCursor.pos())

    def usable_area(self):
        """Area of the active screen where cats sit, excluding the task bar."""
        if self.kwin_cursor and self.kwin_area:
            _, _, width, height = self.kwin_cursor
            whole = QGuiApplication.primaryScreen().virtualGeometry()
            fx, fy = whole.width() / width, whole.height() / height
            x, y, w, h = self.kwin_area
            return QRect(
                int(whole.left() + x * fx), int(whole.top() + y * fy), int(w * fx), int(h * fy)
            )
        area = QGuiApplication.primaryScreen().availableGeometry()
        return area.adjusted(0, 0, 0, -48)

    def usage_only(self):
        """Turn the session cats off (they no longer start) and leave."""
        save_setting("session_cats", False)
        QApplication.instance().quit()

    def set_usage_cat(self, enabled):
        """Show the usage cat again, or hide it for good (it leaves by itself
        within a second, and the status line no longer starts it)."""
        save_setting("usage_cat", enabled)
        if enabled:
            import usage_statusline

            if not usage_statusline.program_is_running():
                usage_statusline.start_program()

    def set_follow(self, state, enabled):
        """Menu setting, shared by every cat: follow the mouse in this state or not."""
        save_setting(FOLLOW_SETTING[state], enabled)
        if not enabled:
            for cat in self.cats.values():
                if cat.state == state:
                    cat.follows = False

    def follower_order(self, cat):
        followers = sorted((c for c in self.cats.values() if c.follows), key=lambda c: c.rank)
        return followers.index(cat) if cat in followers else 0

    # --- Claude Code events -------------------------------------------------

    def read(self):
        while True:
            try:
                data = self.socket.recv(65536)
            except (BlockingIOError, InterruptedError):
                return
            except OSError:
                return
            try:
                message = json.loads(data)
            except ValueError:
                continue
            try:
                self.handle(message)
            except Exception as error:
                log("error:", error, message)

    def cat_of(self, session):
        cat = self.cats.get(session)
        if cat is None:
            ranks = {c.rank for c in self.cats.values()}
            rank = next(i for i in range(len(ranks) + 1) if i not in ranks)
            taken = {c.coat["name"] for c in self.cats.values()}
            free = [c for c in sprites.COATS if c["name"] not in taken]
            coat = free[0] if free else pick(sprites.COATS, session)
            cat = Cat(self, session, rank, coat)
            self.cats[session] = cat
        return cat

    def remove(self, session):
        cat = self.cats.pop(session, None)
        if cat is not None:
            cat.close()
            cat.deleteLater()
        if not self.cats:
            self.empty_since = time.monotonic()

    def handle(self, m):
        log(json.dumps(m, ensure_ascii=False))
        event, session = m.get("ev", ""), m.get("sid", "")
        if event == "Quit":  # sent by the usage cat when the session cats are turned off
            QApplication.instance().quit()
            return
        if not session:
            return
        if event == "SessionEnd":
            self.remove(session)
            return
        cat = self.cat_of(session)
        cat.seen = time.monotonic()
        if m.get("pid"):
            cat.pid = int(m["pid"])
        agent = m.get("agent_id", "")
        if m.get("cwd") and not agent and (not cat.project or event == "SessionStart"):
            cat.project = os.path.basename(m["cwd"].rstrip("/")) or m["cwd"]
        tool = m.get("tool", "")

        if event == "SubagentStart":
            key = agent or f"agent-{len(cat.kittens)}"
            cat.kittens[key] = new_kitten(m.get("agent_type", ""), len(cat.kittens))
        elif event == "SubagentStop":
            if agent in cat.kittens:
                del cat.kittens[agent]
            elif cat.kittens and not agent:
                cat.kittens.pop(next(iter(cat.kittens)))
        elif agent:
            # Subagent event: only its kitten changes activity.
            if agent not in cat.kittens:
                cat.kittens[agent] = new_kitten(m.get("agent_type", ""), len(cat.kittens))
            kitten = cat.kittens[agent]
            if event == "PreToolUse":
                set_kitten_activity(kitten, describe_tool(tool, "")[1])
            elif event in ("PostToolUse", "PostToolUseFailure"):
                set_kitten_activity(kitten, "think")
        elif event == "UserPromptSubmit":
            cat.set_state("work", "thinking")
        elif event == "PreToolUse":
            if tool == "AskUserQuestion":
                cat.set_state("question", "asking you something")
            elif tool == "ExitPlanMode":
                cat.set_state("question", "proposing a plan")
            else:
                cat.set_state("work", *describe_tool(tool, m.get("detail", "")))
        elif event in ("PostToolUse", "PostToolUseFailure"):
            cat.set_state("work", "thinking")
        elif event == "PreCompact":
            cat.set_state("work", "summarizing the conversation")
        elif event == "Notification":
            kind = m.get("notif", "")
            text = m.get("message", "").lower()
            if kind == "permission_prompt" or (not kind and "permission" in text):
                cat.set_state("question", "waiting for your approval")
            elif kind == "elicitation_dialog":
                cat.set_state("question", "asking you something")
            elif kind == "idle_prompt" or (not kind and "waiting for your input" in text):
                if cat.state == "work":
                    cat.set_state("question", "waiting for your answer")
        elif event == "Stop":
            if m.get("asks"):
                # Claude's turn ends on a question: it waits for an answer.
                cat.set_state("question", "waiting for your answer")
            else:
                cat.set_state("done", "all done")
        elif event == "StopFailure":
            cat.set_state("question", "stopped on an error")
        cat.refresh()
        self.tick.setInterval(33)

    # --- Program life -------------------------------------------------------

    def animate(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.1)
        self.last_tick = now
        busy = False
        for cat in self.cats.values():
            cat.advance(dt)
            cat.refresh()
            busy = busy or cat.running or cat.follows or cat.grab is not None
        # Fast frame rate only while a cat moves: the rest of the time a few
        # frames per second are enough and the program costs almost nothing.
        interval = 33 if busy else 150
        if self.tick.interval() != interval:
            self.tick.setInterval(interval)

    def clean_up(self):
        now = time.monotonic()
        for session, cat in list(self.cats.items()):
            stopped = cat.pid and not os.path.exists(f"/proc/{cat.pid}")
            if stopped or now - cat.seen > 12 * 3600:
                self.remove(session)
                continue
            elapsed = now - cat.since
            if cat.state == "done" and cat.follows and elapsed > SETTINGS["follow_after_done"]:
                cat.follows = False
            if cat.state == "idle" and elapsed > SETTINGS["sleep_delay"]:
                cat.set_state("sleep")
        if not self.cats and now - self.empty_since > 15:
            QApplication.instance().quit()

    def shutdown(self):
        self.disconnect_cursor()
        try:
            self.socket.close()
            os.unlink(SOCKET)
        except OSError:
            pass


def main():
    if not SETTINGS.get("session_cats", True):
        return 0  # usage cat only (setting session_cats)
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0  # the program is already running

    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setQuitOnLastWindowClosed(False)
    app = App()
    application.aboutToQuit.connect(app.shutdown)
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(stop_signal, lambda *_: application.quit())
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
