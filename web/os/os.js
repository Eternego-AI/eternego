/**
 * OS — shared services for the Eternego desktop.
 *
 * Provides: WebSocket signals, navigation, global state.
 * Components import from this module.
 */

const MAX_SIGNALS = 100;

const OS = {
    // ── State ────────────────────────────────────────────────

    booted: false,
    personas: [],
    currentApp: null,      // null = desktop, otherwise app name
    currentPersonaId: null,
    focusedWidget: null,   // null = grid view, otherwise widget name

    // ── Signals (WebSocket, real-time) ───────────────────────

    _signals: [],
    _signalListeners: [],
    _ws: null,

    onSignal(fn) { this._signalListeners.push(fn); },
    offSignal(fn) { this._signalListeners = this._signalListeners.filter(f => f !== fn); },

    signals(personaId) {
        if (!personaId) return [...this._signals];
        return this._signals.filter(msg => {
            const p = msg.details?.persona || msg.details?.persona_id || '';
            const pid = typeof p === 'object' ? (p.id || '') : String(p);
            return pid.includes(personaId);
        });
    },

    _dispatchSignal(msg) {
        this._signals.push(msg);
        if (this._signals.length > MAX_SIGNALS) this._signals.shift();
        for (const fn of this._signalListeners) fn(msg);
    },

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${location.host}/ws`);

        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                if (msg.title) this._dispatchSignal(msg);
            } catch {}
        };

        ws.onclose = () => {
            setTimeout(() => this.connect(), 3000);
        };

        this._ws = ws;
    },

    // ── API ──────────────────────────────────────────────────

    async fetchPersonas() {
        try {
            const res = await fetch('/api/personas');
            const data = await res.json();
            this.personas = data.personas || [];
        } catch {
            this.personas = [];
        }
        return this.personas;
    },

    // ── Boot ─────────────────────────────────────────────────

    async boot() {
        this.connect();
        const minWait = new Promise(r => setTimeout(r, 1500));
        await this.fetchPersonas();
        await minWait;
        this.booted = true;
    },

    // ── Navigation ───────────────────────────────────────────

    _onNavigate: [],

    onNavigate(fn) { this._onNavigate.push(fn); },

    _notify() {
        for (const fn of this._onNavigate) fn({
            app: this.currentApp,
            personaId: this.currentPersonaId,
            widget: this.focusedWidget,
        });
    },

    open(app, opts) {
        this.currentApp = app;
        this.focusedWidget = null;
        if (opts?.personaId) this.currentPersonaId = opts.personaId;

        if (app === 'persona') {
            history.pushState({ app, id: this.currentPersonaId }, '', `/?persona=${this.currentPersonaId}`);
        } else {
            history.pushState({ app }, '', `/?${app}`);
        }

        this._notify();
    },

    focus(widgetName) {
        this.focusedWidget = widgetName;
        this._notify();
    },

    minimize() {
        if (this.focusedWidget) {
            this.focusedWidget = null;
        } else {
            this.currentApp = null;
            this.currentPersonaId = null;
            history.pushState({ app: null }, '', '/');
        }
        this._notify();
    },
};

// Browser back/forward
window.addEventListener('popstate', (e) => {
    const state = e.state;
    if (!state || !state.app) {
        OS.currentApp = null;
        OS.focusedWidget = null;
        OS._notify();
    } else if (state.app === 'persona' && state.id) {
        OS.currentApp = 'persona';
        OS.currentPersonaId = state.id;
        OS.focusedWidget = null;
        OS._notify();
    } else {
        OS.currentApp = state.app;
        OS.focusedWidget = null;
        OS._notify();
    }
});

// Global keyboard: Escape always minimizes
document.addEventListener('keydown', (e) => {
    if (!OS.booted) return;
    if (e.key === 'Escape' && OS.currentApp) {
        e.preventDefault();
        OS.minimize();
    }
});

export default OS;
