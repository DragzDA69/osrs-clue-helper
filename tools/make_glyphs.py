#!/usr/bin/env python3
"""Render the RuneScape interface font to the pixel grid, into glyphs.json.

The font is RuneScape Plain 12 (cache name p12_full), from RuneStar/fonts,
which publishes the game's own fonts under CC0. At 16px it renders exactly the
bitmap the game draws: an 'A' comes out 6x10, matching the letters traced off a
real light box screenshot pixel for pixel.

    python tools/make_glyphs.py            A-Z, a-z, 0-9
    python tools/make_glyphs.py --sheet    ... and the sprite sheet

Each glyph is stored twice over: `rows` is the ink, trimmed to the glyph's own
box, and `left`/`top` say where that box sits against the pen position and the
baseline. A single letter on a button only needs `rows`; anything that sets a
word needs the offsets, or the descenders sit wrong.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONT = HERE / "RuneScape-Plain-12.ttf"
OUT = HERE / "glyphs.json"
SHEET_DIR = ROOT / "docs" / "images" / "font"
SIZE = 16
INK = 110          # a pixel is on above this, off below; the font is 1-bit
ORIGIN = (12, 12)
CANVAS = (56, 56)
CHARS = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
         "abcdefghijklmnopqrstuvwxyz"
         "0123456789")


def render(font, ch):
    img = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(img).text(ORIGIN, ch, font=font, fill=255)
    box = img.getbbox()
    if box is None:                     # a space, or a character the font lacks
        return None
    x0, y0, x1, y1 = box
    crop = img.crop(box)
    rows = ["".join("#" if crop.getpixel((x, y)) > INK else "."
                    for x in range(crop.width))
            for y in range(crop.height)]
    return {"rows": rows, "left": x0 - ORIGIN[0], "top": y0 - ORIGIN[1]}


def sprite_sheet(glyphs: dict) -> None:
    cols = 16
    cell_w = max(len(g["rows"][0]) for g in glyphs.values()) + 2
    tops = [g["top"] for g in glyphs.values()]
    bottoms = [g["top"] + len(g["rows"]) for g in glyphs.values()]
    cell_h = max(bottoms) - min(tops) + 2
    baseline = -min(tops) + 1

    chars = list(glyphs)
    rows_of = -(-len(chars) // cols)
    sheet = Image.new("RGBA", (cols * cell_w, rows_of * cell_h), (0, 0, 0, 0))
    px = sheet.load()

    index = {}
    for n, ch in enumerate(chars):
        cx, cy = (n % cols) * cell_w, (n // cols) * cell_h
        glyph = glyphs[ch]
        ox, oy = cx + 1, cy + baseline + glyph["top"]
        for j, row in enumerate(glyph["rows"]):
            for i, cell in enumerate(row):
                if cell == "#":
                    px[ox + i, oy + j] = (255, 255, 255, 255)
        index[ch] = {"x": ox, "y": cy, "w": len(glyph["rows"][0]), "h": cell_h}

    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(SHEET_DIR / "osrs_plain12.png")
    (SHEET_DIR / "osrs_plain12.json").write_text(json.dumps({
        "_comment": "Sprite sheet for RuneScape Plain 12. White ink on "
                    "transparent, so it can be tinted. Cells are uniform; "
                    "each glyph sits on the cell's shared baseline.",
        "cell": {"width": cell_w, "height": cell_h, "baseline": baseline},
        "glyphs": index,
    }, indent=2), encoding="utf-8")
    print("wrote", (SHEET_DIR / "osrs_plain12.png").relative_to(ROOT),
          "({}x{})".format(*sheet.size))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Render the font to glyphs.json.")
    ap.add_argument("--sheet", action="store_true", help="also write the sprite sheet")
    args = ap.parse_args(argv)

    font = ImageFont.truetype(str(FONT), SIZE)
    glyphs = {}
    for ch in CHARS:
        glyph = render(font, ch)
        if glyph is None:
            print("skipped (not in the font):", ch)
            continue
        glyphs[ch] = glyph

    OUT.write_text(json.dumps({
        "_comment": [
            "The Old School RuneScape interface font, Plain 12 (p12_full).",
            "Rendered from tools/RuneScape-Plain-12.ttf by tools/make_glyphs.py.",
            "The font is from github.com/RuneStar/fonts, published under CC0.",
            "'#' is ink, '.' is nothing. 'left' and 'top' place the rows",
            "against the pen position and the baseline.",
        ],
        "font": "RuneScape Plain 12",
        "size": SIZE,
        "glyphs": glyphs,
    }, indent=2), encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT), "with", len(glyphs), "glyphs")

    if args.sheet:
        sprite_sheet(glyphs)


if __name__ == "__main__":
    main()
