# Contributing to the Web UI

The frontend is built on the web platform — Web Components, ES modules, no framework. It follows Natural Architecture, the same shape as the backend, with one twist: every layer has two sides because the frontend has two substrates (visual matter and behavioral matter) where the backend has one.

Read this file before changing anything under `web/ui/`. Rules below are enforced. If code contradicts a rule, the code is wrong.

---

## The shape

Three layers, dependencies flow down. Each layer has a UI side (paints content) and a Logic side (structures and coordinates).

|   | UI side | Logic side |
|---|---------|------------|
| **Business** — what kind of moment this is | `business/worlds/`, `business/frame.js` | `index.js` |
| **Core** — engineering | `core/widgets/` | `core/apps/` |
| **Platform** — primitives | `platform/elements/` | `platform/layouts/`, `platform/network.js`, `platform/socket.js`, `platform/router.js` |

Read each row top-to-bottom: this is what the persona shows, how it's composed, and what it's composed of.

- **Business** is the persona's worlds. `worlds/` are full-screen states with URLs (outer-world, inner-world, status-world, setup, welcome). `frame.js` is the chrome that holds them. `index.js` is the orchestrator — boots the app, owns session state, signals, and routing wiring.
- **Core** is the engineering. `widgets/` are composite painted units (a conversation, a setup form, a pair flow). `apps/` are flows that coordinate widgets over time.
- **Platform** is the primitives. `elements/` are DOM things (a button, a text input, a log line). `layouts/` compose what to draw — they pick which elements to use based on data shape, but don't paint themselves (forms, tail, composer, carousel, timeline). Non-visual primitives (`network.js`, `socket.js`, `router.js`, `markdown.js`) live alongside as **tools** — stateless utilities any layer may import. The shared HTMLElement base (`painted.js`) provides one-time CSS injection for everything that paints.

---

## Folder structure

```
web/ui/
  index.html                    starter — mounts the frame, loads index.js
  index.js                      orchestrator (business/Logic)
  index.css                     design tokens (semantic, OS-level)

  business/
    frame.js                    chrome — header, persona picker, world tabs
    worlds/                     full-screen states with URLs
      outer-world.js
      inner-world.js
      status-world.js
      setup.js
      welcome.js

  core/
    widgets/                    composite painted units (core/UI)
    apps/                       coordinated flows (core/Logic)

  platform/
    painted.js                  shared HTMLElement base (CSS injection)
    elements/                   DOM primitives (platform/UI)
    layouts/                    composition primitives (platform/Logic)
    network.js                  fetch wrapper (platform/Logic)
    socket.js                   WebSocket wrapper (platform/Logic)
    router.js                   URL ↔ state (platform/Logic)
    markdown.js                 markdown → HTML (platform/Logic)
```

The 3-layer × 2-side shape is visible in the tree. New cells slot into the matching folder; if a cell can't decide which folder, it's doing two jobs — split.

---

## Entry layer (index.*)

`index.html`, `index.js`, `index.css` sit at the root because that's where the browser looks for entry points.

`index.js` plays the role of the **business/Logic singleton** — it lives at the entry-point name because it IS the entry point. It owns:
- The boot sequence
- The session state (current persona, current world, persona cache)
- The signals feed (cross-application events)
- The wiring of platform primitives (`network.js`, `socket.js`, `router.js`) into a coherent application surface

`index.css` holds **design tokens**, semantic not literal:

- `--danger`, not `--red`
- `--surface-recessed`, not `--bg-darker`
- `--text-muted`, not `--text-gray-400`

Cells make windows on top without thinking about color, spacing, or font. They reach for behavior (`--danger`), not pigment (`--red`).

---

## Logic commands UI

At every layer, the Logic side is the controller. The UI side is the body of each branch.

> Logic decides which UI to invoke and with what variable. UI knows how to draw given the variable. When Logic changes the variable, it re-invokes UI.

Uniform across layers; the variable that drives differs:

