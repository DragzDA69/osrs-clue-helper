#!/usr/bin/env python3
"""Build the OSRS-style button sprites: one SVG per label per state.

The buttons are not drawn by hand. They are composed:

    button_bg_md.svg  the stone face and its bevelled frame, as exported
    glyphs.json     the interface font, traced out of a real screenshot
    STATES          what each state does to the face and the letter

so a new button is one more character in an argument, and a change to the look
is a change here rather than in thirty files.

    python tools/osrs_buttons.py           btn_md, btn_md_hover, btn_md_selected

The letters are not baked in. There are three backgrounds in total, and the
page lays a glyph over the middle of whichever one is showing -- so a new
label costs a character of markup rather than three more files.

The small base beside it, button_bg_sm.svg, is used as it comes: it carries no
states because nothing interactive is drawn at that size yet.

Two things about the template are worth knowing before changing any of this.
It is a crop of the real A button, so the letter A is still in its texture;
the five flat paths in it are patches that hide the letter, not the face. That
is why a state tints over the top through a mask instead of recolouring those
paths: recolour them and the old A comes back, or the patches stop matching
the stone around them.

The mask is read from the template's own texture each run, so if the artwork is
re-exported the tint follows it without anything here being edited.
"""

from __future__ import annotations

import argparse
import base64
import io
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ART = ROOT / "docs" / "images" / "buttons"
TEMPLATE = ART / "button_bg_md.svg"
BTN_W, BTN_H = 35, 16
ART_W, ART_H = 68, 31
SX, SY = BTN_W / ART_W, BTN_H / ART_H
PRESS = 1

# --- the states -------------------------------------------------------------
STATES: dict[str, dict] = {
    "": {
        "tint": None,
        "shift": False,
        "bevel": None,
    },
    "hover": {
        "tint": '<rect x="0" y="0" width="35" height="16" fill="#ffffff" opacity="0.1"/>',
        "shift": True,
        "bevel": ("#2e251a", "#8a7560", 0.6),
    },
    "selected": {
        "tint": '<rect x="0" y="0" width="35" height="16" fill="url(#face-selected)" opacity="0.7"/>',
        "shift": True,
        "bevel": ("#240303", "#5e1c1c", 0.6),
        "defs": (
            '    <linearGradient id="face-selected" gradientUnits="userSpaceOnUse"\n'
            '                    x1="0" y1="0" x2="0" y2="16">\n'
            '      <stop offset="0" stop-color="#7a1414"/>\n'
            '      <stop offset="1" stop-color="#4a0808"/>\n'
            "    </linearGradient>\n"
        ),
    },
}


def face_mask() -> str:
    data = re.search(r"base64,([^\"]+)", TEMPLATE.read_text(encoding="utf-8")).group(1)
    from PIL import Image   # only the sprite build needs it, not the site build

    art = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGBA")
    px = art.load()
    w, h = art.size

    def wall(x, y):
        r, g, b, a = px[x, y]
        return a < 40 or r + g + b < 60

    inside = [[False] * w for _ in range(h)]
    stack = [(w // 2, h // 2)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or inside[y][x] or wall(x, y):
            continue
        inside[y][x] = True
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    rects = []
    for y in range(h):
        x = 0
        while x < w:
            if not inside[y][x]:
                x += 1
                continue
            start = x
            while x < w and inside[y][x]:
                x += 1
            rects.append(
                '      <rect x="{:.4f}" y="{:.4f}" width="{:.4f}" height="{:.4f}"/>'
                .format(start * SX, y * SY, (x - start) * SX, SY))
    return ('    <clipPath id="face">\n' + "\n".join(rects) + "\n    </clipPath>\n")


def bevel(shadow: str, light: str, opacity: float) -> str:
    x0, y0 = 1 * SX, 1 * SY
    x1, y1 = (ART_W - 1) * SX, (ART_H - 1) * SY
    w, h = SX, SY
    return (
        '  <g clip-path="url(#face)" opacity="{:.2f}" shape-rendering="crispEdges">\n'
        '    <rect x="{:.4f}" y="{:.4f}" width="{:.4f}" height="{:.4f}" fill="{}"/>\n'
        '    <rect x="{:.4f}" y="{:.4f}" width="{:.4f}" height="{:.4f}" fill="{}"/>\n'
        '    <rect x="{:.4f}" y="{:.4f}" width="{:.4f}" height="{:.4f}" fill="{}"/>\n'
        '    <rect x="{:.4f}" y="{:.4f}" width="{:.4f}" height="{:.4f}" fill="{}"/>\n'
        "  </g>\n".format(
            opacity,
            x0, y0, x1 - x0, h, shadow,
            x0, y0, w, y1 - y0, shadow,
            x0, y1 - h, x1 - x0, h, light,
            x1 - w, y0, w, y1 - y0, light))


def glyph_rects(rows: list[str], colour: str, shift: bool) -> str:
    height = len(rows)
    width = max(len(row) for row in rows)
    ox = (BTN_W - width * SX) / 2 + (PRESS * SX if shift else 0)
    oy = (BTN_H - height * SY) / 2 + (PRESS * SY if shift else 0)

    out = []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            if row[i] != "#":
                i += 1
                continue
            start = i
            while i < len(row) and row[i] == "#":
                i += 1
            out.append(
                '    <rect x="{:.4f}" y="{:.4f}" width="{:.4f}" height="{:.4f}" fill="{}"/>'
                .format(ox + start * SX, oy + j * SY, (i - start) * SX, SY, colour))
    return "\n".join(out)


def build(state: str, mask: str) -> str:
    spec = STATES[state]
    svg = TEMPLATE.read_text(encoding="utf-8")

    defs = mask + spec.get("defs", "")
    svg = svg.replace("  <defs>\n", "  <defs>\n" + defs, 1)

    body = ""
    if spec["tint"]:
        body += '  <g clip-path="url(#face)">{}</g>\n'.format(spec["tint"])
    if spec["bevel"]:
        body += bevel(*spec["bevel"])
    return svg.replace("</svg>", body + "</svg>")


def filename(state: str) -> str:
    return "btn_md{}.svg".format("_" + state if state else "")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Build the OSRS button backgrounds.")
    ap.add_argument("--states", default="",
                    help="comma-separated states; default is all of them")
    args = ap.parse_args(argv)

    states = args.states.split(",") if args.states else list(STATES)
    mask = face_mask()
    for state in states:
        path = ART / filename(state)
        path.write_text(build(state, mask), encoding="utf-8")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
