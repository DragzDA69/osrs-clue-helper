"use strict";

/* The Light Box solver, for the build that has no Python behind it.
 *
 * server.py never serves this file: it is inlined only into the standalone
 * index.html, the one that runs from GitHub Pages or straight off a phone.
 * Locally, solvers/light_box.py answers instead, and app.js's solve() prefers
 * the server whenever there is one -- so the two never both run.
 *
 * It is a port of the same comparison.js the Python is a port of, and it
 * answers in the same shape, so the page cannot tell which side replied.
 * Keep the two in step: a change to one is a change to both.
 *
 * The request: `switches[X].before` is the board before lever X, and for A that
 * is the starting combination the player entered; every later `before` is the
 * previous lever's `after`. `state` is the board after H. The start is never
 * sent on its own -- it is already inside A's mask.
 */

(function () {
  const GRID = 5;
  const LETTERS = "ABCDEFGH";
  const ALL_ON = Array.from({ length: GRID }, () => Array(GRID).fill(1));

  const xor = (a, b) => a.map((row, r) => row.map((v, c) => v ^ b[r][c]));
  const same = (a, b) => a.every((row, r) => row.every((v, c) => v === b[r][c]));

  function subsets(letters) {
    const found = [];
    for (const letter of letters) {
      const sofar = found.length;
      for (let i = 0; i < sofar; i++) found.push(letter + found[i]);
      found.push(letter);
    }
    found.push("");
    return found;
  }

  function grid(value, where) {
    if (!Array.isArray(value) || value.length !== GRID) {
      throw new Error(`${where} must be ${GRID} rows of ${GRID} lights.`);
    }
    return value.map((row, i) => {
      if (!Array.isArray(row) || row.length !== GRID) {
        throw new Error(`${where}: row ${i + 1} must have ${GRID} lights.`);
      }
      return row.map((cell) => (cell ? 1 : 0));
    });
  }

  function masks(switches) {
    if (!switches || typeof switches !== "object" || !Object.keys(switches).length) {
      throw new Error("No switches were recorded. Press each switch once and "
        + "note which lights changed.");
    }
    const out = {};
    for (const [raw, entry] of Object.entries(switches)) {
      const letter = String(raw).trim().toUpperCase();
      if (!LETTERS.includes(letter)) {
        throw new Error(`'${letter}' is not a switch. The switches are `
          + LETTERS.split("").join(", ") + ".");
      }
      out[letter] = entry && entry.before !== undefined
        ? xor(grid(entry.before, `Switch ${letter} (before)`),
              grid(entry.after, `Switch ${letter} (after)`))
        : grid(entry, `Switch ${letter}`);
    }
    return out;
  }

  window.LOCAL_SOLVERS = window.LOCAL_SOLVERS || {};
  window.LOCAL_SOLVERS["light-box"] = function (request) {
    let state, switches;
    try {
      state = grid(request.state, "The lights that are on");
      switches = masks(request.switches);
    } catch (exc) {
      return { ok: false, error: exc.message };
    }

    const order = LETTERS.split("").filter((letter) => letter in switches).join("");
    const found = [];
    for (const combo of subsets(order)) {
      let lights = state;
      for (const letter of combo) lights = xor(lights, switches[letter]);
      if (same(lights, ALL_ON)) found.push(combo);
    }

    const dead = Object.entries(switches)
      .filter(([, mask]) => mask.every((row) => row.every((v) => v === 0)))
      .map(([letter]) => letter);

    if (!found.length) {
      return {
        ok: true,
        solution: null,
        solutions: [],
        unusedSwitches: dead,
        message: "No solution found. Check the readings and try again."
          + "\nA single mis-noted light is enough to make a box look unsolvable.",
      };
    }

    const best = found[0];
    return {
      ok: true,
      solution: best.split("").sort(),
      sequence: best,
      presses: best.length,
      solutions: found.map((combo) => combo.split("").sort()),
      unusedSwitches: dead,
      message: best ? "Press each of these once." : "Every light is already on.",
    };
  };
})();