- **Business** — current world + current persona drives which world renders. The singleton commands `frame.js` and the worlds.
- **Core** — app state drives which widget composition shows. An app commands its widgets.
- **Platform** — data shape drives which elements compose. A simple-form sees `{ name: text, birthday: date, provider: options }` and chooses `input-text`, `input-text`, `input-options`. A step-form does the same plus back/next.

**The full chain:** App → Widget (picks layout) → Layout (picks elements) → Elements (render). Each Logic level commands its UI based on what it received from above.

UI never asks Logic for behavior. UI is invoked, not consulted.

---

## Dependency rules

**Vertical, between layers — strictly downward.**

A widget never imports a world. An element never imports a widget. Imports up the stack are the wrong shape; if you feel one is needed, the cell is in the wrong layer.

**Horizontal, within a layer.**

- Same-side peers may import each other — sparingly.
- Cross-side at the same layer flows **Logic → UI** *for control*. Logic instantiates UI and feeds it data; UI does not ask Logic for behavior. Stateless **tools** (pure transforms — markdown, formatters, escapers) are exempt — they're functions, not controllers; any layer may import them.

---

## State and signals

Two paths, never confused.

**Inter-layer state — plain programming.**

- The upper layer owns the variable.
- It hands a reference down to the lower layer.
- The lower layer reads, mutates, or returns a result.
- That's it. No reactive bus, no observable, no global manager.

State lives where it's used: input draft text in the element, wizard step in the app, current persona in the singleton.

**Mutation by reference is the form pattern.** When the parent passes a `values` object to a form layout (e.g., `simple-form`), the form mutates fields onto that same object as the user types. The parent reads from the same reference whenever it needs current values — on submit, on step change, on send. This avoids re-rendering on every keystroke and is the natural expression of "upper layer owns the object, lower layer modifies."

**Cross-application — signals.**

Signals are events propagated to anyone who's interested, with no contract between sender and receivers. Throw a stone; for the thrower the act is done; for the window that the stone hits, that means getting broken. The thrower doesn't track the window.

- Only the **Logic side** dispatches signals. UI never throws.
- The business/Logic singleton owns the Feed.
- A signal is for *world has changed*, not *please update yourself*. Use a callback or a method call for direct asks.

If you're dispatching a signal to update a sibling, you're using the wrong tool — pass the reference instead.

---

## URL is the source of truth for navigation

Every screen-changing event goes through the URL. Reload always reproduces the current view from URL alone.

- Selecting a persona → URL.
- Switching worlds → URL.
- Step in a wizard → URL.
- Open dialog, expanded panel, current archive in the carousel → URL.

If a state isn't in the URL, the user can't link to it, can't bookmark it, can't reload it. The test — *can I copy this URL and get back here?*

The browser state and `index.js` together fully describe the view. There is no other source.

---

## DRY: abstract by pruning, not by design

The base rule: **do not DRY without pain.**

- Duplicate freely on first write.
- Don't extract helpers up front.
- Don't introduce a base class because two cells happened to need the same line.

Abstraction earns its place during the **prune phase**, after first delivery, when "obvious weirdness" surfaces — code that no one can read without flinching, a name that suggests itself naturally, three structural duplicates that mean the same thing.

If you can't say what's painful about the duplication, the abstraction isn't ready.

---

## No client, no spec

If no URL or interaction reaches a screen, that screen doesn't exist.

- Don't build a widget that nothing renders.
- Don't expose an API method nothing calls.
- Don't add a world that has no entry point.

Dead UI is dead code. Remove it.

---

## Platform portability

Platform code must be portable. It can use libraries, plugins, or vanilla code — whatever delivers. But it must not contain project-specific jargon.

- ✅ `create_form(url, fields, onSubmit)`
- ❌ `create_persona_form(...)`
- ✅ A tooltip-input that shows a tooltip on hover
- ❌ An input that knows about `persona.id`

The implementation must work in any project. A specific input that happens to be used only here is fine — as long as nothing in its body references the persona, the daemon, or any business name.

---

## Naming

Each cell's naming reflects the cell's business.

- The **backend's** business is to *make* a persona — gerunds, verbs of process (recognizing, deciding, archiving).
- The **frontend's** business is to *show* the persona — nouns of presentation (world, widget, layout, element).

