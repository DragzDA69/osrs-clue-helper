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

Most edits need only a browser refresh: files in `web/` are read on every
request, and `ui.py` is reloaded as soon as it changes. Restart for what the
server loads once — a change to a solver in `solvers/`, and any *new* file (a
tool script, an image, a sound), because the list of what it serves is built at
start.

Standard library only, bound to localhost.

## How it fits together

```
ui.py               every label, every tool, every timing — one definition
web/index.html      the shell: header, home menu, tool page
web/style.css       the theme
web/app.js          the router, the menu, toasts, sound, the solver bridge
web/tools/*.js      one file per tool's UI
web/offline/*.js    the same solvers in JS, for the page with no Python
solvers/            the Python behind the tools, one module per tool
server.py           serves web/ and docs/, answers /api/solve/<tool>
build_standalone.py bundles all of the above into index.html
index.html          GENERATED — never edit it by hand
comparison.js       the original solver, the reference the ports follow
docs/images/<tool>/ that tool's sprites
docs/images/*.png   loose images: the app's icons (app_icon.png is the Home
                    Screen one) and the empty scroll
docs/images/font/   the interface font as a sprite sheet
docs/audio/         sounds
screenshots/        the README's pictures; the site never loads them
tools/              build-time scripts; nothing the site needs at runtime
```

`web/index.html` and the scripts carry `{{key}}` placeholders. `server.py`
fills them in as it serves a file; `build_standalone.py` fills them in once
when it builds `index.html`. Change a value in `ui.py` and both pages follow.

Values go in exactly as written, with no escaping, so mind where a placeholder
sits. Inside a quoted JS string a value must not contain that quote (or a
backslash, or a line break): an apostrophe in a value placed in `'...'` ends the
string early and takes the whole page down. That is why the tool list goes in as
a bare literal, `const TOOLS = {{tools_json}};`, and not inside
`JSON.parse('...')` — JSON is valid JS, so any blurb is safe, and `ui.py`
escapes `<` so none can close the `<script>` the standalone build inlines it
into.

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
6. Add it to the **Tools** table in `README.md`, linked to a section of its own.
   A placeholder section is fine until the tool is built.

## The Light Box request

The solver is sent one request, `{ state, switches }`, and the start step added
nothing to it:

- Every lever has a `before` and an `after` — the board before and after it was
  pulled. Their difference is exactly the lights that lever toggles.
- The first reading is the **starting combination**. The player enters it and
  locks it in with Set Start before any lever can be chosen — a box need not
  begin dark, so it cannot be assumed — and the tool then selects lever A.
  The start is lever A's `before`; every later `before` is the previous lever's
  `after`. It is never sent on its own: it is already inside A's mask.
- `state` is the board after H, the one the answer is worked out from.

`solvers/light_box.py` and `web/offline/light-box.js` read that identically, and
agree field for field on the same request. The shape follows `comparison.js`,
which asks for the starting board first and then once after each lever.

## The page around a tool

The shell draws everything outside a tool's body; a tool's `mount` is handed
only the body.

- **The header** at the top is the app's. It reads the same on every page — a
  tool names itself in its own title instead — and only the browser tab's title
  follows the page.
- **A tool's title** — its icon and name from `TOOLS`, centred — stays pinned to
  the top of the window while a long page scrolls under it. The home screen's
  "Tools" title is left to scroll away with its page.

## Sound

Sounds are off until the **Enable Sounds** switch is turned on, and the choice is
remembered in `localStorage` under `clue-helper.sound` (`"1"` is on). A tool
plays one with `playSound("/audio/<file>")`, which does nothing while the switch
is off, so a tool never checks for itself. The earlier key, `clue-helper.mute`,
held the opposite meaning and is deliberately never read.

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
