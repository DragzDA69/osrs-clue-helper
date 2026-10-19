"""The Python behind the tools, one module per tool.

A solver module defines `solve(request: dict) -> dict` and is registered here
under the same id the tool carries in ui.py's TOOLS. The page posts to
/api/solve/<id>, and server.py hands the body straight to that function.

The contract both ways is plain JSON:

    request   whatever the tool's page put in the body, already parsed
    response  {"ok": True, ...} on success
              a raised ValueError for anything the user can fix -- the message
              is shown to them as-is, so write it for them

Adding a tool means dropping a module in here and naming it in MODULES below.
"""

from __future__ import annotations

import importlib

# id -> the module under solvers/ that answers for it.
MODULES: dict[str, str] = {
    "light-box": "light_box",
    # "puzzle-box": "puzzle_box",
}

_loaded: dict[str, object] = {}


def reload() -> None:
    for module in _loaded.values():
        importlib.reload(module)
    _loaded.clear()


def get(tool: str):
    if tool not in MODULES:
        raise LookupError("No solver for '{}'.".format(tool))
    if tool not in _loaded:
        _loaded[tool] = importlib.import_module(__name__ + "." + MODULES[tool])
    return _loaded[tool]


def run(tool: str, request: dict) -> dict:
    return get(tool).solve(request)