A world is a place you are. A widget is a thing with a job. A layout is an arrangement. An element is a primitive.

Folders are plural nouns describing what they contain (`worlds/`, `widgets/`, `apps/`, `layouts/`, `elements/`). Files are kebab-case singular nouns naming the cell (`outer-world.js`, `simple-form.js`, `input-text.js`).

---

## Where to add things

| What you're adding | Where it goes |
|---|---|
| A full-screen state with a URL | `business/worlds/<name>.js`. Register the route in `index.js`. |
| The chrome around worlds | `business/frame.js` |
| Session/global state, signals, world routing wiring | `index.js` |
| A coordinated flow (multi-step or stateful feature) | `core/apps/<name>.js`. Plain class with `init / start / activate / deactivate`. |
| A composite painted unit | `core/widgets/<name>.js`. Extends `Widget`. |
| A non-visual platform primitive | new file under `platform/` named for what it wraps |
| A composition layout (form variant, tail, composer, carousel, timeline) | `platform/layouts/<name>.js`. Extends `Layout`. |
| A DOM primitive (input variant, button variant, log line) | `platform/elements/<name>.js`. Extends `Element`. |
| A design token | `index.css`, semantically named |

---

## Base classes

All custom-element bases follow the same pattern: `init(props)` then one verb method.

| Base | Verb | Lifecycle |
|---|---|---|
| `Element` (platform/UI) | `render()` | — |
| `Layout` (platform/Logic) | `arrange()` | — |
| `Widget` (core/UI) | `build()` | — |
| `World` (business/UI) | `build()` | `activate() / deactivate()` |
| `App` (core/Logic, plain class) | `start()` | `activate() / deactivate()` |

Style injection: each base owns its `_css` static and injects once via the `_styled` flag. Globals live in `index.css`.

---

## Conventions

Enforced.

- **One element per file.** Filename matches the custom element name (kebab-case).
- **All imports at file level.** No dynamic imports inside methods.
- **No helpers up front.** No `_helper` functions extracted to dedupe two lines. Wait for pain.
- **No backwards-compat shims.** When you change something, update the callers.
- **No project name in platform.** Platform code never references `persona`, `eternego`, the daemon, or any business concept by name.
- **No fetch outside `platform/network.js`.** Widgets and worlds use the API surface exposed by `index.js`.
- **No WebSocket outside `platform/socket.js`.** Same pattern.
- **No history/location reads outside `platform/router.js`.** Same pattern.
- **No markdown parsing outside `platform/markdown.js`.** Elements display markdown via this tool.
- **No upward imports.** A widget importing a world is a bug.
- **No DOM in Logic that doesn't need it.** Apps and the singleton hold no DOM. Layouts hold DOM only because arrangement requires it.
- **No state in UI beyond what the cell renders.** A widget can hold input draft state; it cannot hold session state. Session state belongs in the singleton.
- **Comments are rare and explain *why*, never *what*.** Names are the documentation.
- **Style tokens are semantic.** `--danger`, not `--red`. If you reach for a literal name, find the behavior it represents.

---

## What to watch for

- **The Logic-commands-UI flow is easy to invert.** Watch for UIs that subscribe to global state, ask Logic for behavior, or fetch on their own. Those are inversions; route them back through Logic.
- **The 6-cell shape gets fuzzy at edges.** If a cell can't decide which layer it belongs to, it's probably doing two jobs. Split.
- **The base-class pattern (`init` then verb) is the contract.** Don't override `connectedCallback` or other lifecycle methods unless you have a specific reason. The verb method is where work happens.
- **URL completeness.** Before merging anything that adds a screen-changing event, verify the URL reflects it. If reload doesn't reproduce the view, the URL is incomplete.
- **Signals are not a state mechanism.** If you're dispatching a signal to update a sibling, pass a reference instead.
- **DRY drift.** A base class that started as a real abstraction can ossify into a place to dump shared lines. When you reach to add a method to a base, ask whether the base is still earning its place.
