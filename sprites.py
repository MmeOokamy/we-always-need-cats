"""Pixel art drawings of the cat.

Every sprite is a list of text lines, one character per pixel:

    .  transparent        K  outline
    F  fur                S  stripes (darker fur)
    W  white (muzzle, belly)
    P  pink (ears, nose, mouth)
    E  eyes
    G  laptop shell
    L  laptop screen (color depends on the activity)

After editing a drawing, run `python3 sprites.py preview.png` to see the result.
"""

from PyQt6.QtGui import QColor, QImage, QTransform

# Size of the cell each sprite is placed in (bottom-aligned, centered).
# It includes one pixel of margin on every side for the light halo.
CELL_W = 22
CELL_H = 18

# --- Front head (10 lines), with variants for the eyes and the mouth --------

_HEAD_TOP = [
    "..KK........KK....",
    ".KFFK......KFFK...",
    ".KFPFKKKKKKFPFK...",
    ".KFFFSFSSFSFFFK...",
    ".KFFFFFSSFFFFFK...",
]
_EYES = {
    "open": [".KFEEFFFFFFEEFK...", ".KFEEFFPPFFEEFK..."],
    "lowered": [".KFFFFFFFFFFFFK...", ".KFEEFFPPFFEEFK..."],
    "happy": [".KFFEFFFFFFEFFK...", ".KFEFEFPPFEFEFK..."],
}
_MOUTH = {
    "closed": [".KFFFWWWWWWFFFK...", "..KFFFWWWWFFFK....", "...KKKKKKKKKK....."],
    "open": [".KFFFWWWWWWFFFK...", "..KFFFWPPWFFFK....", "...KKKKKKKKKK....."],
}


def _head(eyes, mouth="closed"):
    return _HEAD_TOP + _EYES[eyes] + _MOUTH[mouth]


# --- Front body (6 lines) ---------------------------------------------------

_BODY_TAIL_DOWN = [
    "..KFFFFFFFFFFK....",
    ".KFFFWWWWWWFFFK...",
    ".KFFFWWWWWWFFFK.KK",
    ".KFFKFWWWWFKFFKKFK",
    ".KFFKFFKKFFKFFFFK.",
    ".KKKKKKKKKKKKKKK..",
]
_BODY_TAIL_UP = [
    "..KFFFFFFFFFFK..KK",
    ".KFFFWWWWWWFFFK.KF",
    ".KFFFWWWWWWFFFK.KF",
    ".KFFKFWWWWFKFFKKFK",
    ".KFFKFFKKFFKFFFFK.",
    ".KKKKKKKKKKKKKKK..",
]
_BODY_ARMS_UP = [
    "KFKFFFFFFFFFFKFK..",
    "KFFFFWWWWWWFFFFK..",
    ".KKFFWWWWWWFFKK...",
    "..KFKFWWWWFKFK....",
    "..KFKFFKKFFKFK....",
    "..KKKKKKKKKKKK....",
]
_BODY_LAPTOP_LEFT = [
    "..KFFFFFFFFFFK....",
    ".KGGGGGGGGGGGGK...",
    "KFGLLLLLLLLLLGK...",
    "KKGLLLLWWLLLLGKFK.",
    ".KGLLLLLLLLLLGKKK.",
    "KKKKKKKKKKKKKKKK..",
]
_BODY_LAPTOP_RIGHT = [
    "..KFFFFFFFFFFK....",
    ".KGGGGGGGGGGGGK...",
    ".KGLLLLLLLLLLGKFK.",
    "KFGLLLLWWLLLLGKKK.",
    "KKGLLLLLLLLLLGK...",
    "KKKKKKKKKKKKKKKK..",
]

# --- Side views -------------------------------------------------------------

