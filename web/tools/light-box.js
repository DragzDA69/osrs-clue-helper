"use strict";

/* Light Box: the board you read the puzzle onto, one lever at a time.
 *
 * The picture is the interface. Each painted-on bulb gets a hit area over it,
 * and tapping one lays the lit sprite on top; each painted-on lever gets a
 * real button over it, drawn from the same artwork the game uses.
 *
 * How the reading goes, and why
 * -----------------------------
 * A lever toggles some fixed set of lights, and which set differs from box to
 * box -- so the tool has to watch. The original solver (comparison.js, kept in
 * the repo root) asks for the board nine times: once before anything is
 * pressed, then once after each of A..H. The difference between one reading
 * and the next is exactly what that lever toggles.
 *
 * This does the same. The first reading is the starting combination, entered
 * and locked in with Set Start before any lever can be chosen -- a box does not
 * have to begin dark, so nothing can be assumed about it. Set Start then moves
 * straight on to lever A. So:
 *
 *     lever A's mask = (board after A) xor (the starting combination)
 *     lever B's mask = (board after B) xor (board after A)
 *     ... and the board after H is what the answer is worked out from.
 *
 * The board is cleared after the start and between levers, so each reading is
 * entered from a dark board rather than adjusted from the one before. What is
 * entered is still the whole board as it stands in the game after that lever
 * has been pressed -- that is what the differences above are taken between.
 *
 * Set Start takes the board exactly as it was entered, however few lights that
 * is, and there is no way back from it: Reset is how a box is begun again.
 *
 * Every position here is a percentage of the artwork, measured off
 * light_box_start.png (1011x969) rather than guessed. The bulbs sit on a 5x5
 * grid whose columns are not quite evenly spaced, so both edges are listed as
 * they were found; the levers are 4 by 2 and evenly pitched.
 */

