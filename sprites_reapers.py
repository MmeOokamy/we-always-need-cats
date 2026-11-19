"""Pixel art drawings of the Reapers theme ("theme": "reapers" in config.json).

Same names as sprites.py, so that cats.py and usage_cat.py draw them without
knowing the theme: a Sovereign-class Reaper per Claude Code session, a small
destroyer per running subagent.

Every sprite is a list of text lines, one character per pixel:

    .  transparent        K  outline
    F  hull               S  hull seams (darker)
    W  hull edge (lighter)
    E  red glow (eyes, seam)  D  dimmed glow (asleep)
    L  core glow (color depends on the activity)
    N  small ship hull    B  engine and mass relay blue
    H  hot beam core      R  beam
    Q  Citadel hull       q  Citadel lights

Front views are symmetric: they are written as their left half and mirrored.
After editing a drawing, run `python3 sprites_reapers.py preview.png`.
"""

import sprites
from sprites import CELL_H, CELL_W  # noqa: F401  (same cell as the cats)


# --- Standing Reaper, seen from the side, facing right (16 lines) ----------
# A long hull tilted up, its glow where the legs meet the hull, four legs.

_HULL = [
    "....KKK.............",
    "...KWWFKK...........",
    "...KWFFSFK..........",
    "..KWFFSFFFK.........",
    "..KWFSFFFSFK........",
    "..KWFFSFFFSFK.......",
    "..KWFFFSFFFSFK......",
    "...KWFFSFFFSFEK.....",
    "...KWFFFSFFFEEK.....",
    "....KWFFFSFEEEK.....",
    "...KKKFFFFFKEEKK....",
]
_HULL_MAW = _HULL[:7] + [  # the glow opens wide: the horn
    "...KWFFSFFFSEEK.....",
    "...KWFFFSFFEHEEK....",
    "....KWFFFSEHHEK.....",
    "...KKKFFFFKEEEKK....",
]


def _hull(glow="E", core=None):
    """The hull, its glow in another color (D asleep, L by activity), with a
    hot core (H) or not."""
    lines = [line.replace("E", glow) for line in _HULL]
    if core:
        lines[8] = lines[8][:13] + core + lines[8][14:]
        lines[9] = lines[9][:12] + core + lines[9][13:]
    return lines


_LEGS_A = [
    "...KFKKFKKFKKFK.....",
    "..KFK.KFK.KFK.KFK...",
    ".KFK..KFK.KFK..KFK..",
    "KFK...KFK..KFK...KFK",
    "KK....KK...KK.....KK",
]
_LEGS_B = [
    "...KFKKFKKFKKFK.....",
    "...KFK.KFKKFK.KFK...",
    "..KFK..KFK.KFK.KFK..",
    ".KFK...KFK.KFK..KFK.",
    ".KK....KK...KK...KK.",
]
_LEGS_UP = [  # front leg raised
    "...KFKKFKKFKKFKKFK..",
    "..KFK.KFK.KFK..KFK..",
    ".KFK..KFK.KFK.......",
    "KFK...KFK..KFK......",
    "KK....KK...KK.......",
]

# --- Flying, seen from the side: legs trailing behind (10 lines) ------------

_RUN_A = [
    "....................",
    "KKKK..KKKKKKKKKK....",
    "KFFFKKWWWWWWWWWWKK..",
    ".KKKKEFFSFFFSFFFWWK.",
    "KFFFKEEFFFSFFFSFFFFK",
    ".KKKKEFFSFFFSFFFFKK.",
    "KFFFKKKKKKKKKKKKK...",
    "KKKK................",
    "....................",
    "....................",
]
_RUN_B = [
    "....................",
    ".KKK..KKKKKKKKKK....",
    "KFFKKKWWWWWWWWWWKK..",
    "KKKKKEFFSFFFSFFFWWK.",
    ".KFFKEEFFFSFFFSFFFFK",
    "KKKKKEFFSFFFSFFFFKK.",
    "KFFKKKKKKKKKKKKKK...",
    ".KKK................",
    "....................",
    "....................",
]

# --- Dormant in dark space: lying down, legs folded, glow dimmed (8 lines) --

_SLEEP_A = [
    "......KKKKKKKKK.....",
    "...KKKWWWWWWWWWKK...",
    ".KKWFFFSFFFSFFFFWK..",
    "KWFFSFFFSFFFSFFFDK..",
    "KFFFFSFFFSFFFFFDDK..",
    ".KKKKKKKKKKKKKKKKKK.",
    "..KFKKFK..KFKKFKKFK.",
    "..KKKKKK..KKKKKKKKK.",
]
_SLEEP_B = [
    "....................",
    "......KKKKKKKKK.....",
    "...KKKWWWWWWWWWKK...",
    ".KKWFFFSFFFSFFFFWK..",
    "KWFFSFFFSFFFSFFDDK..",
    ".KKKKKKKKKKKKKKKKKK.",
    "..KFKKFK..KFKKFKKFK.",
    "..KKKKKK..KKKKKKKKK.",
]

