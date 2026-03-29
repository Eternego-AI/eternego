/**
 * OS — entry point. Owns boot, state, signals, API, modes.
 */

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

const OS = {
    // ── State ────────────────────────────────────────────────
    booted: false,
    personas: [],
    models: [],
    currentApp: null,
    currentPersonaId: null,

    // ── Feeds ────────────────────────────────────────────────
    signals: new Feed(),

    // ── App Registry ─────────────────────────────────────────
    _apps: [],

    registerApp(AppClass) {
        this._apps.push(AppClass);
    },

    get apps() { return this._apps; },

    // ── Chat (WebSocket incoming) ────────────────────────────
    _chatListeners: [],
    onChat(fn) { this._chatListeners.push(fn); },
    offChat(fn) { this._chatListeners = this._chatListeners.filter(f => f !== fn); },
    _dispatchChat(msg) { for (const fn of this._chatListeners) fn(msg); },

    // ── WebSocket ────────────────────────────────────────────
    _ws: null,
    _wsPersonaId: null,

    connectPersona(personaId) {
        if (this._wsPersonaId === personaId && this._ws) return;
        this.disconnectPersona();
        this._wsPersonaId = personaId;
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${location.host}/ws/${personaId}`);

        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                if (msg.type === 'chat_message') this._dispatchChat(msg);
                else if (msg.title) this.signals.push(msg);
            } catch {}
        };

        ws.onclose = () => {
            if (this._wsPersonaId === personaId) {
                setTimeout(() => this.connectPersona(personaId), 3000);
            }
        };
        this._ws = ws;
    },

    disconnectPersona() {
        this._wsPersonaId = null;
        if (this._ws) {
            this._ws.onclose = null;
            this._ws.close();
            this._ws = null;
        }
    },

    // ── API ──────────────────────────────────────────────────
    async fetchEnvironment() {
        try {
            const res = await fetch('/api/models');
            const data = await res.json();
            this.models = data.models || [];
        } catch { this.models = []; }
        return this.models;
    },

    async fetchPersonas() {
        try {
            const res = await fetch('/api/personas');
            const data = await res.json();
            this.personas = data.personas || [];
        } catch { this.personas = []; }
        return this.personas;
    },

    // ── Boot ─────────────────────────────────────────────────
    _mode: null,

    async boot() {
        const minWait = new Promise(r => setTimeout(r, 1500));
        await Promise.all([this.fetchEnvironment(), this.fetchPersonas()]);
        await minWait;
        this.booted = true;
    },

    setMode(modeEl) {
        if (this._mode) this._mode.deactivate();
        this._mode = modeEl;
        if (this._mode) this._mode.activate();
    },

    // ── Navigation ───────────────────────────────────────────
    _onNavigate: [],
    onNavigate(fn) { this._onNavigate.push(fn); },

    _notify() {
        for (const fn of this._onNavigate) fn({
            app: this.currentApp,
            personaId: this.currentPersonaId,
        });
    },

    _buildUrl() {
        if (!this.currentApp) return '/';
        const appParam = this.currentApp === 'persona'
            ? `persona-${this.currentPersonaId}`
            : this.currentApp;
        return `/?app=${appParam}`;
    },

    _parseUrl() {
        const params = new URLSearchParams(location.search);
        const app = params.get('app');
        if (!app) {
            this.currentApp = null;
            this.currentPersonaId = null;
            return;
        }
        if (app.startsWith('persona-')) {
            this.currentApp = 'persona';
            this.currentPersonaId = app.slice('persona-'.length);
        } else {
            this.currentApp = app;
            this.currentPersonaId = null;
        }
    },

    restore() {
        this._parseUrl();
        if (this.currentApp) this._notify();
    },

    open(app, opts) {
        this.currentApp = app;
        if (opts?.personaId) this.currentPersonaId = opts.personaId;
        history.pushState(null, '', this._buildUrl());
        this._notify();
    },

    minimize() {
        this.currentApp = null;
        this.currentPersonaId = null;
        history.pushState(null, '', this._buildUrl());
        this._notify();
    },

    async deletePersona(personaId) {
        try {
            const res = await fetch(`/api/persona/${personaId}/delete`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json();
                console.error('Delete failed:', err.detail || 'Unknown error');
                return false;
            }
        } catch {
            console.error('Delete failed: network error');
            return false;
        }
        await this.fetchPersonas();
        this.minimize();
        return true;
    },

    signalsFor(personaId) {
        if (!personaId) return [...this.signals.items];
        return this.signals.items.filter(msg => {
            const p = msg.details?.persona || msg.details?.persona_id || '';
            const pid = typeof p === 'object' ? (p.id || '') : String(p);
            return pid.includes(personaId);
        });
    },
};

window.addEventListener('popstate', () => { OS._parseUrl(); OS._notify(); });
document.addEventListener('keydown', (e) => {
    if (!OS.booted) return;
    if (e.key === 'Escape' && OS.currentApp) { e.preventDefault(); OS.minimize(); }
});

export default OS;
export { Feed };
