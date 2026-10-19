"""The Light Box solver.

A straight port of comparison.js, which is kept in the repo root as the
reference implementation. The maths is unchanged; only the shape of the input
is, because the page hands over a whole puzzle at once instead of walking the
user through it one click at a time.

How the puzzle works
--------------------
The box is a 5x5 grid of lights and eight switches, A to H. A switch toggles
some fixed set of lights -- and *which* set differs from box to box, so no
table of switch effects can be written down in advance. That is why the tool
asks: note the lights, press a switch, note them again. The lights that changed
are exactly the ones that switch toggles. XOR of the two readings gives its
mask, and `difference` does that here.

Why the answer is a set and not a sequence
------------------------------------------
Toggling is its own inverse and order does not matter, so pressing a switch
twice is the same as never pressing it, and any solution is a *subset* of the
eight switches, each pressed exactly once. With eight switches there are only
256 subsets, so they are simply all tried.

The subsets are generated in comparison.js's own order and the first one that
works is reported, so this module and the reference pick the same answer when a
box has more than one -- which happens whenever the switch masks are not
independent.
"""

from __future__ import annotations

GRID = 5
LETTERS = "ABCDEFGH"

Grid = tuple[tuple[int, ...], ...]

ALL_ON: Grid = tuple(tuple(1 for _ in range(GRID)) for _ in range(GRID))
ALL_OFF: Grid = tuple(tuple(0 for _ in range(GRID)) for _ in range(GRID))


def xor(a: Grid, b: Grid) -> Grid:
    return tuple(tuple(x ^ y for x, y in zip(row_a, row_b))
                 for row_a, row_b in zip(a, b))


def difference(before: Grid, after: Grid) -> Grid:
    return xor(before, after)


def apply(state: Grid, masks: list[Grid]) -> Grid:
    for mask in masks:
        state = xor(state, mask)
    return state


def subsets(letters: str) -> list[str]:
    combos: list[str] = []
    for letter in letters:
        # Snapshot: the new entries must not themselves be extended this round.
        combos.extend(letter + combo for combo in list(combos))
        combos.append(letter)
    combos.append("")
    return combos


def solutions(state: Grid, switches: dict[str, Grid]) -> list[str]:
    order = "".join(letter for letter in LETTERS if letter in switches)
    found = []
    for combo in subsets(order):
        if apply(state, [switches[letter] for letter in combo]) == ALL_ON:
            found.append(combo)
    return found


# --------------------------------------------------------------------------- #
# The request the page sends
# --------------------------------------------------------------------------- #

def parse_grid(value, where: str) -> Grid:
    if not isinstance(value, (list, tuple)) or len(value) != GRID:
        raise ValueError("{} must be {} rows of {} lights.".format(where, GRID, GRID))
    rows = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, (list, tuple)) or len(row) != GRID:
            raise ValueError("{}: row {} must have {} lights.".format(where, index, GRID))
        rows.append(tuple(1 if cell else 0 for cell in row))
    return tuple(rows)


def parse_switches(value) -> dict[str, Grid]:
    if not isinstance(value, dict) or not value:
        raise ValueError("No switches were recorded. Press each switch once and note which lights changed.")

    masks: dict[str, Grid] = {}
    for letter, entry in value.items():
        letter = str(letter).strip().upper()
        if letter not in LETTERS:
            raise ValueError("'{}' is not a switch. The switches are {}.".format(
                letter, ", ".join(LETTERS)))
        where = "Switch " + letter
        if isinstance(entry, dict):
            mask = difference(parse_grid(entry.get("before"), where + " (before)"),
                              parse_grid(entry.get("after"), where + " (after)"))
        else:
            mask = parse_grid(entry, where)
        masks[letter] = mask
    return masks


def solve(request: dict) -> dict:
    state = parse_grid(request.get("state"), "The lights that are on")
    switches = parse_switches(request.get("switches"))

    found = solutions(state, switches)
    dead = [letter for letter, mask in switches.items() if mask == ALL_OFF]

    if not found:
        return {
            "ok": True,
            "solution": None,
            "solutions": [],
            "unusedSwitches": dead,
            "message": "No solution found. Check the readings and try again.\n"
                       "A single mis-noted light is enough to make a box look unsolvable.",
        }

    best = found[0]
    return {
        "ok": True,
        "solution": sorted(best),
        "sequence": best,
        "presses": len(best),
        "solutions": [sorted(combo) for combo in found],
        "unusedSwitches": dead,
        "message": "Press each of these once." if best else "Every light is already on.",
    }