(function () {
  const ROWS = 5;
  const COLS = 5;
  const LEFT = [11.315, 28.229, 44.45, 61.265, 77.487];
  const TOP = [18.132, 29.174, 39.597, 50.639, 61.063];
  const LEVERS = "ABCDEFGH";
  const LEVER_LEFT = [3.759, 27.498, 51.236, 74.876];
  const LEVER_TOP = [71.414, 82.987];
  const FEW_LIGHTS = 4;

  const SOUND = {
    light: "/audio/light_box_press.mp3",
    leverIn: "/audio/btn_selected.wav",
    leverOut: "/audio/btn_deselected.wav",
    reset: "/audio/board_reset.wav",
  };

  registerTool("light-box", {
    mount(page, tool) {
      const lights = Array.from({ length: ROWS }, () => Array(COLS).fill(false));
      const buttons = [];
      const levers = new Map();

      let started = false;
      let start = null;
      let current = null;
      const readings = new Map();
      let solved = false;

      const box = document.createElement("div");
      box.className = "lightbox";
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", tool.title);

      for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
          const light = document.createElement("button");
          light.type = "button";
          light.className = "light";
          light.style.left = LEFT[c] + "%";
          light.style.top = TOP[r] + "%";
          light.setAttribute("aria-pressed", "false");
          light.setAttribute("aria-label", "{{lb_light_label}}"
            .replace("{r}", r + 1).replace("{c}", c + 1));
          light.dataset.row = r;
          light.dataset.col = c;
          for (const state of ["off", "on"]) {
            const bulb = document.createElement("i");
            bulb.className = state;
            light.append(bulb);
          }
          box.append(light);
          buttons.push(light);
        }
      }

      /* One listener for the whole board rather than 25. */
      box.addEventListener("click", (event) => {
        const light = event.target.closest(".light");
        if (light && !light.disabled) toggle(+light.dataset.row, +light.dataset.col);
      });

      LEVERS.split("").forEach((label, index) => {
        const lever = osrsButton(label, {
          title: "{{lb_lever_label}}".replace("{label}", label),
          onPress: () => chooseLever(label),
        });
        lever.classList.add("lever");
        lever.style.left = LEVER_LEFT[index % 4] + "cqw";
        lever.style.top = LEVER_TOP[Math.floor(index / 4)] + "cqw";
        lever.setAttribute("aria-pressed", "false");
        levers.set(label, lever);
        box.append(lever);
      });

      // --- the board ------------------------------------------------------

      function toggle(r, c) {
        set(r, c, !lights[r][c]);
        playSound(SOUND.light);
        refresh();
      }

      function set(r, c, on) {
        lights[r][c] = on;
        const light = buttons[r * COLS + c];
        light.classList.toggle("on", on);
        light.setAttribute("aria-pressed", String(on));
      }

      function clearLights() {
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) set(r, c, false);
        }
      }

      function snapshot() {
        return lights.map((row) => row.map((on) => (on ? 1 : 0)));
      }

      function litCount() {
        return lights.flat().filter(Boolean).length;
      }

      // --- the starting combination ---------------------------------------

      /* Locks in the board as entered, then goes straight on to lever A, so the
         first thing left to do is read the board after pulling it. The start is
         not questioned the way a lever's reading is -- an empty board, or a
         nearly empty one, is a fair start. */
      function setStart() {
        if (started) return;
        start = snapshot();
        started = true;
        clearLights();
        chooseLever(LEVERS[0]);
      }

      // --- the lever sequence ---------------------------------------------

      function nextLever() {
        if (current === null) return LEVERS[0];
        const at = LEVERS.indexOf(current);
        return at < LEVERS.length - 1 ? LEVERS[at + 1] : null;
      }

      async function chooseLever(label) {
        if (!started || solved || label !== nextLever()) return;

        // Moving on locks in what is on the board as the reading for the lever
        // before this one, so this is the moment to question a thin board.
        if (current !== null) {
          const lit = litCount();
          if (lit < FEW_LIGHTS) {
            const go = await confirmAction({
              title: "{{lb_few_title}}".replace("{n}", lit).replace("{label}", current),
              message: "{{lb_few_message}}",
              note: "{{lb_few_note}}".replace("{label}", current),
              confirm: "{{btn_continue}}",
            });
            if (!go) return;        // stay where we are; nothing is recorded
          }
          readings.set(current, snapshot());
          clearLights();
        }

        current = label;
        playSound(SOUND.leverIn);
        refresh();
      }

      function refresh() {
        const next = nextLever();
        for (const [label, lever] of levers) {
          const done = readings.has(label) || label === current;
          lever.pressed = done;
          lever.disabled = solved || !started || (!done && label !== next);
        }

        // Open for the start, and then for each lever's reading in turn.
        for (const light of buttons) light.disabled = solved;

        const lit = litCount();
        const ready = current === LEVERS.at(-1) && lit >= FEW_LIGHTS;

        // Only one of these is ever live: Set Start until it is set, then Solve.
        startBtn.disabled = started;
        solveBtn.disabled = solved || !ready;
        startPrompt.textContent = started ? "" : "{{lb_enter_start}}";

        if (solved) return;
        if (!started) {
          flash("");
        } else if (ready) {
          flash("{{lb_ready}}");
        } else {
          flash("{{lb_step}}".replace("{label}", current)
            + (lit ? "  ·  " + "{{lb_step_count}}".replace("{n}", lit) : ""));
        }
      }

      // --- solving ---------------------------------------------------------

      function request() {
        const switches = {};
        let before = start;
        for (const label of LEVERS) {
          const after = label === current ? snapshot() : readings.get(label);
          switches[label] = { before, after };
          before = after;
        }
        return { state: snapshot(), switches };
      }

      async function runSolve() {
        readings.set(current, snapshot());
        flash("{{lb_solving}}");
        solveBtn.disabled = true;

        const data = await solve("light-box", request());

        if (!data.ok) {
          flash(data.error, true);
          solveBtn.disabled = false;
          return;
        }
        solved = true;
        refresh();

        if (data.solution === null) {
          flash(data.message, true);
          return;
        }
        flash("");
        showAnswer(data.solution);
      }

      function showAnswer(letters) {
        answer.hidden = false;
        answerCaption.textContent = letters.length
          ? "{{lb_answer}}" : "{{lb_answer_none}}";
        answerChips.replaceChildren(
          ...letters.map((letter) => osrsChip(letter, { toggle: true })));
      }

      // --- resetting -------------------------------------------------------

      function touched() {
        return started || litCount() > 0;
      }

      function reset() {
        answer.hidden = true;
        answerCaption.textContent = "";
        answerChips.replaceChildren();
        clearLights();
        started = false;
        start = null;
        current = null;
        solved = false;
        readings.clear();
        playSound(SOUND.reset);
        refresh();
      }

      // --- the page --------------------------------------------------------

      const actions = document.createElement("div");
      actions.className = "toolactions";

      const resetBtn = document.createElement("button");
      resetBtn.type = "button";
      resetBtn.className = "secondary-btn";
      resetBtn.textContent = "{{btn_reset}}";
      resetBtn.addEventListener("click", async () => {
        if (!touched()) return;
        const go = await confirmAction({
          title: "{{lb_reset_title}}",
          message: "{{lb_reset_message}}",
          note: "{{msg_cannot_undo}}",
          confirm: "{{btn_confirm_reset}}",
        });
        if (go) reset();
      });

      const startBtn = document.createElement("button");
      startBtn.type = "button";
      startBtn.className = "primary-btn";
      startBtn.textContent = "{{btn_set_start}}";
      startBtn.addEventListener("click", setStart);

      const solveBtn = document.createElement("button");
      solveBtn.type = "button";
      solveBtn.className = "primary-btn";
      solveBtn.textContent = "{{btn_solve}}";
      solveBtn.addEventListener("click", runSolve);

      actions.append(resetBtn, startBtn, solveBtn);

      const answer = document.createElement("div");
      answer.className = "answer";
      answer.hidden = true;

      const answerCaption = document.createElement("p");
      answerCaption.className = "dict";

      const answerChips = document.createElement("div");
      answerChips.className = "osrs-chip-row";
      answer.append(answerCaption, answerChips);

      const hint = document.createElement("p");
      hint.className = "dict pagehint";
      hint.textContent = "{{lb_prompt}}";

      const startPrompt = document.createElement("p");
      startPrompt.className = "startprompt";

      const status = document.getElementById("status");
      const statusHome = status.parentNode;

      page.append(hint, startPrompt, box, status, actions, answer);
      refresh();

      return () => statusHome.append(status);
    },
  });
})();
