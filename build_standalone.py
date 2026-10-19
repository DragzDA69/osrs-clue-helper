#!/usr/bin/env python3
"""Build index.html -- a single self-contained page with no server.

Takes web/index.html -- the same page server.py serves -- and inlines what it
would otherwise fetch: style.css, app.js, every tool script, and each image as
a data URI. The result is one file that runs offline in any browser: open it
from the Files app on iOS, or let GitHub Pages serve it.

Building from the served page rather than a second template is deliberate: the
two used to be separate documents, and they drifted.

    python build_standalone.py
"""

import argparse
import base64
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ui  # noqa: E402

TEMPLATE = HERE / "web" / "index.html"
STYLES = HERE / "web" / "style.css"
APP = HERE / "web" / "app.js"
TOOLS_DIR = HERE / "web" / "tools"
IMAGES = HERE / "web" / "images"
ICON = HERE / "icon.png"
OUT = HERE / "index.html"

# The served page's own tags are what gets swapped out, so there are no
# build markers to keep in sync -- and nothing for a browser to choke on if
# web/index.html is opened directly.
STYLESHEET_TAG = '<link rel="stylesheet" href="/style.css">'
SCRIPT_TAG = '<script src="/app.js"></script>'
ICON_URL = "/icon.png"
DOCTYPE = "<!doctype html>"

# Stamped at the top of the output. A generated file sitting in the repo root
# looks exactly like a source file, and an edit made here is destroyed by the
# next build without warning -- so the file says so itself.
BANNER = """<!--
  GENERATED FILE -- DO NOT EDIT.

  Built by build_standalone.py from:
      web/index.html   markup        web/tools/*.js   the tools
      web/style.css    styles        web/images/*     icons
      ui.py            every label, tool and timing

  Edit those, then run:  python build_standalone.py
-->
"""


def fail(message: str):
    raise SystemExit("Error: " + message)


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def tool_scripts() -> list[tuple[str, str]]:
    """Every web/tools/*.js, in name order so a build is reproducible."""
    if not TOOLS_DIR.is_dir():
        return []
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(TOOLS_DIR.glob("*.js"))]


def _build(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Build the standalone single-file app.")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    page = TEMPLATE.read_text(encoding="utf-8")
    for tag in (STYLESHEET_TAG, SCRIPT_TAG, ICON_URL, DOCTYPE):
        if tag not in page:
            fail("Could not rebuild the page: {} is missing {}.".format(TEMPLATE.name, tag))

    try:
        styles = STYLES.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        tools = tool_scripts()
    except FileNotFoundError as exc:
        fail("Could not read a file needed to rebuild the page.\nDetails: {}".format(exc))

    # Copy and timings go in before the images do, so no base64 payload is
    # scanned for placeholders.
    try:
        page = ui.render(page, TEMPLATE.name)
        styles = ui.render(styles, STYLES.name)
        app = ui.render(app, APP.name)
        tools = [(name, ui.render(text, name)) for name, text in tools]
    except KeyError as exc:
        fail("Could not rebuild the page because a UI label is missing.\nDetails: {}".format(exc))

    if "</" in styles:
        fail("Could not rebuild the page: the stylesheet contains invalid HTML closing text.")
    for name, text in [("app.js", app)] + tools:
        if "</script" in text.lower():
            fail("Could not rebuild the page: {} contains invalid script closing text.".format(name))

    # Images: the icon the page links to, then every tool icon ui.py names.
    # Each is replaced everywhere it appears, so a path written in the markup
    # and the same path inside the rendered tool list both resolve offline.
    try:
        icon = data_uri(ICON)
        pictures = {route: data_uri(IMAGES / name) for route, name in ui.IMAGES.items()}
    except FileNotFoundError as exc:
        fail("Could not rebuild the page: an image is missing.\nDetails: {}".format(exc))

    # A tool registers itself on load, so its script must come after app.js.
    scripts = "<script>" + app + "</script>" + "".join(
        "<script>" + text + "</script>" for _, text in tools)

    page = page.replace(STYLESHEET_TAG, "<style>" + styles + "</style>", 1)
    page = page.replace(SCRIPT_TAG, scripts, 1)
    page = page.replace(ICON_URL, icon)     # favicon, home icon, apple touch icon
    for route, uri in pictures.items():
        page = page.replace(route, uri)
    # The banner goes in last, so nothing above can scan it for tags.
    page = page.replace(DOCTYPE, DOCTYPE + "\n" + BANNER, 1)

    args.out.write_text(page, encoding="utf-8", newline="\n")
    print("{} has been recompiled with the latest changes.".format(args.out.name))


def main(argv=None) -> None:
    try:
        _build(argv)
    except (OSError, UnicodeError) as exc:
        fail("Could not rebuild the page. Check that the required files are available "
             "and the output file can be saved.\nDetails: {}".format(exc))


if __name__ == "__main__":
    main()
