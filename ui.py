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
# Every image and sound lives under docs/, laid out by the tool it belongs to.
# It is the one copy of each asset: the server hands them out from here and the
# standalone build inlines them from here.
DOCS = HERE / "docs"

# The two halves of the name are separate because the header styles them
# differently; app_name joins them for the title bars.
BRAND_LEAD = "Clue"
BRAND_TAIL = "Helper"

# How long a toast sits on screen, and how long it takes to slide in or out.
# The fade drives both the CSS transition and the JS that removes the element
# afterwards, so the two can never fall out of step.
TOAST_MS = 2000
TOAST_FADE_MS = 220

# What a page may ask for, by extension. Anything else under docs/ -- notes, a
# README, a spare .psd -- is simply not part of the app and is never served.
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
    """Every asset under docs/, keyed by the URL a page refers to it by.

    The URL mirrors the folder: docs/images/light_box/light_on.png is asked for
    as /images/light_box/light_on.png. Nothing is listed by hand, so dropping a
    sprite into docs/ is all it takes to be able to use it -- and the server
    still works from a fixed list built here rather than resolving whatever
    path a browser sends it.
    """
    found: dict[str, Path] = {}
    if not DOCS.is_dir():
        return found
    for path in sorted(DOCS.rglob("*")):
        if path.is_file() and path.suffix.lower() in ASSET_TYPES:
            found["/" + path.relative_to(DOCS).as_posix()] = path
    return found


def tool_scripts() -> list[str]:
    """Every web/tools/*.js, in name order so a build is reproducible."""
    folder = WEB / "tools"
    return sorted(p.name for p in folder.glob("*.js")) if folder.is_dir() else []


def tool_script_tags() -> str:
    """The <script> tags that load the tools, for the served page. They come
    after app.js, which is what lets each one register itself on load.

    The standalone build inlines the same files instead, and strips this.
    """
    return "".join('<script src="/tools/{}"></script>'.format(name)
                   for name in tool_scripts())


# The app's own mark: the browser tab, the iOS home screen, and the header
# beside the name.
APP_ICON = "/images/clue_scroll_(master).png"

# The home screen menu, in the order it is shown. Each tool becomes a card on
# the home page and a page of its own at #/<id>.
#
#     id       the route, and the key app.js looks the tool up by
#     title    the card's label, the page's heading and the browser title
#     icon     the URL of its sprite under docs/
#     blurb    one line under the title on the card
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
        "blurb": "Solve the sliding tile puzzle, move by move.",
    },
]

VALUES: dict[str, object] = {
    # -- identity ----------------------------------------------------------
    "app_name": "{} {}".format(BRAND_LEAD, BRAND_TAIL),
    "app_icon": APP_ICON,
    "brand_lead": BRAND_LEAD,
    "brand_tail": BRAND_TAIL,
    "developer_credit": "Developed by Dragz",
    # Two sentences, kept apart: the header puts each in its own inline-block,
    # so a line break lands between them rather than mid-sentence.
    "app_description_lead": "Tools for solving Old School RuneScape clue scrolls.",
    "app_description_tail": "Pick a tool to begin.",

    # -- home --------------------------------------------------------------
    "home_heading": "Tools",
    "home_hint": "Choose the clue step you are stuck on.",
    "btn_back": "All tools",
    "title_back": "Back to all tools",

    # -- tool pages --------------------------------------------------------
    "tool_placeholder_heading": "Nothing here yet",
    "tool_placeholder_body":
        "This tool is still being built. The page, the route and the layout "
        "are in place, so the solver can drop straight in.",
    "msg_unknown_tool": "That tool does not exist.",

    # -- shared controls ---------------------------------------------------
    "title_clear": "Clear",
    "msg_copy_failed": "Clipboard blocked by the browser",
    "toast_copied_suffix": " was copied to the clipboard",

    # -- timings (milliseconds; used by both the CSS and the scripts) ------
    "toast_ms": TOAST_MS,
    "toast_fade_ms": TOAST_FADE_MS,

    # -- data the scripts read ---------------------------------------------
    # Rendered into app.js, so the menu is defined once, here.
    "tools_json": json.dumps(TOOLS, separators=(",", ":")),
}

PLACEHOLDER = re.compile("[{]{2}([a-z0-9_]+)[}]{2}")


def render(text: str, where: str = "") -> str:
    """Replace every {{key}} in `text`. An unknown key is an error, so a typo
    fails the build instead of shipping a literal `{{key}}` to the page."""
    values = dict(VALUES, tool_scripts=tool_script_tags())
    missing = sorted({m.group(1) for m in PLACEHOLDER.finditer(text)} - set(values))
    if missing:
        raise KeyError("{}: no such value{}: {}".format(
            where or "template", "" if len(missing) == 1 else "s", ", ".join(missing)))
    return PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), text)


if __name__ == "__main__":
    for key, value in dict(VALUES, tool_scripts=tool_script_tags()).items():
        print("{:<24} {}".format(key, value))
