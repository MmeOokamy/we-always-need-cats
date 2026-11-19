"""Drawings of the Reapers look ("Look" menu, or "theme": "reapers").

Same names as sprites.py, so that cats.py and usage_cat.py draw them without
knowing the look: a Sovereign-class Reaper per Claude Code session, a small
destroyer per running subagent.

The Reaper is a pixel art animation (art/reaper.gif, see the README for its
author), at its own size: one drawing pixel is one screen pixel (PIXEL is a
quarter of a cat pixel). tools/make_reaper_frames.py turns the GIF into
art/reaper-frames.png, its frames facing right; this module reads that strip
with Qt and makes the variants on the fly:

- the hull of each session (COATS): the steel blue of the animation turned
  into bronze, rust, ash...;
- working: the red lights take the color of the activity;
- destroyers (KITTEN_COATS): their lights in the color of their agent type;
- asleep: the frame darkened, lights dimmed.

A drawing is (GIF frame number, effect): None, "glow" (lights in the color
of the activity) or "dim" (asleep).

Preview: python3 sprites_reapers.py preview.png
"""

import colorsys
import json
import os

from PyQt6.QtGui import QColor, QImage, QTransform

import sprites

HERE = os.path.dirname(os.path.abspath(__file__))
STRIP = os.path.join(HERE, "art", "reaper-frames.png")
INDEX = os.path.join(HERE, "art", "reaper-frames.json")

PIXEL = 0.25  # a drawing pixel is a quarter of a cat pixel: the Reaper at its own size
# The cell of the Reaper's body (frames are wider: the beam and the
# explosion go past it, on the right, over the room of the destroyers).
CELL_W, CELL_H = 86, 151

# Frames per second of each animation (the animation's own pace; cats.py
# keeps its own for the other looks).
FPS = {"idle": 8, "question": 8, "done": 8, "work": 8, "think": 10, "play": 10,
       "cube": 10, "run": 14, "sleep": 1.5, "panic": 12}


def _frames(first, last, effect=None):
    return [f"g{n}" + (f"_{effect}" if effect else "") for n in range(first, last + 1)]


_EFFECTS = (None, "glow", "dim")
IMAGES = {
    f"g{n}" + (f"_{effect}" if effect else ""): (n, effect)
    for n in range(93) for effect in _EFFECTS
}

# The sequences of the animation: swaying (0-21), the lights glowing (36-55),
# the beam fired at the ground (56-65), the explosion (66-80).
ANIMATIONS = {
    "idle": _frames(0, 21),
    "question": _frames(44, 55),
    "done": _frames(0, 21),
    "work": _frames(36, 55, "glow"),
    # Thinking, in turn (16 cat frames each, 3.2 seconds: 32 frames at 10 fps):
    "think": _frames(56, 80) + _frames(0, 6),  # it fires at the ground
    "play": _frames(36, 55) + _frames(0, 11),  # its lights charge up
    "cube": _frames(0, 21) + _frames(0, 9),  # it sways
    "run": _frames(0, 21),
    "sleep": ["g0_dim", "g0_dim"],
}

# Nothing is drawn over the Reaper: its animation says it all.
CREPE_FLIGHT = [[]]
YARN_PLAY = [[]]
CUBE_SOLVE = [[]]

SYMBOLS = sprites.SYMBOLS

# --- Colors -----------------------------------------------------------------

OUTLINE = "#0E1018"
HALO = "#70D0E0F0"  # a soft light edge, to stay readable on a dark background

# Hulls (one per Claude Code session): hue (0-1, None: the animation's own
# steel blue), saturation and brightness factors.
COATS = [
    {"name": "sovereign", "hue": None, "sat": 1.0, "val": 1.0},
    {"name": "harbinger", "hue": 0.08, "sat": 0.55, "val": 1.0},
    {"name": "obsidian", "hue": 0.70, "sat": 0.25, "val": 0.72},
    {"name": "rust", "hue": 0.04, "sat": 0.9, "val": 0.95},
    {"name": "ash", "hue": None, "sat": 0.12, "val": 1.05},
    {"name": "bone", "hue": 0.11, "sat": 0.28, "val": 1.15},
]

# Destroyers (one per subagent type): the same hull, lights of their own.
KITTEN_COATS = [
    {"name": "crimson", "hue": None, "sat": 1.0, "val": 1.0, "lights": "#FF3B5C"},
    {"name": "amber", "hue": None, "sat": 1.0, "val": 1.0, "lights": "#FFA62B"},
    {"name": "violet", "hue": None, "sat": 1.0, "val": 1.0, "lights": "#B57BFF"},
    {"name": "cyan", "hue": None, "sat": 1.0, "val": 1.0, "lights": "#3BD8FF"},
    {"name": "acid", "hue": None, "sat": 1.0, "val": 1.0, "lights": "#A6FF3B"},
    {"name": "ember", "hue": None, "sat": 1.0, "val": 1.0, "lights": "#FF6B3B"},
]

