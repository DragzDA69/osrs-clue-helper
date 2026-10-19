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

# The two halves of the name are separate because the header styles them
# differently; app_name joins them for the title bars.
BRAND_LEAD = "Clue"
BRAND_TAIL = "Helper"

# How long a toast sits on screen, and how long it takes to slide in or out.
# The fade drives both the CSS transition and the JS that removes the element
# afterwards, so the two can never fall out of step.
TOAST_MS = 2000
TOAST_FADE_MS = 220

# Every image the pages use, by the name the page refers to it by. The build
# inlines each of these as a data URI; the server hands them out from web/images.
# Keys are the URL path, values the file under web/images/.
IMAGES: dict[str, str] = {
    "/images/light_box.png": "light_box.png",
    "/images/puzzle_box.png": "puzzle_box.png",
}

# The home screen menu, in the order it is shown. Each tool becomes a card on
# the home page and a page of its own at #/<id>.
#
#     id       the route, and the key app.js looks the tool up by
#     title    the card's label, the page's heading and the browser title
#     icon     a key of IMAGES
#     blurb    one line under the title on the card
TOOLS: list[dict[str, str]] = [
    {
        "id": "light-box",
        "title": "Light Box",
        "icon": "/images/light_box.png",
        "blurb": "Work out the switch presses that light every panel.",
    },
    {
        "id": "puzzle-box",
        "title": "Puzzle Box",
        "icon": "/images/puzzle_box.png",
        "blurb": "Solve the sliding tile puzzle, move by move.",
    },
]

VALUES: dict[str, object] = {
    # -- identity ----------------------------------------------------------
    "app_name": "{} {}".format(BRAND_LEAD, BRAND_TAIL),
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
    missing = sorted({m.group(1) for m in PLACEHOLDER.finditer(text)} - set(VALUES))
    if missing:
        raise KeyError("{}: no such value{}: {}".format(
            where or "template", "" if len(missing) == 1 else "s", ", ".join(missing)))
    return PLACEHOLDER.sub(lambda m: str(VALUES[m.group(1)]), text)


if __name__ == "__main__":
    for key, value in VALUES.items():
        print("{:<24} {}".format(key, value))
