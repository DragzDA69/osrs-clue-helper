"use strict";

/* The shell: a home menu of tools, and one page per tool.
 *
 * The tool list is not written here -- it is rendered in from ui.py's TOOLS, so
 * the menu, the routes and the browser titles all come from one definition.
 * A tool's own code registers itself with `registerTool(id, { mount })` and is
 * handed the page element when its route opens; until one does, the page shows
 * a placeholder. That keeps every tool a self-contained file that knows nothing
 * about routing.
 *
 * Routing is by hash (#/light-box) rather than by path: the standalone build is
 * opened straight from the filesystem or from GitHub Pages, where there is no
 * server to map a path onto a page.
 */

const $ = (id) => document.getElementById(id);

/* Quoted so this file is valid JS before rendering as well as after. */
const TOOLS = JSON.parse('{{tools_json}}');
const TOAST_MS = +"{{toast_ms}}", TOAST_FADE_MS = +"{{toast_fade_ms}}";
const APP_NAME = "{{app_name}}";

const byId = new Map(TOOLS.map((tool) => [tool.id, tool]));

/* Filled in by each tool's own script. A missing entry is not an error: the
   route still opens, and shows the "not built yet" card. */
const implementations = new Map();
window.registerTool = (id, impl) => {
  implementations.set(id, impl);
  // A tool script that loads after the router has already opened its page
  // (or is re-registered during development) still gets to draw.
  if (current && current.id === id) openTool(id);
};

let current = null;       // the tool whose page is showing, or null on home
let teardown = null;      // whatever the last mount handed back, to undo

// --- the home menu --------------------------------------------------------

function buildMenu() {
  const frag = document.createDocumentFragment();
  for (const tool of TOOLS) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "tile";
    tile.dataset.tool = tool.id;

    const icon = document.createElement("img");
    icon.src = tool.icon;
    icon.alt = "";          // decorative: the name is right beside it
    icon.loading = "lazy";

    const text = document.createElement("span");
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = tool.title;
    text.append(name);
    if (tool.blurb) {
      const blurb = document.createElement("span");
      blurb.className = "blurb";
      blurb.textContent = tool.blurb;
      text.append(blurb);
    }

    tile.append(icon, text);
    frag.append(tile);
  }
  $("menu").replaceChildren(frag);
}

/* One listener for the whole menu rather than one per card. */
$("menu").addEventListener("click", (event) => {
  const tile = event.target.closest(".tile");
  if (tile) go(tile.dataset.tool);
});

$("back").addEventListener("click", () => go(null));

// --- routing --------------------------------------------------------------

/** Navigate to a tool, or to the home screen with `null`. */
function go(id) {
  // Let the hash drive the render, so the back button and a typed URL take
  // exactly the same path through here as a click does.
  location.hash = id ? "#/" + id : "";
}

function routeFromHash() {
  const id = location.hash.replace(/^#\/?/, "").trim();
  return id && byId.has(id) ? id : null;
}

function render() {
  const id = routeFromHash();
  if (id) openTool(id);
  else openHome();
}

function openHome() {
  releaseTool();
  current = null;
  $("page-tool").hidden = true;
  $("page-tool").replaceChildren();
  $("page-home").hidden = false;
  $("back").hidden = true;
  setBrand(null);
  flash("");
  syncBrandLayout();
}

function openTool(id) {
  const tool = byId.get(id);
  if (!tool) return openHome();

  releaseTool();
  current = tool;
  $("page-home").hidden = true;
  $("back").hidden = false;

  const page = $("page-tool");
  page.hidden = false;
  page.replaceChildren(toolHeading(tool), toolBody(tool));
  setBrand(tool);
  flash("");
  syncBrandLayout();

  const impl = implementations.get(id);
  if (impl && typeof impl.mount === "function") {
    teardown = impl.mount(page.querySelector(".toolbody"), tool) || null;
  }
}

/** Undo whatever the last tool set up outside its own page element. */
function releaseTool() {
  if (typeof teardown === "function") teardown();
  teardown = null;
}

function toolHeading(tool) {
  const h = document.createElement("h2");
  h.className = "pagetitle";

  const icon = document.createElement("img");
  icon.className = "toolicon";
  icon.src = tool.icon;
  icon.alt = "";
  h.append(icon, document.createTextNode(tool.title));
  return h;
}

/** The tool's own surface. Empty until its script mounts something into it;
    a tool with no script yet gets the placeholder instead. */
function toolBody(tool) {
  const body = document.createElement("div");
  body.className = "toolbody";
  if (implementations.has(tool.id)) return body;

  const card = document.createElement("div");
  card.className = "card";
  const heading = document.createElement("h3");
  heading.textContent = "{{tool_placeholder_heading}}";
  const text = document.createElement("p");
  text.textContent = "{{tool_placeholder_body}}";
  card.append(heading, text);
  body.append(card);
  return body;
}

/** The header carries the tool's name and icon while its page is open, and
    the app's own while it is not. */
function setBrand(tool) {
  const icon = $("brandIcon");
  const name = $("brandName");
  if (tool) {
    icon.src = tool.icon;
    name.textContent = tool.title;
    $("appInfo").hidden = true;
    document.title = tool.title + " · " + APP_NAME;
  } else {
    icon.src = HOME_ICON;
    name.replaceChildren(span("lead", "{{brand_lead}}"),
                         document.createTextNode(" "),
                         span("", "{{brand_tail}}"));
    $("appInfo").hidden = false;
    document.title = APP_NAME;
  }
}

function span(cls, text) {
  const el = document.createElement("span");
  if (cls) el.className = cls;
  el.textContent = text;
  return el;
}

// --- status line ----------------------------------------------------------

function flash(message, isError) {
  const status = $("status");
  status.innerHTML = message || "";
  status.classList.toggle("err", Boolean(isError));
}
window.flash = flash;

// --- copying --------------------------------------------------------------

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    if (!legacyCopy(text)) {
      flash("{{msg_copy_failed}}", true);
      return;
    }
  }
  toast(text);
}
window.copyText = copyText;

function legacyCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.append(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch {}
  ta.remove();
  return ok;
}

/* Android-style: a new toast wipes out whatever is on screen at once, rather
   than queueing behind it or crossfading with it. */
function toast(text) {
  const host = $("toasts");
  for (const old of host.querySelectorAll(".toast")) {
    clearTimeout(old.dismiss);
    old.remove();
  }

  const el = document.createElement("div");
  el.className = "toast";
  const chip = document.createElement("code");
  chip.textContent = text;
  el.append(chip, document.createTextNode("{{toast_copied_suffix}}"));
  host.append(el);

  // Two frames, so the browser paints the off-screen state before it animates.
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("show")));

  el.dismiss = setTimeout(() => {
    el.classList.remove("show");
    el.dismiss = setTimeout(() => el.remove(), TOAST_FADE_MS + 80);
  }, TOAST_MS);
}
window.toast = toast;

// --- the solver bridge ----------------------------------------------------

/* Tools ask for an answer through here and never care which side computed it.
 * The served page posts to server.py; the standalone build has no server, so
 * it calls the matching function a tool's own script has registered under
 * window.LOCAL_SOLVERS. Either way a tool awaits one promise.
 */
async function solve(tool, payload) {
  const local = window.LOCAL_SOLVERS && window.LOCAL_SOLVERS[tool];
  if (local) {
    try {
      return await local(payload);
    } catch (exc) {
      return { ok: false, error: exc.message };
    }
  }
  try {
    const res = await fetch("/api/solve/" + encodeURIComponent(tool), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await res.json();
  } catch {
    return { ok: false, error: "Lost contact with the local server. Is server.py still running?" };
  }
}
window.solve = solve;

// --- startup --------------------------------------------------------------

/* Captured before any tool swaps it out, so going home restores the real
   icon rather than whichever tool was open last. */
const HOME_ICON = $("brandIcon").src;

/** Stack the header's two halves once the name and the description no longer
    fit side by side. Measured rather than guessed at a breakpoint: the tool
    names change the width of the first half. */
function syncBrandLayout() {
  const bar = document.querySelector(".bar");
  const info = $("appInfo");
  if (info.hidden) {       // a tool page shows only the name: never compact
    bar.classList.remove("compact");
    return;
  }
  const style = getComputedStyle(bar);
  const available = bar.clientWidth - parseFloat(style.paddingLeft)
    - parseFloat(style.paddingRight);
  // Measure the unwrapped copy, not its current (possibly wrapped) width.
  const probe = info.cloneNode(true);
  probe.removeAttribute("id");
  probe.style.cssText =
    "position:fixed;visibility:hidden;width:max-content;white-space:nowrap";
  document.body.append(probe);
  const required = bar.querySelector("h1").getBoundingClientRect().width
    + parseFloat(style.columnGap) + probe.getBoundingClientRect().width;
  probe.remove();
  bar.classList.toggle("compact", required > available);
}

window.addEventListener("hashchange", render);

(function init() {
  buildMenu();
  render();
  let headerWidth = null;
  new ResizeObserver(([entry]) => {
    if (entry.contentRect.width === headerWidth) return;
    headerWidth = entry.contentRect.width;
    syncBrandLayout();
  }).observe(document.querySelector(".bar"));
  document.fonts.ready.then(syncBrandLayout);
})();
