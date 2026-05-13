# Contributing to the Web UI

The frontend is vanilla — Web Components, ES modules, no framework, no build step. Three layers, one file per component. Refresh-and-it's-there development.

Read this before touching anything under `web/ui/`. The rules below are enforced.

---

## The shape

Three layers. Each layer has one `.css` file and one `.js` aggregator at `web/ui/`. The components themselves live in same-named folders next to the aggregators.

```
web/ui/
  index.html             tag soup — links the CSS files, scripts the JS files
  index.css              design tokens (light + dark via [data-theme])
  index.js               orchestrator — API surface, router, socket, session state, theme

  elements.css           styles for every element
  elements.js            aggregator: `import './elements/<name>.js'` per file
  elements/              primitives — DOM-level, project-agnostic shape
    breath-dot.js
    role-message.js
    chat-input.js
    pending-row.js
    menu-link.js
    field-input.js
    field-select.js
    power-button.js
    theme-picker.js

  widgets.css            styles for every widget
  widgets.js             aggregator
  widgets/               composites — compose elements, may know domain (persona)
    sidebar-nav.js
    chat-view.js
    status-view.js
    settings-view.js
    memory-view.js       (top-level Memory tab; sub-tabs + body via prose-view)
    prose-view.js        (renders one markdown body — composable, used by memory-view)
    instructions-view.js (renders the meanings catalog as a list)
    calendar-view.js     (month grid; dots per event, click-popovers)
    onboarding-cold.js
    create-form.js
    migrate-form.js
    provider-select.js

  pages.css              styles for every page
  pages.js               aggregator
  pages/                 full-screen views, mounted by index.js into #app
    persona-page.js
    onboarding-page.js

  platform/              logic-only tools (no CSS, no DOM if avoidable)
    network.js           fetch wrapper
    socket.js            WebSocket wrapper with auto-reconnect
    router.js            URL ↔ handler matching
    markdown.js          markdown → HTML
    escape.js            HTML-escape helper
```

**Why this shape:**
- One file per component means you grep for `cab` and find `cabinet-tabs.js` immediately.
- Aggregators are pure manifest — adding a new component = one line in the manifest, one file in the folder.
- Per-layer CSS files mean "where do button styles live?" has one answer (`elements.css`).
- No `<base>` class ceremony. A custom element is just `class X extends HTMLElement` + `customElements.define`.

---

## Logic commands UI

The pattern is uniform at every layer:

> The upper layer creates the lower layer and feeds it data. Lower layer renders.
> Upper layer never asks lower layer for behavior — it tells.

Concretely:
- `index.js` mounts a `<persona-page>` and calls `page.setProps({persona, messages, ...})`.
- `<persona-page>` chooses which widget to render based on `tab` and calls `widget.setProps({...})`.
- Widgets compose elements via `document.createElement('x')` + `el.setProps({...})`.
- Events flow upward via `CustomEvent`. Each layer can re-dispatch or handle.

UI never fetches. UI never reads `location`. UI never opens a WebSocket. Those go through `platform/`, called by `index.js`, with data passed down.

---

## State: arrays are passed, never shared

**Critical pitfall.** When a parent passes a list to a child via `setProps({messages: this._messages})`, the child must COPY:

```js
setProps({ messages }) {
    if (messages !== undefined) {
        this._messages = messages.slice();   // copy, never assign directly
    }
}
```

Otherwise the child's `push()` mutates the parent's array. We hit this exact bug with chat — every user message appeared twice.

Default rule: if you call `setProps` with a list, copy it on receipt.

---

## URL is the source of truth

Every screen-changing event goes through the URL. Reload reproduces the view exactly.

Routes are defined in `index.js` via `platform/router.js`:

```js
router.add('/persona/{id}/{tab}',  ({ id, tab }) => showPersona(id, tab));
router.add('/persona/{id}',        ({ id })      => showPersona(id, 'chat'));
router.add('/onboarding/create',   () => showOnboarding('create'));
router.add('/onboarding/migrate',  () => showOnboarding('migrate'));
router.add('/onboarding',          () => showOnboarding('cold'));
router.add('/',                    () => ...redirect to first persona or onboarding);
```

Open a dialog, expand a section, switch tab — if it's worth bookmarking, it lives in the URL. If the user can't reload and get back here, the URL is incomplete.

---

## CSS tokens, never literals

`index.css` defines semantic tokens like `--accent`, `--text-muted`, `--surface`, `--border`. Light and dark themes redefine the same tokens; everything else just reaches for them.

Class prefixes are layer-scoped to avoid collisions:
- `.el-*` — element internals (e.g. `.el-input`, `.el-trace-row`)
- `.w-*` — widget internals (e.g. `.w-cold-card`, `.w-status-section`)
- `.p-*` — page internals (e.g. `.p-main`, `.p-blank`)

If you reach for `--red` instead of `--danger`, fix it. If you reach for `#f0c868` instead of `--accent`, fix it.

Phase tinting is currently NOT applied user-side. The persona experiences morning/day/night internally; the user only sees light vs dark. Don't add phase-tinted backgrounds without explicit design buy-in.

---

## How to add things

