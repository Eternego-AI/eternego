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

    async fetchProviderConfig() {
        try {
            return await this._get('/api/config/providers');
        } catch { return { local: { url: 'http://localhost:11434' }, anthropic: { url: 'https://api.anthropic.com' }, openai: { url: 'https://api.openai.com' } }; }
    },

    // ── API: persona data ────────────────────────────────────
    async fetchPersona(id) {
        if (!this.personas.length) await this.fetchPersonas();
        return this.personas.find(p => p.id === id) || null;
    },

    async fetchConversation(id) {
        try {
            const data = await this._get(`/api/persona/${id}/conversation`);
            return data.messages || [];
        } catch { return []; }
    },

    async fetchDiagnose(id) {
        try {
            return await this._get(`/api/persona/${id}/diagnose`);
        } catch { return null; }
    },

    async updatePersona(id, fields) {
        try {
            return await this._post(`/api/persona/${id}/update`, fields);
        } catch (e) { return { error: e.message }; }
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

    async seePersona(id, file, caption) {
        try {
            const form = new FormData();
            form.append('image', file);
            if (caption) form.append('caption', caption);
            await this._postForm(`/api/persona/${id}/see`, form);
            return { success: true };
        } catch (e) { return { success: false, error: e.message }; }
    },

    mediaUrl(id, source) {
        const base = (source || '').split('/').pop();
        return `/api/persona/${id}/media/${encodeURIComponent(base)}`;
    },

    async actionPersona(id, action) {
        try {
            await this._post(`/api/persona/${id}/${action}`);
            return { success: true };
        } catch (e) { return { success: false, error: e.message }; }
    },

    async exportPersona(id) {
        try {
            const response = await fetch(`/api/persona/${id}/export`);
            if (!response.ok) {
                const err = await response.json();
                return { success: false, error: err.detail };
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${id}.diary`;
            a.click();
            URL.revokeObjectURL(url);
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
    async createPersona(data) {
        try {
            const result = await this._post('/api/persona/create', data);
            return { success: true, persona_id: result.persona?.id, recovery_phrase: result.recovery_phrase, message: result.message };
        } catch (e) { return { success: false, message: e.message }; }
    },

    async migratePersona(formData) {
        try {
            const result = await this._postForm('/api/persona/migrate', formData);
            return { success: true, persona_id: result.persona?.id, message: result.message };
        } catch (e) { return { success: false, message: e.message }; }
    },

    async pairChannel(code, personaId) {
        try {
            await this._post(`/api/persona/${personaId}/pair`, { code });
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
            fetchDiagnose: (id) => this.fetchDiagnose(id),
            updatePersona: (id, fields) => this.updatePersona(id, fields),
            fetchOversee: (id) => this.fetchOversee(id),
            hearPersona: (id, msg) => this.hearPersona(id, msg),
            seePersona: (id, file, caption) => this.seePersona(id, file, caption),
            mediaUrl: (id, source) => this.mediaUrl(id, source),
            actionPersona: (id, action) => this.actionPersona(id, action),
            exportPersona: (id) => this.exportPersona(id),
            controlPersona: (id, ids) => this.controlPersona(id, ids),
            feedPersona: (id, file, source) => this.feedPersona(id, file, source),
            deletePersona: (id) => this.deletePersona(id),
            connectPersona: (id) => this.connectPersona(id),
            disconnectPersona: () => this.disconnectPersona(),
            onChat: (fn) => this.onChat(fn),
            offChat: (fn) => this.offChat(fn),
            createPersona: (data) => this.createPersona(data),
            migratePersona: (fd) => this.migratePersona(fd),
            fetchProviderConfig: () => this.fetchProviderConfig(),
            pairChannel: (code, personaId) => this.pairChannel(code, personaId),
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
        history.pushState(null, '', `/persona/${personaId}`);
        this._notifyModeChange({ mode: 'outer', personaId });
    },

    async enterInnerWorld() {
        if (!this.currentPersonaId) return;
        this.currentMode = 'inner';
        history.pushState(null, '', `/persona/${this.currentPersonaId}/inner`);
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
        history.pushState(null, '', '/setup');
        this._notifyModeChange({ mode: 'setup' });
    },

    enterStatus() {
        if (!this.currentPersonaId) return;
        this.currentMode = 'status';
        history.pushState(null, '', `/persona/${this.currentPersonaId}/status`);
        this._notifyModeChange({ mode: 'status', personaId: this.currentPersonaId });
    },

    // Resolve location.pathname to a mode and dispatch.
    async routeFromPath() {
        const path = location.pathname || '/';
        if (path === '/setup' || path === '/setup/') return this.enterSetup();
        const m = path.match(/^\/persona\/([^/]+)(?:\/(inner|status))?\/?$/);
        if (m) {
            const id = m[1];
            const view = m[2];
            if (view === 'inner') {
                this.currentPersonaId = id;
                return this.enterInnerWorld();
            }
            if (view === 'status') {
                this.currentPersonaId = id;
                return this.enterStatus();
            }
            return this.enterOuterWorld(id);
        }
        if (this.personas.length > 0) return this.enterOuterWorld(this.personas[0].id);
        if (path !== '/setup') return this.enterSetup();
    },

    _SetupApp: null,
    registerSetupApp(cls) { this._SetupApp = cls; },
};

window.addEventListener('popstate', () => {
    UI.routeFromPath();
});

export default UI;
export { Feed };