_RUN_A = [
    "K.............K.K...",
    "KK...........KFKFK..",
    ".KK.KKKKKKKKKKFFFFK.",
    "..KKFFSFSFSFFFFEFFPK",
    "..KFFFFFFFFFFFFFFWWK",
    "..KFFFFFFFFFFFFFKKK.",
    "..KFFFFFFFFFFFWK....",
    ".KFFKKKKKKKKFFK.....",
    "KFFK........KFFK....",
    "KKK..........KKK....",
]
_RUN_B = [
    "..............K.K...",
    ".K...........KFKFK..",
    "KFK.KKKKKKKKKKFFFFK.",
    "KFKKFFSFSFSFFFFEFFPK",
    ".KFFFFFFFFFFFFFFFWWK",
    "..KFFFFFFFFFFFFFKKK.",
    "..KFFFFFFFFFFFWK....",
    "..KKFFKKKKKFFKK.....",
    "...KFFK...KFFK......",
    "....KK.....KK.......",
]
_SLEEP_A = [
    "..K..K..KKKKKKK.....",
    ".KFKKFKKFFSFSFFKK...",
    ".KFFFFFFFFFFFFFFFK..",
    "KFFFFFFFFFFFFFFFFFK.",
    "KFEEFFEEFFFFFFFFFFK.",
    "KFFFPPFFFFFFFKKKKFK.",
    ".KWWWWWFFFFFKFFFFK..",
    "..KKKKKKKKKKKKKKK...",
]
_SLEEP_B = [
    "....................",
    "..K..K..KKKKKKK.....",
    ".KFKKFKKFFSFSFFKK...",
    "KFFFFFFFFFFFFFFFFFK.",
    "KFEEFFEEFFFFFFFFFFK.",
    "KFFFPPFFFFFFFKKKKFK.",
    ".KWWWWWFFFFFKFFFFK..",
    "..KKKKKKKKKKKKKKK...",
]

IMAGES = {
    "sit_a": _head("open") + _BODY_TAIL_DOWN,
    "sit_b": _head("open") + _BODY_TAIL_UP,
    "sit_blink": _head("lowered") + _BODY_TAIL_DOWN,
    "meow_a": _head("open", "open") + _BODY_TAIL_UP,
    "meow_b": _head("open") + _BODY_TAIL_DOWN,
    "happy_a": _head("happy", "open") + _BODY_ARMS_UP,
    "happy_b": _head("happy") + _BODY_TAIL_UP,
    "work_a": _head("lowered") + _BODY_LAPTOP_LEFT,
    "work_b": _head("lowered") + _BODY_LAPTOP_RIGHT,
    "run_a": _RUN_A,
    "run_b": _RUN_B,
    "sleep_a": _SLEEP_A,
    "sleep_b": _SLEEP_B,
}

# Animations: sequences of sprites played in a loop.
ANIMATIONS = {
    "idle": ["sit_a"] * 4 + ["sit_b"] * 4 + ["sit_a"] * 3 + ["sit_blink"],
    "question": ["meow_a", "meow_b"],
    "done": ["happy_a", "happy_b"],
    "work": ["work_a", "work_b"],
    "run": ["run_a", "run_b"],
    "sleep": ["sleep_a"] * 3 + ["sleep_b"] * 3,
}

# Small symbols drawn above the cat.
SYMBOLS = {
    "?": ["KKK.", "..K.", ".KK.", ".K..", "....", ".K.."],
    "!": ["K", "K", "K", "K", ".", "K"],
    "z": ["KKKK", "..K.", ".K..", "KKKK"],
    "star": [".K.", "KKK", ".K."],
}

# --- Colors -----------------------------------------------------------------

OUTLINE = "#2B2230"
# Light halo around the drawing, to stay readable on a dark background.
HALO = "#D9FFFFFF"

# Cat coats (one per Claude Code session).
COATS = [
    {"name": "ginger", "F": "#F0A04B", "S": "#C9742A", "W": "#FFF4E3"},
    {"name": "grey", "F": "#9AA5B4", "S": "#6F7A8A", "W": "#F4F6F8"},
    {"name": "black", "F": "#55516A", "S": "#3C3950", "W": "#E9E6F2"},
    {"name": "cream", "F": "#F3E3C3", "S": "#D9BE8E", "W": "#FFFFFF"},
    {"name": "brown", "F": "#A9764F", "S": "#7E5334", "W": "#F7EADB"},
    {"name": "blue", "F": "#7FA8C9", "S": "#5A84A6", "W": "#F0F7FC"},
]

