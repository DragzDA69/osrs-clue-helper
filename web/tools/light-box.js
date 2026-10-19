"use strict";

/* Light Box: the board you read the puzzle onto.
 *
 * The picture is the interface. Each painted-on bulb gets a hit area over it,
 * and tapping one lays the lit sprite on top; each painted-on lever gets a
 * real button over it, drawn from the same artwork the game uses. So what is
 * on the screen looks like what is in the game, rather than a grid of
 * checkboxes beside it.
 *
 * Every position here is a percentage of the artwork, measured off
 * light_box_start.png (1011x969) rather than guessed. The bulbs sit on a 5x5
 * grid whose columns are not quite evenly spaced, so both edges are listed as
 * they were found; the levers are 4 by 2 and evenly pitched.
 */

(function () {
  const ROWS = 5;
  const COLS = 5;

  // Left edge of each column, and top edge of each row, as a percentage of the
  // picture. These place the whole sprite, transparent margin included, which
  // is what makes the lit bulb land exactly on the dark one it replaces.
  const LEFT = [11.315, 28.229, 44.45, 61.265, 77.487];
  const TOP = [18.132, 29.174, 39.597, 50.639, 61.063];

  // The levers, in cqw -- hundredths of the artwork's width -- so they line up
  // with the painted ones whatever size the box is drawn at.
  const LEVERS = "ABCDEFGH";
  const LEVER_LEFT = [3.759, 27.498, 51.236, 74.876];
  const LEVER_TOP = [71.414, 82.987];

  /* Played through app.js, so the sound switch in the page bar silences them.
     The paths are written out in full because the offline build can only
     inline an asset whose URL appears literally. */
  const SOUND = {
    light: "/audio/light_box_press.mp3",
    leverIn: "/audio/btn_selected.wav",
    leverOut: "/audio/btn_deselected.wav",
  };

  registerTool("light-box", {
    mount(page, tool) {
      // Row-major, so lights[r][c] matches how the solver reads the board.
      const lights = Array.from({ length: ROWS }, () => Array(COLS).fill(false));
      const buttons = [];
      const levers = new Map();

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
          // Two layers: the dark bulb, and the lit one that fades in over it.
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
        if (light) toggle(+light.dataset.row, +light.dataset.col);
      });

      // The levers, over the ones in the picture.
      LEVERS.split("").forEach((label, index) => {
        const lever = osrsButton(label, {
          toggle: true,
          title: "{{lb_lever_label}}".replace("{label}", label),
          onPress: (pressed) => {
            playSound(pressed ? SOUND.leverIn : SOUND.leverOut);
            console.log(`Lever ${label} ${pressed ? "pressed in" : "released"}`);
          },
        });
        lever.classList.add("lever");
        lever.style.left = LEVER_LEFT[index % 4] + "cqw";
        lever.style.top = LEVER_TOP[Math.floor(index / 4)] + "cqw";
        levers.set(label, lever);
        box.append(lever);
      });

      /** Lights are numbered as they read: 1-5 across the top row, 6-10 the
          next, and so on to 25. */
      function lightNumber(r, c) {
        return r * COLS + c + 1;
      }

      function toggle(r, c) {
        set(r, c, !lights[r][c]);
        playSound(SOUND.light);
        console.log(`Light ${lightNumber(r, c)} ${lights[r][c] ? "on" : "off"}`);
      }

      function set(r, c, on) {
        lights[r][c] = on;
        const light = buttons[r * COLS + c];
        light.classList.toggle("on", on);
        light.setAttribute("aria-pressed", String(on));
      }

      function reset() {
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) set(r, c, false);
        }
        for (const lever of levers.values()) lever.pressed = false;
        flash("");
        console.log("Board reset");
      }

      const actions = document.createElement("div");
      actions.className = "toolactions";

      const resetBtn = document.createElement("button");
      resetBtn.type = "button";
      resetBtn.className = "secondary-btn";
      resetBtn.textContent = "{{btn_reset}}";
      resetBtn.addEventListener("click", reset);

      const solveBtn = document.createElement("button");
      solveBtn.type = "button";
      solveBtn.className = "primary-btn";
      solveBtn.textContent = "{{btn_solve}}";
      // Not wired to the solver yet: reading the board is the whole of this
      // step. What it will send is what `board()` returns.

      actions.append(resetBtn, solveBtn);

      const hint = document.createElement("p");
      hint.className = "dict pagehint";
      hint.textContent = "{{lb_prompt}}";

      page.append(hint, box, actions);

      /* --- what the solver will be handed ---------------------------------
       * `state` is the board as 25 ones and zeroes, row by row, which is the
       * shape solvers/light_box.py reads. `on` is the same thing as light
       * numbers, which is easier to eyeball in the console.
       */
      function board() {
        return {
          state: lights.map((row) => row.map((on) => (on ? 1 : 0))),
          on: lights.flatMap((row, r) =>
            row.map((lit, c) => (lit ? lightNumber(r, c) : 0)).filter(Boolean)),
          levers: [...levers].filter(([, el]) => el.pressed).map(([label]) => label),
        };
      }

      page.board = board;
      page.reset = reset;
      // Handy while the solver is being wired up: `clueLightBox.board()` in
      // the console says exactly what would be sent.
      window.clueLightBox = { board, reset, lightNumber };
    },
  });
})();