# --- Thinking 1: the Reaper fires at a small ship, which dodges -------------

_SHIP = ["..KKKK.", "KNNNNKB", ".KKKKK."]
_BEAM = [  # from the glow up and forward, 12 lines
    ".....RHR",
    ".....RHR",
    "....RHR.",
    "....RHR.",
    "...RHR..",
    "...RHR..",
    "..RHR...",
    "..RHR...",
    ".RHR....",
    ".RHR....",
    "RHR.....",
    "RHR.....",
]

# --- Thinking 2: the Reaper charges a mass relay, which sends a streak ------

_RELAY_A = [".KKKKKKK.", "KQQQQQQQK", ".KKBqBKK.", "KQQQQQQQK", ".KKKKKKK."]
_RELAY_B = [".KKKKKKK.", "KQQQQQQQK", ".KKqBqKK.", "KQQQQQQQK", ".KKKKKKK."]
_RELAY_FLASH = [".KKKKKKK.", "KQQQQQQQK", ".KKHHHKK.", "KQQQQQQQK", ".KKKKKKK."]
_STREAK = ["qBBBBBHH"]
_ZAP = ["RHR"] * 9  # the glow reaching up to the relay

# --- Thinking 3: the Reaper closes the arms of the Citadel ------------------
# Seen from the side: the ring at the bottom, five arms; from wide open to
# closed, step by step.

_CITADEL = [
    [
        "K...K...K",
        "Q...Q...Q",
        ".Q..Q..Q.",
        "..Q.Q.Q..",
        "...QQQ...",
        "..KqqqK..",
        "...KKK...",
    ],
    [
        ".K..K..K.",
        ".Q..Q..Q.",
        "..Q.Q.Q..",
        "..Q.Q.Q..",
        "...QQQ...",
        "..KqqqK..",
        "...KKK...",
    ],
    [
        "..K.K.K..",
        "..Q.Q.Q..",
        "..Q.Q.Q..",
        "...QQQ...",
        "...QQQ...",
        "..KqqqK..",
        "...KKK...",
    ],
    [
        "...KKK...",
        "...QQQ...",
        "...QQQ...",
        "...QQQ...",
        "...QQQ...",
        "..KqqqK..",
        "...KKK...",
    ],
]

IMAGES = {
    "sit_a": _hull() + _LEGS_A,
    "sit_b": _hull() + _LEGS_B,
    "sit_blink": _hull("D") + _LEGS_A,
    "meow_a": _HULL_MAW + _LEGS_A,
    "meow_b": _hull() + _LEGS_A,
    "happy_a": _hull(core="H") + _LEGS_UP,
    "happy_b": _hull(core="H") + _LEGS_B,
    # Working: the glow takes the color of the activity, its core keeps the
    # color of the Reaper (or of the destroyer, which tells its type).
    "work_a": _hull("L", "E") + _LEGS_A,
    "work_b": _hull("L", "E") + _LEGS_B,
    "charge": _hull(core="H") + _LEGS_A,
    "ship": _SHIP,
    "beam": _BEAM,
    "relay_a": _RELAY_A,
    "relay_b": _RELAY_B,
    "relay_flash": _RELAY_FLASH,
    "streak": _STREAK,
    "zap": _ZAP,
    **{f"citadel_{n}": lines for n, lines in enumerate(_CITADEL)},
    "run_a": _RUN_A,
    "run_b": _RUN_B,
    "sleep_a": _SLEEP_A,
    "sleep_b": _SLEEP_B,
}

# Animations: sequences of sprites played in a loop. The three thinking games
# last 16 frames (the length of a thinking turn in cats.py).
ANIMATIONS = {
    "idle": ["sit_a"] * 4 + ["sit_b"] * 4 + ["sit_a"] * 3 + ["sit_blink"],
    "question": ["meow_a", "meow_b"],
    "done": ["happy_a", "happy_b"],
    "work": ["work_a", "work_b"],
    "think": ["sit_a", "sit_a", "charge", "charge", "sit_a", "sit_a", "sit_b", "sit_b"],
    "play": ["sit_a"] * 3 + ["charge"] * 3 + ["sit_a"] * 6 + ["sit_b"] * 4,
    "cube": ["charge", "sit_a"] * 6 + ["happy_b"] * 4,
    "run": ["run_a", "run_b"],
    "sleep": ["sleep_a"] * 3 + ["sleep_b"] * 3,
}