# Kitten coats (one per subagent type).
KITTEN_COATS = [
    {"name": "pink", "F": "#F7A8C4", "S": "#DB7FA2", "W": "#FFF2F7"},
    {"name": "mint", "F": "#8FD9B6", "S": "#62B891", "W": "#F1FFF8"},
    {"name": "lavender", "F": "#B9A6F0", "S": "#917BD1", "W": "#F6F2FF"},
    {"name": "sky", "F": "#8CCBF2", "S": "#5FA6D1", "W": "#F0F9FF"},
    {"name": "lemon", "F": "#F2DC7A", "S": "#D1B74C", "W": "#FFFCE8"},
    {"name": "coral", "F": "#F59A85", "S": "#D4735D", "W": "#FFF1EE"},
]

# Laptop screen color, depending on the activity.
SCREENS = {
    "think": "#DDE3EA",
    "write": "#7CE38B",
    "read": "#7CC4FF",
    "shell": "#FFC857",
    "web": "#C59BFF",
    "agent": "#FF9ECF",
}


def palette(coat, activity="think"):
    """Character -> color table for a coat and an activity."""
    return {
        "K": OUTLINE,
        "F": coat["F"],
        "S": coat["S"],
        "W": coat["W"],
        "P": "#F58CA8",
        "E": "#2B2230",
        "G": "#5B6472",
        "L": SCREENS.get(activity, SCREENS["think"]),
    }


def draw(lines, colors, mirror=False):
    """Turn a list of lines into an image, one pixel per character."""
    width = max(len(line) for line in lines) + 2
    height = len(lines) + 2
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    filled = set()
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char in colors:
                image.setPixelColor(x + 1, y + 1, QColor(colors[char]))
                filled.add((x + 1, y + 1))
    halo = QColor(HALO)
    for x, y in filled:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (nx, ny) not in filled:
                image.setPixelColor(nx, ny, halo)
    if mirror:
        image = image.transformed(QTransform().scale(-1, 1))
    return image


def check():
    """Report inconsistent line lengths (helps while editing the drawings)."""
    errors = []
    for name, lines in IMAGES.items():
        lengths = {len(line) for line in lines}
        if len(lengths) > 1:
            errors.append(f"{name}: lines of different lengths {sorted(lengths)}")
        if max(lengths) + 2 > CELL_W or len(lines) + 2 > CELL_H:
            errors.append(f"{name}: larger than the {CELL_W}x{CELL_H} cell")
    return errors


def _preview(path, zoom=8):
    """Save a sheet of every sprite, for a visual check."""
    from PyQt6.QtGui import QGuiApplication, QPainter

    app = QGuiApplication.instance() or QGuiApplication([])
    names = list(IMAGES)
    columns = 5
    rows = (len(names) + columns - 1) // columns
    margin = 2
    step_w, step_h = (CELL_W + margin) * zoom, (CELL_H + margin) * zoom
    sheet = QImage(columns * step_w, rows * step_h * 2, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#6C8EAD"))
    painter = QPainter(sheet)
    for band, coats in enumerate((COATS, KITTEN_COATS)):
        for i, name in enumerate(names):
            coat = coats[i % len(coats)]
            activity = list(SCREENS)[i % len(SCREENS)]
            image = draw(IMAGES[name], palette(coat, activity))
            x = (i % columns) * step_w + (CELL_W - image.width()) // 2 * zoom + zoom
            y = (i // columns + band * rows) * step_h + (CELL_H - image.height()) * zoom + zoom
            painter.drawImage(x, y, image.scaled(image.width() * zoom, image.height() * zoom))
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
