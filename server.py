#!/usr/bin/env python3
"""Local web app for Clue Helper.

Serves web/index.html and answers its requests by calling the solvers in
solvers/, so the page and the Python behind it can never drift apart.

    python server.py             ->  http://127.0.0.1:8000
    python server.py --port 9000 --no-browser

While it is running:

    Ctrl+R   restart -- reloads ui.py and every solver
    Ctrl+O   the same, and reopen the page in a browser
    Ctrl+C   stop

Standard library only, and it binds to localhost: nothing is exposed off
this machine.
"""

from __future__ import annotations

import importlib
import json
import queue
import socket
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import msvcrt
except ImportError:   # not Windows: the hotkeys are skipped, Ctrl+C still works
    msvcrt = None

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
sys.path.insert(0, str(HERE))

import ui  # noqa: E402  (needs HERE on sys.path first)
import solvers  # noqa: E402

MAX_BODY = 256 * 1024


def info(message: str) -> None:
    print(message, flush=True)


def fail(message: str):
    raise SystemExit("Error: " + message)


class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can bind over a live listener and serve stale pages.
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self) -> None:
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


# Explicit allowlist: the server never resolves a client-supplied path.
# The flag says whether the file carries {{...}} placeholders for ui.py
# to fill in on the way out.
STATIC = {
    "/": (WEB / "index.html", "text/html; charset=utf-8", True),
    "/index.html": (WEB / "index.html", "text/html; charset=utf-8", True),
    "/style.css": (WEB / "style.css", "text/css; charset=utf-8", True),
    "/app.js": (WEB / "app.js", "text/javascript; charset=utf-8", True),
    "/icon.png": (HERE / "icon.png", "image/png", False),
}

# Every tool icon, from the one list in ui.py, so adding a tool there is all
# it takes for its image to be served here as well.
STATIC.update({
    route: (WEB / "images" / name, "image/png", False)
    for route, name in ui.IMAGES.items()
})

_ui_lock = threading.Lock()
_ui_stamp: tuple[int, int] | None = None

CTRL_C_KEY = "\x03"
CTRL_O_KEY = "\x0f"
CTRL_R_KEY = "\x12"
SPECIAL_KEY_PREFIXES = {"\x00", "\xe0"}   # first half of an arrow/function key


def has_console_keyboard() -> bool:
    """Whether keys can be read at all -- not on a pipe, and not off Windows."""
    return msvcrt is not None and sys.stdin.isatty()


def keyboard_listener(events: "queue.Queue", stop: threading.Event) -> None:
    while not stop.is_set():
        if not msvcrt.kbhit():
            stop.wait(0.05)
            continue
        try:
            key = msvcrt.getwch()
        except OSError:
            break
        if stop.is_set():
            break
        if not key or key in SPECIAL_KEY_PREFIXES:
            continue   # drop the scan-code half, so an arrow key is not a command
        if key == CTRL_R_KEY:
            events.put("restart")
        elif key == CTRL_O_KEY:
            events.put("reopen")
        elif key == CTRL_C_KEY:
            # getwch() swallows the interrupt, so it is forwarded by hand.
            events.put("stop")