**A new primitive element** (e.g. a date input):
1. `elements/<name>.js`: class extending `HTMLElement`, register with `customElements.define`.
2. Append `import './elements/<name>.js';` to `elements.js`.
3. Add its styles to `elements.css` under tag selector or `.el-...` classes.
4. Use it via `document.createElement('<name>')` from any widget.

**A new widget** (composite, domain-aware):
1. `widgets/<name>.js`: class with `connectedCallback` + `setProps` + `render`. Compose elements via createElement + setProps.
2. Append `import './widgets/<name>.js';` to `widgets.js`.
3. Styles in `widgets.css` (`.w-...`).
4. Emits events upward via `dispatchEvent(new CustomEvent(...))`.

**A new page** (full-screen):
1. `pages/<name>.js`: class composing widgets. Receives setProps from `index.js`.
2. Append to `pages.js` aggregator.
3. Add route in `index.js`.
4. Styles in `pages.css`.

**A platform tool** (project-agnostic logic):
1. `platform/<name>.js`. Export functions or a class. No CSS, no DOM unless required.
2. Import from `index.js` (or another platform tool).
3. If it touches the network/storage/window, it goes here. Widgets shouldn't.

---

## A worked example: the chat vertical

To see the layered shape end-to-end, follow this trail:

1. **Page** — `pages/persona-page.js`: builds `<sidebar-nav>` + `<chat-view>`, forwards events.
2. **Widget** — `widgets/chat-view.js`: builds `<chat-input>` and a list of `<role-message>` elements, manages messages array + pending state.
3. **Elements** — `elements/chat-input.js` (composer), `elements/role-message.js` (bubble + optional trace fold), `elements/pending-row.js` (live "thinking" status + STOP).
4. **Orchestrator** — `index.js` mounts `<persona-page>`, opens `Socket(/ws/{id})`, buffers signals into `pendingTrace`, attaches the trace to each persona message as it arrives, posts user messages via `POST /api/persona/{id}/hear`.
5. **Platform** — `platform/socket.js` reconnects, `platform/network.js` wraps fetch.

The pattern repeats for every page. If you internalize chat, the rest is the same shape.

---

## Conventions

Enforced. Code that violates these is wrong.

- **One component per file.** Filename matches custom element tag (kebab-case).
- **No base class ceremony.** Components extend `HTMLElement` directly. The old `World` / `Widget` / `Layout` / `Element` bases are gone.
- **No `static _css` + injection.** Styles live in the layer's CSS file.
- **All imports at the top of the file.** No dynamic imports inside methods.
- **Pages don't fetch.** API calls live in `index.js` (or platform). Pages emit events; orchestrator handles them.
- **`setProps({messages: arr})` must copy the array.** Don't share references.
- **Events bubble upward only.** A widget doesn't listen to its siblings; it doesn't reach into other widgets. It emits, parent routes.
- **Comments are rare and explain *why*.** Names are the documentation.
- **No project-name leaks in `platform/`.** Platform code never references "persona", "eternego", or any business concept.
- **Theme tokens are semantic.** `--danger`, not `--red`. If you reach for a literal, find the behavior it represents.
- **URL completeness.** Before merging anything that adds a screen-changing event, verify the URL reflects it.

---

## What to watch for

- **Shared-array bug** (covered above) — `setProps` receivers must copy lists.
- **Signal type vs title** — `msg.type` is the class name (`Plan` / `Event` / `Tick` / `CapabilityRun`); `msg.title` is the human label (`Hearing` / `Heard` / `realize` / `tools.http.oauth1_request`). Check the right one.
- **The `Heard` / `Said` filter** — these signals can arrive with `channel = null` (broadcast-to-all). Filter both `!d.channel` and `d.channel.type === 'web'`, since `chat_message` already delivered the web copy.
- **setProps before appendChild gets clobbered** — call `parent.appendChild(el)` *first*, then `el.setProps({...})`. Otherwise `connectedCallback` fires on attach and resets the fields setProps just set. Defensive guard in connectedCallback: `if (this._x === undefined) this._x = '';` rather than unconditional `this._x = ''`.
- **Top-level chrome is `.p-main > X`, not bare `X`** — applying `flex:1; min-height:0; overflow-y:auto` to a tag selector affects nested instances too, collapsing them to 0 height. Scope the chrome to direct children of `.p-main`.
- **WebSocket reconnect** — `socket.js` reconnects automatically every 3s after `onclose`. If you write code that creates a second Socket, close the first explicitly.
- **DevTools focus** — when DevTools is open and the elements panel is focused, keyboard shortcuts (Ctrl+L, Ctrl+R) go there instead of the page. Manual testing surprise.
- **Native select on dark mode** — declare `color-scheme: dark` on `[data-theme="dark"]` and style `option { background; color }`, otherwise Linux/KDE renders the dropdown white-on-white.

---

## Pull requests

- Branch off `master` (or the active version branch).
- Tests pass — but the frontend currently has none. When adding non-trivial logic to `platform/`, prefer a small isolated test (since platform is project-agnostic).
- One logical change per PR.
- PR body: a single `## Summary` section; no test plan section, no AI footer.

---

## License

MIT.
