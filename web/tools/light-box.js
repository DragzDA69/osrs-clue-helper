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
 * This does the same with eight readings, because the box starts with every
 * light off: that all-off board is the ninth reading, and it is already on the
 * screen before the first lever is chosen. So:
 *
 *     lever A's mask = (board after A) xor (all off)
 *     lever B's mask = (board after B) xor (board after A)
 *     ... and the board after H is what the answer is worked out from.
 *
 * The board is cleared between levers, so each reading is entered from a dark
 * board rather than adjusted from the one before. What is entered is still the
 * whole board as it stands in the game after that lever has been pressed --
 * that is what the differences above are taken between.
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

  const ALL_OFF = Array.from({ length: ROWS }, () => Array(COLS).fill(0));

  registerTool("light-box", {
    mount(page, tool) {
      const lights = Array.from({ length: ROWS }, () => Array(COLS).fill(false));
      const buttons = [];
      const levers = new Map();

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

      // --- the lever sequence ---------------------------------------------

      function nextLever() {
        if (current === null) return LEVERS[0];
        const at = LEVERS.indexOf(current);
        return at < LEVERS.length - 1 ? LEVERS[at + 1] : null;
      }

      async function chooseLever(label) {
        if (solved || label !== nextLever()) return;

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
          lever.disabled = solved || (!done && label !== next);
        }

        const open = current !== null && !solved;
        for (const light of buttons) light.disabled = !open;

        const lit = litCount();
        const ready = current === LEVERS.at(-1) && lit >= FEW_LIGHTS;
        solveBtn.disabled = solved || !ready;

        if (solved) return;
        if (current === null) {
          flash("{{lb_step_start}}");
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
        let before = ALL_OFF;
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
        return current !== null || litCount() > 0;
      }

      function reset() {
        answer.hidden = true;
        answerCaption.textContent = "";
        answerChips.replaceChildren();
        clearLights();
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

      const solveBtn = document.createElement("button");
      solveBtn.type = "button";
      solveBtn.className = "primary-btn";
      solveBtn.textContent = "{{btn_solve}}";
      solveBtn.addEventListener("click", runSolve);

      actions.append(resetBtn, solveBtn);

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

      const status = document.getElementById("status");
      const statusHome = status.parentNode;

      page.append(hint, box, status, actions, answer);
      refresh();

      return () => statusHome.append(status);
    },
  });
})();