# What is drawn over the Reaper, frame by frame of each thinking game, in
# drawing order, as (sprite, column, line, mirrored); line < 0: above it.

# The ship crosses from the front, the beam misses it.
CREPE_FLIGHT = [
    [("ship", 20, -6, False)],
    [("ship", 17, -6, False)],
    [("ship", 14, -5, False)],
    [("ship", 11, -6, False), ("beam", 13, -3, False)],
    [("ship", 8, -6, False)],
    [("ship", 5, -5, False)],
    [("ship", 2, -6, False)],
    [],
]

_RELAY = (11, -6)
YARN_PLAY = (
    [[("relay_a" if k % 2 else "relay_b", *_RELAY, False)] for k in range(3)]
    + [[("relay_b", *_RELAY, False), ("zap", 14, -1, False)] for _ in range(2)]
    + [[("relay_flash", *_RELAY, False), ("zap", 14, -1, False)]]
    + [[("relay_a", *_RELAY, False), ("streak", 21 + 5 * k, -4, False)] for k in range(4)]
    + [[("relay_a" if k % 2 else "relay_b", *_RELAY, False)] for k in range(6)]
)

_CITADEL_AT = (14, 0)
CUBE_SOLVE = [
    [(f"citadel_{min(k // 3, 3)}", *_CITADEL_AT, False)] for k in range(12)
] + [[("citadel_3", *_CITADEL_AT, False)]] * 4

SYMBOLS = sprites.SYMBOLS

# --- Colors -----------------------------------------------------------------

OUTLINE = "#14101A"
# Pale red halo, to stay readable on a dark background.
HALO = "#C8F2D6D0"

# Reaper hulls (one per Claude Code session).
COATS = [
    {"name": "sovereign", "F": "#5E5A63", "S": "#3D3A44", "W": "#8E8794", "E": "#FF3B2F"},
    {"name": "harbinger", "F": "#6B5847", "S": "#47392D", "W": "#9C8670", "E": "#FF4A2A"},
    {"name": "obsidian", "F": "#3F3D4A", "S": "#2A2833", "W": "#6C6878", "E": "#FF2E4D"},
    {"name": "rust", "F": "#7A4E3A", "S": "#553324", "W": "#A9735A", "E": "#FF5A1F"},
    {"name": "ash", "F": "#7C7F86", "S": "#55585F", "W": "#A9ADB5", "E": "#FF3B2F"},
    {"name": "bone", "F": "#9C9284", "S": "#6F675B", "W": "#C9BFAF", "E": "#E8341C"},
]

# Destroyers (one per subagent type): same hull, lights of their own.
KITTEN_COATS = [
    {"name": "crimson", "F": "#55525C", "S": "#38353F", "W": "#857F8C", "E": "#FF3B5C"},
    {"name": "amber", "F": "#55525C", "S": "#38353F", "W": "#857F8C", "E": "#FFA62B"},
    {"name": "violet", "F": "#55525C", "S": "#38353F", "W": "#857F8C", "E": "#B57BFF"},
    {"name": "cyan", "F": "#55525C", "S": "#38353F", "W": "#857F8C", "E": "#3BD8FF"},
    {"name": "acid", "F": "#55525C", "S": "#38353F", "W": "#857F8C", "E": "#A6FF3B"},
    {"name": "ember", "F": "#55525C", "S": "#38353F", "W": "#857F8C", "E": "#FF6B3B"},
]

# Core glow, depending on the activity.
SCREENS = {
    "think": "#FF6B5E",
    "write": "#7CE38B",
    "read": "#7CC4FF",
    "shell": "#FFC857",
    "web": "#C59BFF",
    "agent": "#FF9ECF",
}


def palette(coat, activity="think"):
    """Character -> color table for a hull and an activity."""
    return {
        "K": OUTLINE,
        "F": coat["F"],
        "S": coat["S"],
        "W": coat["W"],
        "E": coat["E"],
        "D": "#6E2A2A",
        "L": SCREENS.get(activity, SCREENS["think"]),
        "N": "#E6E9EE",
        "B": "#4FC3FF",
        "H": "#FFB09A",
        "R": "#E8261C",
        "Q": "#B9C3CF",
        "q": "#7FD3FF",
    }


def draw(lines, colors, mirror=False):
    """Turn a list of lines into an image, one pixel per character."""
    return sprites.draw(lines, colors, mirror, HALO)


def check():
    return sprites.check(IMAGES)


if __name__ == "__main__":
    import sys

    for error in check():
        print("Warning:", error)
    if len(sys.argv) > 1:
        sprites._preview(sys.argv[1], theme=sys.modules[__name__], background="#1B2233")
        print("Sheet saved:", sys.argv[1])
