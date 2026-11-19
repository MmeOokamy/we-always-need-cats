#!/usr/bin/env python3
"""Builds art/reaper-frames.png, the frames of the Reapers look, from the
animated GIF art/reaper.gif (see the README for its author).

Every frame of the GIF, turned to face right like the other drawings, is
laid side by side in one PNG strip; identical frames that follow each other
are kept once. sprites_reapers.py reads the strip with Qt (no Pillow needed
to run the cats). Requires Pillow.

Usage: python3 tools/make_reaper_frames.py
"""

import json
import os

from PIL import Image, ImageChops, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "art", "reaper.gif")
STRIP = os.path.join(ROOT, "art", "reaper-frames.png")
INDEX = os.path.join(ROOT, "art", "reaper-frames.json")


def main():
    gif = Image.open(SOURCE)
    frames, index = [], []
    for i in range(gif.n_frames):
        gif.seek(i)
        frame = ImageOps.mirror(gif.convert("RGBA"))
        if frames and ImageChops.difference(frame, frames[-1]).getbbox() is None:
            index.append(len(frames) - 1)
            continue
        frames.append(frame)
        index.append(len(frames) - 1)
    w, h = frames[0].size
    strip = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        strip.paste(frame, (i * w, 0))
    strip.save(STRIP, optimize=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        # GIF frame number -> strip frame number, and the frame size.
        json.dump({"width": w, "height": h, "frames": index}, f)
        f.write("\n")
    print(f"{len(frames)} frames ({w}x{h}) -> {STRIP}")


if __name__ == "__main__":
    main()