# Glow, depending on the activity (same colors as the laptop of the cats).
SCREENS = {
    "think": "#FF6B5E",
    "write": "#7CE38B",
    "read": "#7CC4FF",
    "shell": "#FFC857",
    "web": "#C59BFF",
    "agent": "#FF9ECF",
}


def palette(coat, activity="think"):
    """What draw() needs to make a variant: the hull and the colors of the lights."""
    colors = dict(coat)
    colors["L"] = SCREENS.get(activity, SCREENS["think"])
    return colors


# --- Drawing ----------------------------------------------------------------

_strip = None
_index = None


def _load():
    global _strip, _index
    if _strip is None:
        _strip = QImage(STRIP).convertToFormat(QImage.Format.Format_ARGB32)
        with open(INDEX, encoding="utf-8") as f:
            _index = json.load(f)
    return _strip, _index


def _hue(color):
    c = QColor(color)
    return c.hueF() if c.hueF() >= 0 else 0.0


def draw(entry, colors, mirror=False):
    """A frame of the animation as an image, with its variant."""
    number, effect = entry
    strip, index = _load()
    w, h = index["width"], index["height"]
    frame = strip.copy(index["frames"][number] * w, 0, w, h)
    hull_hue, sat, val = colors.get("hue"), colors.get("sat", 1.0), colors.get("val", 1.0)
    lights = colors.get("L") if effect == "glow" else colors.get("lights")
    light_hue = _hue(lights) if lights else None
    out = QImage(w + 2, h + 2, QImage.Format.Format_ARGB32)
    out.fill(0)
    filled = []
    plain = hull_hue is None and sat == 1.0 and val == 1.0 and light_hue is None and effect != "dim"
    for y in range(h):
        for x in range(w):
            pixel = frame.pixel(x, y)
            alpha = pixel >> 24 & 0xFF
            if not alpha:
                continue
            filled.append((x + 1, y + 1))
            if plain:
                out.setPixel(x + 1, y + 1, pixel)
                continue
            r, g, b = (pixel >> 16 & 0xFF) / 255, (pixel >> 8 & 0xFF) / 255, (pixel & 0xFF) / 255
            hh, s, v = colorsys.rgb_to_hsv(r, g, b)
            light = s > 0.45 and v > 0.45 and (hh < 0.17 or hh > 0.9)
            if light:
                if effect == "dim":
                    hh, s, v = 0.0, 0.6, v * 0.45
                elif light_hue is not None:
                    hh = light_hue
            else:
                if hull_hue is not None:
                    hh = hull_hue
                s = min(1.0, s * sat)
                v = min(1.0, v * val * (0.5 if effect == "dim" else 1.0))
            r, g, b = colorsys.hsv_to_rgb(hh, s, v)
            out.setPixel(x + 1, y + 1, alpha << 24 | round(r * 255) << 16 | round(g * 255) << 8 | round(b * 255))
    halo = QColor(HALO)
    taken = set(filled)
    for x, y in filled:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (nx, ny) not in taken:
                out.setPixelColor(nx, ny, halo)
    if mirror:
        out = out.transformed(QTransform().scale(-1, 1))
    return out


def check():
    errors = []
    for name in (n for frames in ANIMATIONS.values() for n in frames):
        if name not in IMAGES:
            errors.append(f"{name}: unknown frame")
    return errors


def _preview(path):
    """One row per animation, a few frames of each, in several hulls."""
    from PyQt6.QtGui import QGuiApplication, QPainter

    app = QGuiApplication.instance() or QGuiApplication([])
    rows = [(a, frames[:: max(1, len(frames) // 6)][:6]) for a, frames in ANIMATIONS.items()]
    cw, ch = 182, 153
    sheet = QImage(cw * 6, ch * len(rows), QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#1B2233"))
    painter = QPainter(sheet)
    for r, (animation, frames) in enumerate(rows):
        for c, name in enumerate(frames):
            coat = COATS[c % len(COATS)]
            image = draw(IMAGES[name], palette(coat, "write"))
            painter.drawImage(c * cw, r * ch, image)
    painter.end()
    sheet.save(path)
    del app


if __name__ == "__main__":
    import sys

    for error in check():
        print("Warning:", error)
    if len(sys.argv) > 1:
        _preview(sys.argv[1])
        print("Sheet saved:", sys.argv[1])
