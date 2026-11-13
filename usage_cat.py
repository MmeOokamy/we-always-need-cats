#!/usr/bin/env python3
"""usage-cat: a pixel art cat that keeps an eye on the Claude Code usage limits.

The cat (the one of we-always-need-cats) stays above every other window and
shows how much of the session (5 hours) and weekly limits is used, and when
they reset. The figures are written by usage_statusline.py, which Claude Code runs
at every status line refresh.

Normal start: automatic, from usage_statusline.py.
Manual start: python3 usage_cat.py
Sheet of every state, for a visual check: python3 usage_cat.py --preview usage.png
"""

import os
import sys

PREVIEW = "--preview" in sys.argv
if PREVIEW:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
elif os.environ.get("DISPLAY"):
    # Under Wayland, only an X11 window (XWayland) can place itself freely and
    # stay above the others, so that mode is forced before Qt is loaded.
    os.environ["QT_QPA_PLATFORM"] = "xcb"

import fcntl
import json
import math
import signal
import time

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
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

import usage_common as common
import popup
import sprites
import updates
from usage_common import LEVEL_COLOR, LEVELS, SETTINGS, TEXT

S = max(1, int(SETTINGS["scale"]))  # cat scale
S2 = max(1, S // 2)  # scale of the small symbols
CAT_W, CAT_H = sprites.CELL_W * S, sprites.CELL_H * S
SYMBOLS_H = 7 * S
BUBBLE_H = 72
GAUGE_H = 26
WIDTH = max(CAT_W + 64, 290)
HEIGHT = BUBBLE_H + SYMBOLS_H + CAT_H + GAUGE_H
CAT_BOTTOM = HEIGHT - GAUGE_H
CAT_TOP = CAT_BOTTOM - CAT_H

# Frames per second of each animation.
FPS = {"idle": 3, "question": 3, "panic": 6, "done": 4, "work": 4, "sleep": 1.5}
# Sprites of each animation ("panic" is a faster meow).
FRAMES = dict(sprites.ANIMATIONS, panic=sprites.ANIMATIONS["question"])

ACTIVE_SECONDS = 20  # the cat types for that long after fresh figures arrive
CELEBRATION_SECONDS = 30  # the cat jumps for that long after a reset
CREAM = "#FFFDF5"

# The laptop screen takes the color of the usage level.
sprites.SCREENS.update(LEVEL_COLOR)

_pixmaps = {}


def pixmap(name, coat, level, scale):
    key = (name, coat["name"], level, scale)
    if key not in _pixmaps:
        image = sprites.draw(sprites.IMAGES[name], sprites.palette(coat, level))
        _pixmaps[key] = QPixmap.fromImage(
            image.scaled(image.width() * scale, image.height() * scale)
        )
    return _pixmaps[key]


class UsageCat(QWidget):
    def __init__(self):
        super().__init__()
        self.coat = next(
            (c for c in sprites.COATS if c["name"] == SETTINGS["coat"]), sprites.COATS[0]
        )
        self.state = {}  # figures written by usage_statusline.py
        self.state_mtime = None
        self.pids = set()  # Claude Code processes seen so far
        self.level = "none"
        self.started = time.time()
        self.active_until = 0
        self.notify_until = 0
        self.celebrate_until = 0
        self.hovered = False
        self.pinned = False  # bubble kept open by a click
        self.grab = None
        self.dragged = False
        self.home = self.saved_home()
        self.signature = None
        self.updater = None  # updates.Updater, set by main() (not in previews)

        self.setWindowTitle(common.APP_NAME)
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

        position = self.home or self.default_home()
        self.px, self.py = position.x(), position.y()
        self.move(int(self.px), int(self.py))
        self.poll()

    # --- Position -----------------------------------------------------------

    def default_home(self):
        """Bottom left of the main screen, above the task bar."""
        area = QGuiApplication.primaryScreen().availableGeometry().adjusted(0, 0, 0, -48)
        return QPointF(area.left() + 16, area.bottom() - 4 - HEIGHT)

    def saved_home(self):
        try:
            with open(common.POSITION, encoding="utf-8") as f:
                saved = json.load(f)
            point = QPoint(int(saved["x"]), int(saved["y"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None
        whole = QGuiApplication.primaryScreen().virtualGeometry()
        if not whole.contains(point + QPoint(CAT_W // 2, CAT_BOTTOM - CAT_H // 2)):
            return None  # the screens have changed since
        return QPointF(point)

    def save_home(self):
        try:
            if self.home is None:
                os.unlink(common.POSITION)
                return
            os.makedirs(common.CACHE, exist_ok=True)
            with open(common.POSITION, "w", encoding="utf-8") as f:
                json.dump({"x": int(self.home.x()), "y": int(self.home.y())}, f)
        except OSError:
            pass

    def set_session_cats(self, enabled):
        """Show the session cats (cats.py) or keep this usage cat alone."""
        try:
            common.save_setting("session_cats", enabled)
        except OSError:
            return
        if not enabled:
            common.dismiss_session_cats()

    def hide_for_good(self):
        """Leave and stay hidden: the status line no longer starts the cat
        (setting usage_cat, turned back on from a session cat's menu)."""
        try:
            common.save_setting("usage_cat", False)
        except OSError:
            return
        QApplication.instance().quit()

    def reset_home(self):
        self.home = None
        self.save_home()
        position = self.default_home()
        self.px, self.py = position.x(), position.y()
        self.move(int(self.px), int(self.py))

    # --- Usage figures ------------------------------------------------------

    def poll(self):
        """Reads the figures again when usage_statusline.py has written new ones."""
        now = time.time()
        try:
            mtime = os.stat(common.STATE).st_mtime_ns
        except OSError:
            mtime = None
        if mtime is not None and mtime != self.state_mtime:
            fresh = self.state_mtime is not None
            self.state_mtime = mtime
            self.state = common.read_state()
            if self.state.get("pid"):
                self.pids.add(int(self.state["pid"]))
            if fresh or now - self.state.get("ts", 0) < ACTIVE_SECONDS:
                self.active_until = now + ACTIVE_SECONDS
        self.update_level(now)
        self.refresh()

    def update_level(self, now):
        """The level also changes without new figures, when a reset time passes."""
        level = common.worst_level(self.state, now)
        before, after = LEVELS.index(self.level), LEVELS.index(level)
        if after > before:
            self.notify_until = now + SETTINGS["notify_seconds"]
        elif before >= LEVELS.index("alert") and after < LEVELS.index("alert"):
            # The limit that was nearly reached has been reset.
            self.celebrate_until = now + CELEBRATION_SECONDS
            self.notify_until = self.celebrate_until
        self.level = level

    def should_quit(self, now):
        if SETTINGS["keep_alive"] or now - self.started < 45:
            return False
        if self.pids:
            return not any(os.path.exists(f"/proc/{pid}") for pid in self.pids)
        return now - self.state.get("ts", self.started) > 12 * 3600

    # --- Drawing ------------------------------------------------------------

    def animation(self, now):
        if now < self.celebrate_until:
            return "done"
        if self.level == "full":
            return "sleep"
        if self.level == "critical":
            return "panic"
        if self.level == "alert":
            return "question"
        if now < self.active_until:
            return "work"
        return "idle"

    def bubble_lines(self, now):
        """Text lines of the bubble, or an empty list when it is closed."""
        if not (self.hovered or self.pinned or now < self.notify_until):
            return []
        title = TEXT["renewed_title"] if now < self.celebrate_until else TEXT["title"]
        lines = [title] + common.window_lines(self.state, now)
        if self.hovered and self.updater and self.updater.available():
            lines.append(updates.texts(SETTINGS["lang"])["bubble"])
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

    def refresh(self, force=False, now=None):
        """Redraw the window when what it shows has changed."""
        now = time.time() if now is None else now
        animation = self.animation(now)
        index = int(time.monotonic() * FPS[animation])
        lines = self.bubble_lines(now)
        gauges = tuple(common.window(self.state, name, now)[0] for name in common.WINDOWS)
        signature = (animation, index, self.level, tuple(lines), gauges)
        if signature == self.signature and not force:
            return
        self.signature = signature
        # The window is drawn into a buffer, then masked with that drawing:
        # clicks pass through everything that is transparent.
        buffer = QPixmap(WIDTH, HEIGHT)
        buffer.fill(Qt.GlobalColor.transparent)
        painter = QPainter(buffer)
        self.paint(painter, animation, index, lines, gauges)
        painter.end()
        self.buffer = buffer
        self.setMask(QRegion(buffer.mask()))
        self.update()

    def paintEvent(self, _event):
        QPainter(self).drawPixmap(0, 0, self.buffer)

    def draw_symbol(self, painter, name, x, y, color, scale):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        for j, line in enumerate(sprites.SYMBOLS[name]):
            for i, char in enumerate(line):
                if char == "K":
                    painter.drawRect(x + i * scale, y + j * scale, scale, scale)

    def draw_bar(self, painter, y, height, pct, color):
        """Pixel art gauge as wide as the cat, with its light halo."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(sprites.HALO))
        painter.drawRect(0, y - 1, CAT_W, height + 2)
        painter.setBrush(QColor(sprites.OUTLINE))
        painter.drawRect(1, y, CAT_W - 2, height)
        inner = CAT_W - 6
        painter.setBrush(QColor(CREAM))
        painter.drawRect(3, y + 2, inner, height - 4)
        if pct:
            painter.setBrush(QColor(color))
            painter.drawRect(3, y + 2, max(2, round(inner * pct / 100)), height - 4)

    def paint(self, painter, animation, index, lines, gauges):
        even = index % 2 == 0
        color = LEVEL_COLOR[self.level]
        frames = FRAMES[animation]

        # The cat
        image = pixmap(frames[index % len(frames)], self.coat, self.level, S)
        jump = 2 * S if (animation == "done" and even) else 0
        x = (CAT_W - image.width()) // 2
        painter.drawPixmap(x, CAT_BOTTOM - image.height() - jump, image)

        # The symbols above the cat
        top = CAT_TOP
        if animation == "sleep":
            self.draw_symbol(painter, "z", CAT_W - 5 * S, top + (3 if even else 2) * S, "#FFFFFF", S2)
            if even:
                self.draw_symbol(painter, "z", CAT_W - 2 * S, top - S, "#FFFFFF", S2)
        elif animation in ("question", "panic"):
            self.draw_symbol(painter, "!", CAT_W - 3 * S, top - (6 if even else 5) * S, color, S)
        elif animation == "done":
            for i, (sx, sy) in enumerate(((1, -4), (15, -6), (9, -7))):
                if (index + i) % 3:
                    self.draw_symbol(painter, "star", sx * S, top + sy * S + jump // 2, "#FFD43B", S)
        elif animation == "work":
            for i in range(3):
                phase = (index + i * 2) % 6
                if phase < 5:
                    self.draw_symbol(painter, "!", (6 + i * 3) * S, top - phase * S, color, S2)

        # The gauges under the cat: session (thick), then week (thin)
        session, week = gauges
        self.draw_bar(painter, CAT_BOTTOM + 3, 12, session, LEVEL_COLOR[common.level_of(session)])
        self.draw_bar(painter, CAT_BOTTOM + 17, 8, week, LEVEL_COLOR[common.level_of(week)])

        # The session percentage, next to its gauge
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label = "…" if session is None else f"{session} %"
        painter.setFont(self.font_title)
        width = QFontMetrics(self.font_title).horizontalAdvance(label) + 14
        pill = QRect(CAT_W + 5, CAT_BOTTOM + 1, width, 18)
        painter.setPen(QPen(QColor(LEVEL_COLOR[common.level_of(session)]), 2))
        painter.setBrush(QColor(CREAM))
        painter.drawRoundedRect(pill, 7, 7)
        painter.setPen(QColor(sprites.OUTLINE))
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, label)

        # The bubble
        if lines:
            rect = self.bubble_rect(lines)
            border = QColor(color if self.level in LEVELS[2:] else sprites.OUTLINE)
            if animation == "done":
                border = QColor(LEVEL_COLOR["ok"])
            painter.setPen(QPen(border, 2))
            painter.setBrush(QColor(CREAM))
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
            for i, line in enumerate(lines):
                font = self.font_title if i == 0 else self.font_body
                painter.setFont(font)
                text = QFontMetrics(font).elidedText(
                    line, Qt.TextElideMode.ElideRight, rect.width() - 14
                )
                painter.drawText(rect.left() + 8, rect.top() + 17 + 16 * i, text)

    # --- Mouse --------------------------------------------------------------

    def enterEvent(self, _event):
        self.hovered = True
        self.refresh()

    def leaveEvent(self, _event):
        self.hovered = False
        self.refresh()

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
            self.save_home()
        else:
            # Plain click: keeps the bubble open, or closes it.
            self.pinned = not self.pinned
            self.notify_until = 0
            self.refresh()

    def menu(self, position):
        menu = QMenu()
        menu.addAction(TEXT["menu_home"], self.reset_home)
        menu.addSeparator()
        session_cats = menu.addAction(TEXT["menu_session_cats"])
        session_cats.setCheckable(True)
        session_cats.setChecked(bool(SETTINGS["session_cats"]))
        session_cats.toggled.connect(self.set_session_cats)
        menu.addSeparator()
        if self.updater:
            self.updater.add_menu(menu)
            menu.addSeparator()
        menu.addAction(TEXT["menu_hide"], self.hide_for_good)
        menu.addAction(TEXT["menu_quit"], QApplication.instance().quit)
        popup.show_menu(menu, position)


def preview(path):
    """Save a sheet of the cat at every usage level, for a visual check."""
    now = time.time()
    samples = [
        ({}, {}),
        ({"five_hour": 12, "seven_day": 4}, {}),
        ({"five_hour": 34, "seven_day": 20}, {"active_until": now + 60}),
        ({"five_hour": 63, "seven_day": 41}, {}),
        ({"five_hour": 86, "seven_day": 52}, {}),
        ({"five_hour": 97, "seven_day": 58}, {}),
        ({"five_hour": 100, "seven_day": 61}, {}),
        ({"five_hour": 3, "seven_day": 61}, {"celebrate_until": now + 60}),
    ]
    columns = 4
    rows = (len(samples) + columns - 1) // columns
    margin = 12
    sheet = QPixmap(columns * (WIDTH + margin) + margin, rows * (HEIGHT + margin) + margin)
    sheet.fill(QColor("#6C8EAD"))
    painter = QPainter(sheet)
    cat = UsageCat()
    cat.pinned = True
    for i, (percentages, attributes) in enumerate(samples):
        resets = {"five_hour": now + 4350, "seven_day": now + 3.2 * 86400}
        cat.state = {
            name: {"pct": pct, "resets_at": resets[name]} for name, pct in percentages.items()
        }
        cat.active_until = cat.celebrate_until = 0
        for name, value in attributes.items():
            setattr(cat, name, value)
        cat.level = common.worst_level(cat.state, now)
        cat.refresh(force=True, now=now)
        x = margin + (i % columns) * (WIDTH + margin)
        y = margin + (i // columns) * (HEIGHT + margin)
        painter.drawPixmap(x, y, cat.buffer)
    painter.end()
    sheet.save(path)
    print("Sheet saved:", path)


def main():
    application = QApplication(sys.argv)
    application.setApplicationName(common.APP_NAME)
    application.setQuitOnLastWindowClosed(False)

    if PREVIEW:
        position = sys.argv.index("--preview")
        preview(sys.argv[position + 1] if len(sys.argv) > position + 1 else "usage.png")
        return 0

    if common.file_setting("usage_cat") is False:
        print("usage-cat est masqué (usage_cat: false dans config.json)")
        return 0
    lock = open(common.LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0  # the program is already running

    cat = UsageCat()
    cat.updater = updates.Updater(SETTINGS["lang"])
    cat.show()
    restarting = []

    tick = QTimer()
    tick.timeout.connect(cat.refresh)
    tick.start(100)

    def watch():
        cat.poll()
        # Hidden from a session cat's menu: leave at once.
        if cat.should_quit(time.time()) or common.file_setting("usage_cat") is False:
            application.quit()
        elif cat.updater.tick():
            restarting.append(True)  # a new version is installed: restart on it
            application.quit()

    watcher = QTimer()
    watcher.timeout.connect(watch)
    watcher.start(1000)

    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(stop_signal, lambda *_: application.quit())
    code = application.exec()
    if restarting:
        lock.close()
        updates.restart()
    return code


if __name__ == "__main__":
    sys.exit(main())
