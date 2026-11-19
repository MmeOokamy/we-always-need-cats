"""Drawing theme, chosen with "theme" in config.json.

    "cats"     the pixel art cats (sprites.py), the default
    "reapers"  Mass Effect style Reapers (sprites_reapers.py)

The theme is the default look; each session can switch between the looks
from its right-click menu, remembered per project ("looks" in config.json).

Every theme module offers the same names as sprites.py (IMAGES, ANIMATIONS,
the overlays, COATS, KITTEN_COATS, SCREENS, palette, draw...).
"""

import importlib
import json
import os

THEMES = {"cats": "sprites", "reapers": "sprites_reapers"}
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def name():
    """Theme set in config.json, "cats" when missing or unknown."""
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            chosen = json.load(f).get("theme", "cats")
    except (OSError, ValueError, AttributeError):
        chosen = "cats"
    return chosen if chosen in THEMES else "cats"


def load(chosen=None):
    """Module holding the drawings of a theme (the configured one by default)."""
    return importlib.import_module(THEMES.get(chosen or name(), "sprites"))