def rebuild_standalone() -> None:
    """Use a fresh process so the builder reads the current UI copy from disk."""
    info("Recompiling the web page...")
    try:
        subprocess.run(
            [sys.executable, str(HERE / "build_standalone.py")],
            cwd=HERE, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail("Could not rebuild the page; server not started.\nDetails: {}".format(exc))


def reload_sources() -> None:
    """Pick up edits to the solvers and the shared copy without a fresh process."""
    importlib.reload(solvers)
    solvers.reload()
    global _ui_stamp
    with _ui_lock:
        _ui_stamp = None


def render_ui(text: str, where: str) -> str:
    """Keep labels in step with templates served from disk, across requests."""
    global _ui_stamp
    with _ui_lock:
        stat = Path(ui.__file__).stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        if stamp != _ui_stamp:
            importlib.invalidate_caches()
            importlib.reload(ui)
            _ui_stamp = stamp
        return ui.render(text, where)


def validate_ui() -> None:
    for path, _, templated in set(STATIC.values()):
        if templated:
            render_ui(path.read_text(encoding="utf-8"), path.name)


class Handler(BaseHTTPRequestHandler):
    server_version = "ClueHelper"

    def log_message(self, fmt, *a):  # quieter console
        pass

    # -- helpers --
    def send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code: int, obj: dict) -> None:
        self.send(code, json.dumps(obj).encode("utf-8"), "application/json")

    # -- routes --
    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]

        entry = STATIC.get(route)
        if entry is None:
            return self.send(404, b"Not found", "text/plain; charset=utf-8")
        path, ctype, templated = entry
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return self.send(500, b"Missing file: " + path.name.encode(),
                             "text/plain; charset=utf-8")
        if templated:
            # Rendered per request, so an edit to ui.py shows up on reload.
            try:
                body = render_ui(body.decode("utf-8"), path.name).encode("utf-8")
            except (KeyError, OSError, UnicodeError) as exc:
                return self.send(500, str(exc).encode(), "text/plain; charset=utf-8")
        return self.send(200, body, ctype)

    def do_POST(self) -> None:
        route = self.path.split("?", 1)[0]
        prefix = "/api/solve/"
        if not route.startswith(prefix):
            return self.send(404, b"Not found", "text/plain; charset=utf-8")
        tool = route[len(prefix):]

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self.send_json(413, {"ok": False, "error": "Request too large."})

        try:
            try:
                req = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                raise ValueError("Malformed request body.") from None
            if not isinstance(req, dict):
                raise ValueError("Malformed request body.")
            return self.send_json(200, solvers.run(tool, req))
        except (ValueError, LookupError) as exc:
            return self.send_json(200, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - never kill the server on one request
            return self.send_json(200, {"ok": False, "error": "Solver error: {}".format(exc)})


def parse_args(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Local web app for Clue Helper.")
    ap.add_argument("-p", "--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser")
    return ap.parse_args(argv)


def run(argv=None) -> None:
    args = parse_args(argv)

    missing = [str(p.relative_to(HERE)) for p, _, _ in STATIC.values() if not p.exists()]
    if missing:
        fail("The server cannot start because these app files are missing: {}.".format(
            ", ".join(sorted(set(missing)))))

    url = "http://127.0.0.1:{}".format(args.port)
    events: "queue.Queue[str]" = queue.Queue()
    stop_keys = threading.Event()
    hotkeys = has_console_keyboard()
    key_thread = None

    open_browser = not args.no_browser
    try:
        while True:
            try:
                validate_ui()
            except (KeyError, OSError, UnicodeError) as exc:
                fail("Could not load the page; server not started.\nDetails: {}".format(exc))
            rebuild_standalone()

            try:
                httpd = LocalHTTPServer(("127.0.0.1", args.port), Handler)
            except OSError as exc:
                fail("Could not start the server on port {}. Stop any earlier server, "
                     "or use 'python server.py --port 8001'.\nDetails: {}".format(
                         args.port, exc))

            if hotkeys:
                stop_keys.clear()
                key_thread = threading.Thread(
                    target=keyboard_listener, args=(events, stop_keys), daemon=True)
                key_thread.start()

            # serve_forever() on its own thread leaves this one free to wait on a
            # keypress; shutdown() is what stops it, and must come from elsewhere.
            threading.Thread(target=httpd.serve_forever, daemon=True).start()

            info("The app is ready at {}.".format(url))
            info(
                "Ctrl+R restarts, Ctrl+O reopens, Ctrl+C stops."
                if hotkeys else "Press Ctrl+C to stop the server.")
            if open_browser:
                threading.Timer(0.4, webbrowser.open, (url,)).start()
                open_browser = False   # a restart reuses the tab already open

            try:
                action = events.get() if hotkeys else _wait_forever()
            except KeyboardInterrupt:
                action = "stop"

            httpd.shutdown()
            httpd.server_close()
            stop_keys.set()
            if key_thread is not None:
                key_thread.join()

            if action not in ("restart", "reopen"):
                info("The server has stopped.")
                return

            # Ctrl+O is Ctrl+R plus the browser hand-off the first run does.
            open_browser = action == "reopen"
            info("Restarting the app...")
            reload_sources()
    finally:
        stop_keys.set()
        if key_thread is not None:
            key_thread.join()


def _wait_forever() -> str:
    """Block until Ctrl+C when there is no keyboard to read."""
    threading.Event().wait()
    return "stop"


if __name__ == "__main__":
    run()
