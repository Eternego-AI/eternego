# Contributing to Eternego OS

This document covers the architecture, conventions, and patterns for the web-based OS interface.

---

## Natural Architecture

The OS follows [Natural Architecture](https://medium.com/@nickaversano/natural-architecture-for-software-4a78a0d95e48) — three layers, each with a logical + UI pair:

```
Business (WHY)      OS + Modes          What the system needs
Core (WHAT)         Apps + Widgets      Project-specific delivery
Platform (HOW)      Layouts + Elements  Portable, no project knowledge
```

**The portability test decides placement.** Can I take this component to a different project and use it as-is? If yes, it belongs in platform (layout or element). If no, it belongs in core (app or widget).

Within each Natural Architecture layer, logical and UI alternate:

```
OS          logical    index.js       State, API, signals, boot
Mode        UI         modes/         Visual frame (desktop, terminal, ...)
App         logical    apps/          Behavior, constructs widgets
Widget      UI         widgets/       Project-specific visual containers
Layout      logical    layouts/       Portable arrangement + framing
Element     UI         elements/      Portable content display
```

**Logical layers** contain behavior: state management, API calls, data processing, event routing. They are JS files. Each logical component creates a `<div>` with its ID in the DOM (e.g., `<div id="persona-app">`, `<div id="card-layout">`) so the full chain is visible in the inspector for debugging.

**UI layers** contain presentation: DOM structure, CSS class composition, visual state. They are JS custom elements whose concern is only how things look. They never make API calls or process data — they receive everything through `init()`.

---

## The Design System

`index.css` is the single source of visual identity. It defines:

- Colors, gradients, shadows
- Fonts, font sizes, font weights, font colors
- Border colors, thickness, radius
- Blur, opacity, glow values
- Anything that changes when you swap themes

**The theme test:** if switching from glass to Catppuccin to macOS style requires changing a file other than `index.css`, something is in the wrong place.

What does NOT belong in `index.css`:

- Position and layout (flex, grid, padding, margin) — that's the component's concern
- Component-specific structure — that's the element's concern

UI components style themselves by composing classes from `index.css`. This means adding a new widget or element should not require new CSS.

---

## Dependency Injection

No layer reaches up. Every layer receives what it needs from its parent through `init()`.

```
OS constructs Mode        → init({ signals, apps })
OS constructs App         → init({ signals, personas, personaTalk, ... })
App constructs Widget     → init({ messages, received, send, ... })
Widget constructs Layout  → init({ steps, onSubmit, ... })
Layout constructs Element → init({ role, text, ... })
```

### The init pattern

Custom elements cannot take constructor arguments. Every component exposes an `init(props)` method. The parent calls it after creating the element:

```javascript
const chat = document.createElement('chat-widget');
chat.init({ past: messages, received: this._received, send });
container.appendChild(chat);
```

### Reactive state with Feed

When a parent needs to push updates to a child after init, use a `Feed`. A Feed is a reactive list with one writer and many readers, built on `EventTarget`:

```javascript
class Feed extends EventTarget {
    #items = [];
    get items() { return this.#items; }
    push(...values) {
        this.#items.push(...values);
        this.dispatchEvent(new CustomEvent('update', { detail: values }));
    }
    reset(values = []) {
        this.#items = values;
        this.dispatchEvent(new Event('reset'));
    }
}
```

**Only one entity writes to a Feed.** The owner creates it, writes to it, and passes it down. Consumers subscribe:

```javascript
// App creates and owns the feed
this._received = new Feed();

// App passes it to widget
chatWidget.init({ received: this._received });

// App writes when a signal arrives
this._received.push(message);

// Widget reads
props.received.addEventListener('update', (e) => {
    e.detail.forEach(msg => this._render(msg));
});
```

The chat example end-to-end:

1. OS owns `signals` (Feed) — websocket pushes to it
2. Persona app subscribes to `signals`, filters for its persona, writes to `received` (Feed)
3. Chat widget reads `past` (array, loaded once), `received` (Feed, app writes), and `sent` (Feed, form element writes)
4. Chat widget builds history: past first, then sent and received interleaved by time

---

## Boot Flow

1. OS constructs the **tty app** with `signals`
2. OS activates **terminal mode**, passes tty app
3. OS boots: connects websocket (signals flow into `signals` Feed), fetches agents
4. Terminal mode displays tty's stdout widget (tail-layout → log-line elements)
5. Boot completes — OS calls `bootLoaded()`, switches to **desktop mode**
6. Desktop mode receives apps and signals, renders its UI (icons, background, etc.)

The OS does not know about icons or how apps are opened — those are desktop mode's design decisions. Apps may expose metadata (name, icon) that modes can read, but modes decide how to present them.

---

## Layer Details

### Business Layer

#### OS (index.js)

The entry point. Owns:

- **Boot**: websocket connection, initial API calls
- **State**: mode, registered apps, signals (Feed), agents
- **Shared functions**: things multiple apps need (e.g., `freeRamInMB()`)

OS does not own app-opening logic or UI concerns. It sets the active mode and constructs apps when needed.

Any logical layer can make its own API calls. OS provides shared functions only when they are genuinely shared across apps.

#### Mode (modes/)

UI layer. Each mode is a custom element that receives data from OS and provides the visual frame.

- **Terminal mode**: receives `signals` and the tty app. Displays stdout output during boot.
- **Desktop mode**: receives `apps` and `signals`, renders app icons, backgrounds, page transitions. Decides how apps appear when selected.
- **Future modes**: explore (file browser), IDE (code editor), etc.

Modes do not contain app logic. They present apps however they choose and tell OS when the user selects one.

### Core Layer

#### App (apps/)

Logical layer. Each app:

1. Receives state and functions from OS via `init()`
2. Constructs its widgets, passing each what it needs
3. Listens for signals relevant to its domain
4. Pushes updates to widgets via Feed or direct method calls
5. Exposes metadata (name, icon character) that modes can read

Apps make their own API calls for domain-specific operations. They never touch the DOM directly beyond constructing and managing their widgets.

#### Widget (widgets/)

UI layer. Project-specific visual containers. Each widget:

1. Receives data and callbacks via `init()`
2. Composes layouts using `index.css` classes for its own container styling
3. Declares its tile size (`columns`, `rows`) for the grid layout
4. Passes data and callbacks down to its layouts

Widgets never make API calls. They never contain elements directly — elements are always inside a layout. Widgets know about the project domain (personas, chat, creation flows) and translate domain data into generic props for portable layouts.

### Platform Layer

#### Layout (layouts/)

Logical layer. Portable arrangement and framing — no project knowledge:

- **card-layout**: provides a framed container surface
- **step-layout**: manages step visibility, dot indicators, `go(stepId)` navigation
- **form-layout**: manages field collection, validation, emits submit
- **grid-layout**: bin-packs child components by tile size, FLIP animation on focus change
- **tail-layout**: auto-scroll container, stays pinned to bottom

A wizard is the composition of layouts and elements with alternating layers:

```
create-widget (UI — widget, core)
  step-layout (logical — layout, platform)
    step-panel (UI — element, platform)
      form-layout (logical — layout, platform)
        text-input (UI — element, platform)
        option-list (UI — element, platform)
```

Each hop crosses a layer boundary: UI → logical → UI → logical → UI. The app wires the layouts together — a form's submit advances the step, the final form triggers the API call.

Layouts construct and manage their child elements. They do not style content — elements style themselves using `index.css` classes.

#### Element (elements/)

UI layer. Portable content display. Elements know *what* to show, not anything about the project. They receive generic data and render it:

- **step-panel**: visual container for one step in a step-layout
- **text-input**: labeled text field, returns value
- **option-list**: displays options, returns selection
- **searchable-options**: filterable option list, returns selection
- **role-message**: displays a message with a role label and text
- **action-button**: button with label and state
- **info-card**: displays key-value pairs
- **log-line**: single line of timestamped text

Elements style themselves using `index.css` classes. They may have minimal JS for presentational behavior (e.g., focus management), but never business logic. They receive all their data through `init()`.

**The portability test:** every layout and element must work in any project without modification. If it knows about personas, models, or eternego-specific concepts, it belongs in the core layer (widget).

---

## Base Classes

Each layer has a base class that enforces the pattern. Contributors extend the base class; they never subclass `HTMLElement` directly.

```javascript
// modes/mode.js
export default class Mode extends HTMLElement {
    init(props) { this._props = props; this.build(); }
    build() {}                          // subclass renders here
    activate() { /* shown */ }
    deactivate() { /* hidden */ }
}

// apps/app.js
export default class App {
    static name = '';                   // display name
    static icon = '';                   // icon character for modes to read
    init(props) { this._props = props; this.start(); }
    start() {}                          // subclass wires behavior, constructs widgets
    widgets() { return []; }            // returns constructed widget elements
}

// widgets/widget.js
export default class Widget extends HTMLElement {
    static columns = 1;                 // tile width
    static rows = 1;                    // tile height
    init(props) { this._props = props; this.build(); }
    build() {}                          // subclass composes layouts
}

// layouts/layout.js
export default class Layout extends HTMLElement {
    init(props) { this._props = props; this.arrange(); }
    arrange() {}                        // subclass constructs + positions elements
}

// elements/element.js
export default class Element extends HTMLElement {
    init(props) { this._props = props; this.render(); }
    render() {}                         // subclass renders content using index.css classes
}
```

Each base class enforces the `init()` contract and provides the appropriate lifecycle hook for its layer. Subclasses override the hook — never `init()` itself.

---

## File Structure

```
web/os/
  index.html           loads index.css + index.js
  index.css            design system (theme variables, shared classes)
  index.js             OS (boot, state, signals, API)

  modes/
    mode.js            base class
    terminal.js        terminal mode
    desktop.js         desktop mode

  apps/
    app.js             base class
    tty.js             terminal output (stdout for boot + signals)
    persona.js         persona app (chat, memory, skills, signals)
    new-persona.js     creation + migration app

  widgets/
    widget.js          base class
    stdout.js          terminal output stream
    chat.js            chat container
    memory.js          memory viewer
    create.js          persona creation (step-layout + form-layouts)
    migrate.js         persona migration (step-layout + form-layouts)

  layouts/
    layout.js          base class
    card-layout.js     framed container surface
    step-layout.js     step navigation (visibility, dots, go())
    form-layout.js     field collection, validation, submit
    grid-layout.js     widget grid with bin-packing + animation
    tail-layout.js     auto-scroll, pinned to bottom

  elements/
    element.js         base class
    step-panel.js      visual container for one step
    text-input.js      labeled text field
    option-list.js     displays options, returns selection
    searchable-options.js  filterable option list
    role-message.js    message with role and text
    action-button.js   button with label and state
    info-card.js       key-value pairs display
    log-line.js        timestamped text line
```

---

## Rules

### Layer discipline

1. **The full chain is mandatory.** Every path through the tree must be: OS → Mode → App → Widget → Layout → Element. No layer is skipped. No branch stops early. Every piece of visible UI is an element, reached through the complete chain.

2. **Layers alternate strictly.** Every parent-child relationship crosses a boundary: logical → UI → logical → UI. Never skip a layer. A widget (UI) contains layouts (logical). A layout (logical) contains elements (UI). A widget never contains elements directly. A mode never contains widgets. An app never contains elements.

3. **No layer nests with itself.** No widget inside a widget. No layout inside a layout. No app inside an app. Components within the same layer are always siblings, never parent-child.

4. **Siblings are peers.** An app can have widget1, widget2, widget3 as siblings. Never widget1 containing widget2.

```
App (logical)
  ├─ widget1 (UI)
  │    ├─ layout-a (logical)
  │    │    ├─ element1 (UI)
  │    │    └─ element2 (UI)
  │    └─ layout-b (logical)
  │         └─ element3 (UI)
  ├─ widget2 (UI)
  └─ widget3 (UI)
```

### Portability

5. **Platform is portable.** Every layout and element must work in any project without modification. If a component knows about personas, models, or any eternego-specific concept, it belongs in core (app or widget), not platform.

6. **Core is project-specific.** Apps and widgets know about the project domain. They translate domain concepts into generic props for platform components.

### Dependencies

7. **No layer reaches up.** Widgets never import from apps. Apps never import from OS internals. Everything flows down through `init()`.

8. **UI layers don't fetch.** Widgets and elements never make API calls. They receive data and callbacks. If a widget needs data, its parent app fetches it and passes it down.

9. **Logical layers don't style.** Apps and layouts never set CSS classes or inline styles on elements they don't own. They pass data; UI layers decide presentation.

### State

10. **One writer per Feed.** If two things need to write to the same data, they're at the wrong layer. Move the Feed up to where one entity can own it.

### Styling

11. **No cross-layer CSS.** Never write selectors that combine classes from different layers. Each UI component styles itself using classes from `index.css`.

12. **Theme changes touch one file.** If adding a visual feature requires CSS outside `index.css`, reconsider. The feature should compose existing theme classes.

### Contracts

13. **init() is the contract.** Each component documents what it expects in `init()`. This is the interface between layers — keep it explicit and minimal.
