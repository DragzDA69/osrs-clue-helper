# Development notes

How Clue Helper is put together and how to work on it. For what the app does
and how to use it, see [README.md](README.md).

It runs two ways from one set of sources:

- **Locally**, with a small Python server that does the heavy calculation.
- **On GitHub Pages**, as a single self-contained `index.html` that works
  offline — including saved to an iOS home screen.

## Running it

```
python server.py                 ->  http://127.0.0.1:8000
python server.py --port 9000 --no-browser
```

While it runs: `Ctrl+R` restarts (reloading `ui.py` and every solver),
`Ctrl+O` does the same and reopens the browser, `Ctrl+C` stops.

Standard library only, bound to localhost.

## How it fits together

```
ui.py               every label, every tool, every timing — one definition
web/index.html      the shell: header, home menu, tool page
web/style.css       the theme
web/app.js          the router, the menu, toasts, the solver bridge
web/tools/*.js      one file per tool's UI
web/offline/*.js    the same solvers in JS, for the page with no Python
solvers/            the Python behind the tools, one module per tool
server.py           serves web/ and docs/, answers /api/solve/<tool>
build_standalone.py bundles all of the above into index.html
index.html          GENERATED — never edit it by hand
docs/images/<tool>/ that tool's sprites
docs/images/font/   the interface font as a sprite sheet
docs/audio/         sounds
tools/              build-time scripts; nothing the site needs at runtime
```

`web/index.html` and the scripts carry `{{key}}` placeholders. `server.py`
fills them in as it serves a file; `build_standalone.py` fills them in once
when it builds `index.html`. Change a value in `ui.py` and both pages follow.

Because the placeholders stay on disk, opening `web/index.html` straight from
the filesystem shows `{{...}}` rather than the copy. Use `server.py`, or the
built `index.html`.

## Adding a tool

1. Put its sprites in `docs/images/<tool>/`. Anything under `docs/` is served
   at the matching URL — `docs/images/light_box/light_on.png` is
   `/images/light_box/light_on.png` — with no code change.
2. Add an entry to `TOOLS` in `ui.py` — `id`, `title`, `icon`, `blurb`. That
   alone gives it a card on the home screen and a page at `#/<id>`, showing a
   placeholder.
3. Write `web/tools/<id>.js`, ending with
   `registerTool("<id>", { mount(page, tool) { ... } })`. `mount` is handed the
   tool's own empty element and may return a teardown function.
4. If it needs Python, add `solvers/<id>.py` with `solve(request) -> dict` and
   name it in `solvers.MODULES`. The page reaches it with
   `await solve("<id>", payload)`, which posts to the server when one is there
   and calls `window.LOCAL_SOLVERS["<id>"]` in the standalone build.
5. For that standalone build to solve anything, the solver needs a twin in
   `web/offline/<id>.js` answering in the same shape. `server.py` never serves
   those, so locally the Python always answers. The two are separate
   implementations of one algorithm: change one, change both.

## OSRS buttons and the interface font

The game's interface font is RuneScape Plain 12, from
[RuneStar/fonts](https://github.com/RuneStar/fonts) (CC0). `tools/make_glyphs.py`
renders it at 16px -- the size at which it lands on its own pixel grid -- into
`tools/glyphs.json`, and `ui.py` turns that into one hidden `<svg>` of symbols
in the page. Any character can then be set in the game's font, in any colour,
from CSS:

```js
page.append(rsGlyph("Q"));                       // one character
page.append(osrsButton("A", { toggle: true }));  // a lever
```

A button is three background sprites in total -- `btn_bg.svg`,
`btn_bg_hover.svg`, `btn_bg_selected.svg`, built by `tools/osrs_buttons.py` --
with the glyph laid over the middle. A new label costs a character of markup,
not three more files. Everything scales from `--btn-px`, one game pixel, so the
button and its letter stay on the same grid at any size.

## The generated page

`index.html` is built from `web/`, `docs/` and `ui.py`. It carries only the
assets the page actually refers to, so an unused sprite under `docs/` costs it
nothing, and a reference to a file that is not there fails the build rather
than shipping a broken image. It is rebuilt and staged
automatically by the `pre-commit` hook, and `pre-push` refuses to push one that
does not match its sources. Install the hooks once per clone:

```
git config core.hooksPath .githooks
```

Or build it by hand: `python build_standalone.py`.
