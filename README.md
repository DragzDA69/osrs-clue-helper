# osrs-clue-helper

Clue Helper — a multi-tool web app for completing clue scrolls in Old School
RuneScape. It runs two ways from one set of sources:

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
web/tools/*.js      one file per tool's UI (none yet)
web/images/*.png    tool icons, display size
solvers/            the Python behind the tools, one module per tool
server.py           serves web/ and answers /api/solve/<tool>
build_standalone.py bundles all of the above into index.html
index.html          GENERATED — never edit it by hand
docs/images/        the original full-size sprites
```

`web/index.html` and the scripts carry `{{key}}` placeholders. `server.py`
fills them in as it serves a file; `build_standalone.py` fills them in once
when it builds `index.html`. Change a value in `ui.py` and both pages follow.

Because the placeholders stay on disk, opening `web/index.html` straight from
the filesystem shows `{{...}}` rather than the copy. Use `server.py`, or the
built `index.html`.

## Adding a tool

1. Add an entry to `TOOLS` in `ui.py` — `id`, `title`, `icon`, `blurb` — and
   its icon to `IMAGES`. That alone gives it a card on the home screen and a
   page at `#/<id>`, showing a placeholder.
2. Drop its icon in `web/images/` (a copy of the sprite, scaled to ~128px).
3. Write `web/tools/<id>.js`, ending with
   `registerTool("<id>", { mount(page, tool) { ... } })`. `mount` is handed the
   tool's own empty element and may return a teardown function.
4. If it needs Python, add `solvers/<id>.py` with `solve(request) -> dict` and
   name it in `solvers.MODULES`. The page reaches it with
   `await solve("<id>", payload)`, which posts to the server when one is there
   and calls `window.LOCAL_SOLVERS["<id>"]` in the standalone build.

## The generated page

`index.html` is built from `web/` and `ui.py`. It is rebuilt and staged
automatically by the `pre-commit` hook, and `pre-push` refuses to push one that
does not match its sources. Install the hooks once per clone:

```
git config core.hooksPath .githooks
```

Or build it by hand: `python build_standalone.py`.
