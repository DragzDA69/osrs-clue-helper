#!/usr/bin/env python3
"""Build index.html -- a single self-contained page with no server.

Takes web/index.html -- the same page server.py serves -- and inlines what it
would otherwise fetch: style.css, app.js, every tool script, and every sprite
and sound the page refers to, each as a data URI straight from docs/. The
result is one file that runs offline in any browser: open it from the Files app
on iOS, or let GitHub Pages serve it.

Only the assets the page actually names are carried, so an unused sprite sitting
in docs/ costs the page nothing.

Building from the served page rather than a second template is deliberate: the
two used to be separate documents, and they drifted.

    python build_standalone.py
"""

import argparse
import base64
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ui  # noqa: E402

ASSET_SUFFIXES = tuple(ui.ASSET_TYPES)

TEMPLATE = HERE / "web" / "index.html"
STYLES = HERE / "web" / "style.css"
APP = HERE / "web" / "app.js"
TOOLS_DIR = HERE / "web" / "tools"
OFFLINE_DIR = HERE / "web" / "offline"
OUT = HERE / "index.html"
STYLESHEET_TAG = '<link rel="stylesheet" href="/style.css">'
SCRIPT_TAG = '<script src="/app.js"></script>'
DOCTYPE = "<!doctype html>"
BANNER = """<!--
  GENERATED FILE -- DO NOT EDIT.

  Built by build_standalone.py from:
      web/index.html   markup        web/tools/*.js    the tools
      web/style.css    styles        web/offline/*.js  solvers, in JS
      ui.py            every label, tool and timing
      docs/*           sprites and sounds

  Edit those, then run:  python build_standalone.py
-->
"""


def fail(message: str):
    raise SystemExit("Error: " + message)


def data_uri(path: Path) -> str:
    media = ui.ASSET_TYPES[path.suffix.lower()]
    return "data:{};base64,{}".format(
        media, base64.b64encode(path.read_bytes()).decode("ascii"))


def tool_scripts() -> list[tuple[str, str]]:
    return [(name, (TOOLS_DIR / name).read_text(encoding="utf-8"))
            for name in ui.tool_scripts()]


def offline_solvers() -> list[tuple[str, str]]:
    if not OFFLINE_DIR.is_dir():
        return []
    return [(p.name, p.read_text(encoding="utf-8"))
            for p in sorted(OFFLINE_DIR.glob("*.js"))]


ASSET_REFERENCE = re.compile(
    r"/(?:images|audio)/[\w()./-]+?(?:" +
    "|".join(suffix.replace(".", r"\.") for suffix in ASSET_SUFFIXES) + ")")


def check_assets(page: str) -> list[str]:
    known = ui.assets()
    return sorted({ref for ref in ASSET_REFERENCE.findall(page) if ref not in known})


def _build(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Build the standalone single-file app.")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    page = TEMPLATE.read_text(encoding="utf-8")
    for tag in (STYLESHEET_TAG, SCRIPT_TAG, DOCTYPE):
        if tag not in page:
            fail("Could not rebuild the page: {} is missing {}.".format(TEMPLATE.name, tag))

    try:
        styles = STYLES.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        tools = tool_scripts()
        offline = offline_solvers()
    except FileNotFoundError as exc:
        fail("Could not read a file needed to rebuild the page.\nDetails: {}".format(exc))

    try:
        page = ui.render(page, TEMPLATE.name)
        styles = ui.render(styles, STYLES.name)
        app = ui.render(app, APP.name)
        tools = [(name, ui.render(text, name)) for name, text in tools]
        offline = [(name, ui.render(text, name)) for name, text in offline]
    except KeyError as exc:
        fail("Could not rebuild the page because a UI label is missing.\nDetails: {}".format(exc))

    if "</" in styles:
        fail("Could not rebuild the page: the stylesheet contains invalid HTML closing text.")
    for name, text in [("app.js", app)] + tools + offline:
        if "</script" in text.lower():
            fail("Could not rebuild the page: {} contains invalid script closing text.".format(name))

    scripts = ("<script>" + app + "</script>"
               + "".join("<script>" + text + "</script>" for _, text in offline)
               + "".join("<script>" + text + "</script>" for _, text in tools))

    page = page.replace(STYLESHEET_TAG, "<style>" + styles + "</style>", 1)
    page = page.replace(SCRIPT_TAG, scripts, 1)
    tags = ui.tool_script_tags()
    if tags:
        page = page.replace(tags, "", 1)

    missing = check_assets(page)
    if missing:
        fail("Could not rebuild the page. Nothing under docs/ answers to: {}".format(
            ", ".join(missing)))
    for route, path in sorted(ui.assets().items(), key=lambda item: -len(item[0])):
        if route in page:
            page = page.replace(route, data_uri(path))

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
