/**
 * UI — logical state, API, signals, and mode navigation.
 * No DOM. The visual frame lives in frame.js.
 */

class Feed extends EventTarget {
    #items = [];
    get items() { return this.#items; }
    push(...values) {
        this.#items.push(...values);
        this.dispatchEvent(new CustomEvent('update', { detail: values }));
    }
}

const UI = {
    booted: false,
    personas: [],
    currentPersonaId: null,
    currentMode: null,

    signals: new Feed(),

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
            if (this._wsPersonaId === personaId) setTimeout(() => this.connectPersona(personaId), 3000);
        };
        this._ws = ws;
    },

    disconnectPersona() {
        this._wsPersonaId = null;
        if (this._ws) { this._ws.onclose = null; this._ws.close(); this._ws = null; }
    },

    // ── API helpers ──────────────────────────────────────────
    async _get(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || res.statusText);
        }
        return res.json();
    },

    async _post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || res.statusText);
        }
        return res.json();
    },

    async _postForm(url, formData) {
        const res = await fetch(url, { method: 'POST', body: formData });
        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || res.statusText);
        }
        return res.json();
    },

    // ── API: list ────────────────────────────────────────────
    async fetchPersonas() {
        try {
            const data = await this._get('/api/personas');
            this.personas = data.personas || [];
        } catch { this.personas = []; }
        return this.personas;
    },

    // ── API: persona data ────────────────────────────────────
    async fetchPersona(id) {
        try {
            return await this._get(`/api/persona/${id}`);
        } catch (e) { return null; }
    },

    async fetchConversation(id) {
        try {
            const data = await this._get(`/api/persona/${id}/conversation`);
            return data.messages || [];
        } catch { return []; }
    },

    async fetchMind(id) {
        try {
            return await this._get(`/api/persona/${id}/mind`);
        } catch { return null; }
    },

    async fetchOversee(id) {
        try {
            return await this._get(`/api/persona/${id}/oversee`);
        } catch { return null; }
    },

    // ── API: persona actions ─────────────────────────────────
    async hearPersona(id, message) {
        try {
            await this._post(`/api/persona/${id}/hear`, { message });
            return { success: true };
        } catch (e) { return { success: false, error: e.message }; }
    },

    async actionPersona(id, action) {
        try {
            await this._post(`/api/persona/${id}/${action}`);
            return { success: true };
        } catch (e) { return { success: false, error: e.message }; }
    },

    async controlPersona(id, entryIds) {
        try {
            await this._post(`/api/persona/${id}/control`, { entry_ids: entryIds });
            return { success: true };
        } catch (e) { return { success: false, error: e.message }; }
    },

    async feedPersona(id, file, source) {
        try {
            const form = new FormData();
            form.append('history', file);
            form.append('source', source);
            const data = await this._postForm(`/api/persona/${id}/feed`, form);
            return { success: true, message: data.message };
        } catch (e) { return { success: false, error: e.message }; }
    },

    async deletePersona(personaId) {
        try {
            await this._post(`/api/persona/${personaId}/delete`);
        } catch { return false; }
        location.href = '/';
        return true;
    },

    // ── API: setup ───────────────────────────────────────────
    async prepareEnvironment(model) {
        try {
            const data = await this._post('/api/environment/prepare', { model });
            return { success: true, message: data.message };
        } catch (e) { return { success: false, message: e.message }; }
    },

    async createPersona(data) {
        try {
            const result = await this._post('/api/persona/create', data);
            return { success: true, persona_id: result.persona_id, recovery_phrase: result.recovery_phrase, message: result.message };
        } catch (e) { return { success: false, message: e.message }; }
    },

    async migratePersona(formData) {
        try {
            const result = await this._postForm('/api/persona/migrate', formData);
            return { success: true, persona_id: result.persona_id, message: result.message };
        } catch (e) { return { success: false, message: e.message }; }
    },

    async pairChannel(code) {
        try {
            await this._post(`/api/pair/${code}`);
            return { success: true };
        } catch (e) { return { success: false, message: e.message }; }
    },

    // ── Boot ─────────────────────────────────────────────────
    async boot() {
        await this.fetchPersonas();
        this.booted = true;
    },

    // ── API object for modes ─────────────────────────────────
    _api() {
        return {
            fetchPersona: (id) => this.fetchPersona(id),
            fetchConversation: (id) => this.fetchConversation(id),
            fetchMind: (id) => this.fetchMind(id),
            fetchOversee: (id) => this.fetchOversee(id),
            hearPersona: (id, msg) => this.hearPersona(id, msg),
            actionPersona: (id, action) => this.actionPersona(id, action),
            controlPersona: (id, ids) => this.controlPersona(id, ids),
            feedPersona: (id, file, source) => this.feedPersona(id, file, source),
            deletePersona: (id) => this.deletePersona(id),
            connectPersona: (id) => this.connectPersona(id),
            disconnectPersona: () => this.disconnectPersona(),
            onChat: (fn) => this.onChat(fn),
            offChat: (fn) => this.offChat(fn),
            createPersona: (data) => this.createPersona(data),
            migratePersona: (fd) => this.migratePersona(fd),
            prepareEnvironment: (model) => this.prepareEnvironment(model),
            pairChannel: (code) => this.pairChannel(code),
            fetchPersonas: () => this.fetchPersonas(),
        };
    },

    // ── Mode change notification ─────────────────────────────
    _onModeChange: [],
    onModeChange(fn) { this._onModeChange.push(fn); },
    _notifyModeChange(detail) {
        for (const fn of this._onModeChange) fn(detail);
    },

    // ── Navigation ───────────────────────────────────────────
    enterOuterWorld(personaId) {
        this.currentPersonaId = personaId;
        this.currentMode = 'outer';
        history.pushState(null, '', `/?p=${personaId}`);
        this._notifyModeChange({ mode: 'outer', personaId });
    },

    async enterInnerWorld() {
        if (!this.currentPersonaId) return;
        this.currentMode = 'inner';
        const [data, persona] = await Promise.all([
            this.fetchOversee(this.currentPersonaId),
            this.fetchPersona(this.currentPersonaId),
        ]);
        this._notifyModeChange({
            mode: 'inner',
            personaId: this.currentPersonaId,
            data,
            persona,
        });
    },

    enterSetup() {
        this.currentMode = 'setup';
        history.pushState(null, '', '/?v=setup');
        this._notifyModeChange({ mode: 'setup' });
    },

    // SetupApp class is injected from index.html to avoid circular imports
    _SetupApp: null,
    registerSetupApp(cls) { this._SetupApp = cls; },
};

window.addEventListener('popstate', () => {
    const params = new URLSearchParams(location.search);
    const p = params.get('p');
    const v = params.get('v');
    if (p) UI.enterOuterWorld(p);
    else if (v === 'setup') UI.enterSetup();
    else if (UI.personas.length > 0) UI.enterOuterWorld(UI.personas[0].id);
    else UI._notifyModeChange({ mode: 'welcome' });
});

export default UI;
export { Feed };
