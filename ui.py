#!/usr/bin/env python3
"""Every user-facing string, tool definition and UI setting, in one place.

The served page and the standalone single-file build are separate documents,
so a label or a timing written into each of them drifts the moment one is
edited. Instead both carry `{{key}}` placeholders, and the values live here:

    server.py             fills them in as it serves a file
    build_standalone.py   fills them in once, when it builds index.html

Change a value here and both pages follow. HTML is allowed in a value -- it is
substituted before the browser ever sees it -- which is what lets a hint keep
its <kbd> tag. Numbers are substituted bare, so a key can be dropped straight
into CSS or JS: `}, {{toast_ms}});`.

TOOLS is the menu. Adding an entry here is all it takes for the home screen to
grow a card and the router to grow a page: the list is rendered into app.js as
JSON, so Python and the browser can never disagree about what tools exist.

Templated files keep their placeholders on disk, so opening web/index.html
straight from the filesystem shows `{{...}}` rather than the copy. Serve it
with server.py, or use the built index.html.

    python ui.py          print every key and its value
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
DOCS = HERE / "docs"
BRAND_LEAD = "Clue"
BRAND_TAIL = "Helper"
TOAST_MS = 2000
TOAST_FADE_MS = 220
ASSET_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}


def assets() -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not DOCS.is_dir():
        return found
    for path in sorted(DOCS.rglob("*")):
        if path.is_file() and path.suffix.lower() in ASSET_TYPES:
            found["/" + path.relative_to(DOCS).as_posix()] = path
    return found


def tool_scripts() -> list[str]:
    folder = WEB / "tools"
    return sorted(p.name for p in folder.glob("*.js")) if folder.is_dir() else []


def tool_script_tags() -> str:
    return "".join('<script src="/tools/{}"></script>'.format(name)
                   for name in tool_scripts())


# --- the OSRS interface font ------------------------------------------------
GLYPH_DATA = HERE / "tools" / "glyphs.json"


def glyph_symbols() -> str:
    if not GLYPH_DATA.exists():
        return ""
    data = json.loads(GLYPH_DATA.read_text(encoding="utf-8"))

    out = ['<svg xmlns="http://www.w3.org/2000/svg" class="glyph-sheet" aria-hidden="true">']
    for char, glyph in data["glyphs"].items():
        rows = glyph["rows"]
        width, height = len(rows[0]), len(rows)
        segments = []
        for y, row in enumerate(rows):
            x = 0
            while x < len(row):
                if row[x] != "#":
                    x += 1
                    continue
                start = x
                while x < len(row) and row[x] == "#":
                    x += 1
                segments.append("M{} {}h{}v1h-{}z".format(start, y, x - start, x - start))
        out.append('<symbol id="g-{}" viewBox="0 0 {} {}">'
                   '<path d="{}"/></symbol>'.format(
                       symbol_id(char), width, height, "".join(segments)))
    out.append("</svg>")
    return "".join(out)


def symbol_id(char: str) -> str:
    return char if not char.islower() else char.upper() + "-lower"


APP_ICON = "/images/clue_scroll_(master).png"
APP_ICON_MOBILE = "/images/app_icon.png"
TOOLS: list[dict[str, str]] = [
    {
        "id": "light-box",
        "title": "Light Box",
        "icon": "/images/light_box/light_box.png",
        "blurb": "Work out the switch presses that light every panel.",
    },
    {
        "id": "puzzle-box",
        "title": "Puzzle Box",
        "icon": "/images/puzzle_box/puzzle_box.png",
        "blurb": "Solve the sliding tile puzzle box, move by move.",
    },
    {
        "id": "anagram",
        "title": "Anagram",
        "icon": "/images/empty_scroll.png",
        "blurb": "Unscramble letters and phrases to find the correct NPC.",
    },
    {
        "id": "coordinates",
        "title": "Coordinates",
        "icon": "/images/coordinates/sextant.png",
        "blurb": "Find the correct location using the given coordinates.",
    },
    {
        "id": "cryptic-clue",
        "title": "Cryptic Clue",
        "icon": "/images/cryptic_clue/cake_of_guidance.png",
        "blurb": "Solve the cryptic clue to find the correct location.",
    },
    {
        "id": "falo-the-bard",
        "title": "Falo the Bard",
        "icon": "/images/falo_the_bard/falo_the_bard.png",
        "blurb": "Find the correct item to bring to Falo the Bard.",
    },
    {
        "id": "emote-clue",
        "title": "Emote Clues",
        "icon": "/images/emote_clue/mime.png",
        "blurb": "Find location and gear needed for an emote clue.",
    },
    {
        "id": "sherlock",
        "title": "Sherlock",
        "icon": "/images/sherlock/sherlock.png",
        "blurb": "Complete Sherlock challenge scrolls.",
    },
    {
        "id": "hot-cold",
        "title": "Hot & Cold",
        "icon": "/images/hot_cold/strange_device.png",
        "blurb": "Follow the hot and cold clues to find the treasure.",
    }
]

VALUES: dict[str, object] = {
    # -- identity ----------------------------------------------------------
    "app_name": "{} {}".format(BRAND_LEAD, BRAND_TAIL),
    "app_icon": APP_ICON,
    "app_icon_mobile": APP_ICON_MOBILE,
    "brand_lead": BRAND_LEAD,
    "brand_tail": BRAND_TAIL,
    "developer_credit": "Developed by Dragz",
    "app_description_lead": "Old School RuneScape clue scroll solving tools.",
    "app_description_tail": "Pick a tool to begin.",

    # -- home --------------------------------------------------------------
    "home_heading": "Tools",
    "home_hint": "Choose the clue step you are stuck on.",
    "btn_back": "All tools",
    "title_back": "Back to all tools",
    "toggle_sound": "Enable Sounds",

    # -- tool pages --------------------------------------------------------
    "tool_placeholder_heading": "Nothing here yet",
    "tool_placeholder_body": "This tool is still being built. The page, the route and the layout are in place, so the solver can drop straight in.",
    "msg_unknown_tool": "That tool does not exist.",

    # -- light box ---------------------------------------------------------
    "lb_prompt": "Use this step by step interactive light box to mimic lights and levers in game to find the final solution.",
    "lb_enter_start": "Enter your starting combination",
    "lb_step": "Lever {label}: tap every light that is on after pressing it.",
    "lb_step_count": "{n} lit",
    "lb_ready": "All eight levers recorded. Press Solve.",
    "lb_few_title": "Only {n} lit for lever {label}?",
    "lb_few_message": "A lever usually changes more lights than that, so this often means a light was missed.",
    "lb_few_note": "Moving on locks lever {label} in as it stands.",
    "btn_continue": "Continue anyway",
    "lb_solving": "Solving…",
    "lb_answer": "Press the levers in this order to solve:",
    "lb_answer_none": "Every light is already on.",
    "lb_light_label": "Light, row {r}, column {c}",
    "lb_lever_label": "Lever {label}",
    "btn_reset": "Reset",
    "btn_set_start": "Set Start",
    "btn_solve": "Solve",

    # -- confirming something that throws work away ------------------------
    "btn_cancel": "Cancel",
    "btn_confirm": "Confirm",
    "msg_cannot_undo": "This cannot be undone.",
    "lb_reset_title": "Reset the board?",
    "lb_reset_message": "Every light and lever goes back to how it started.",
    "btn_confirm_reset": "Reset board",

    # -- shared controls ---------------------------------------------------
    "title_clear": "Clear",
    "msg_copy_failed": "Clipboard blocked by the browser",
    "toast_copied_suffix": " was copied to the clipboard",

    # -- timings (milliseconds; used by both the CSS and the scripts) ------
    "toast_ms": TOAST_MS,
    "toast_fade_ms": TOAST_FADE_MS,

    # -- data the scripts read ---------------------------------------------
    # Substituted into app.js as a bare literal, not inside a quoted string: JSON
    # is valid JS, whereas an apostrophe or quote in a blurb ("Falo the Bard's")
    # would end a string early and take the whole page down. "<" is escaped so no
    # value can close the <script> tag the standalone build inlines app.js into.
    "tools_json": json.dumps(TOOLS, separators=(",", ":")).replace("<", "\\u003c"),
}

PLACEHOLDER = re.compile("[{]{2}([a-z0-9_]+)[}]{2}")


def render(text: str, where: str = "") -> str:
    values = dict(VALUES,
                  tool_scripts=tool_script_tags(),
                  glyph_symbols=glyph_symbols())
    missing = sorted({m.group(1) for m in PLACEHOLDER.finditer(text)} - set(values))
    if missing:
        raise KeyError("{}: no such value{}: {}".format(
            where or "template", "" if len(missing) == 1 else "s", ", ".join(missing)))
    return PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), text)


if __name__ == "__main__":
    for key, value in dict(
            VALUES,
            tool_scripts=tool_script_tags(),
            glyph_symbols="<svg>...{} glyphs...</svg>".format(
                len(json.loads(GLYPH_DATA.read_text(encoding="utf-8"))["glyphs"]))).items():
        print("{:<24} {}".format(key, value))
