import App from './app.js';
import OS from '../index.js';

export default class PersonaApp extends App {
    static appId = 'persona';
    static appName = 'Persona';
    static icon = '';

    // init({ signals: Feed })
    start() {
        const div = document.createElement('div');
        div.id = 'persona-app';

        const personaInfo = document.createElement('persona-info-widget');
        personaInfo.init({});

        const control = document.createElement('control-widget');
        control.init({
            onAction: (actionId) => this._onAction(actionId),
        });

        const chat = document.createElement('chat-widget');
        chat.init({
            onSend: (personaId, text) => this._send(personaId, text),
            onChat: (fn) => OS.onChat(fn),
            offChat: (fn) => OS.offChat(fn),
        });

        const feed = document.createElement('feed-widget');
        feed.init({
            onFeed: (file, source) => this._feed(file, source),
        });

        const signals = document.createElement('signal-log-widget');
        signals.init({
            signals: this._props.signals,
            getSignalsFor: (id) => OS.signalsFor(id),
        });

        this._personaInfo = personaInfo;
        this._chat = chat;
        this._feed_widget = feed;
        this._signalLog = signals;
        this._el = div;
        this._widgets = [personaInfo, control, chat, feed, signals];
        this._personaId = null;
    }

    async setPersona(personaId) {
        if (personaId === this._personaId) return;
        this._personaId = personaId;
        this._chat.setPersona(personaId);
        this._signalLog.setPersona(personaId);
        await this._loadPersonaInfo(personaId);
    }

    async _loadPersonaInfo(personaId) {
        try {
            const res = await fetch(`/api/persona/${personaId}`);
            if (!res.ok) return;
            const data = await res.json();
            this._personaInfo.update(data);
        } catch {}
    }

    activate(widget) {
        this._chat.activate();
    }

    deactivate() {
        this._chat.deactivate();
    }

    setFocused(widgetName) {
        for (const w of this._widgets) {
            const name = w.getAttribute('widget');
            const focused = name === widgetName;
            if (w.setFocused) w.setFocused(focused);
        }
    }

    widgets() { return this._widgets; }
    get el() { return this._el; }

    async _onAction(actionId) {
        if (!this._personaId) return;
        if (actionId === 'delete') {
            await OS.deletePersona(this._personaId);
            return;
        }
        try {
            const res = await fetch(`/api/persona/${this._personaId}/${actionId}`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json();
                console.error(`Action ${actionId} failed:`, err.detail || 'Unknown error');
            }
        } catch {
            console.error(`Action ${actionId} failed: network error`);
        }
    }

    async _feed(file, source) {
        if (!this._personaId) return { success: false, message: 'No persona selected' };
        const form = new FormData();
        form.append('history', file);
        form.append('source', source);
        try {
            const res = await fetch(`/api/persona/${this._personaId}/feed`, { method: 'POST', body: form });
            if (!res.ok) {
                const err = await res.json();
                return { success: false, message: err.detail || 'Feeding failed' };
            }
            return { success: true, message: 'Persona fed successfully' };
        } catch {
            return { success: false, message: 'Network error' };
        }
    }

    async _send(personaId, text) {
        try {
            const res = await fetch(`/api/persona/${personaId}/hear`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text }),
            });
            if (!res.ok) {
                const err = await res.json();
                this._chat._hideThinking();
                this._chat._addMessage('system', err.detail || 'Error sending message');
                this._chat._input.disabled = false;
                this._chat._sendBtn.disabled = false;
            }
        } catch {
            this._chat._hideThinking();
            this._chat._addMessage('system', 'Network error');
            this._chat._input.disabled = false;
            this._chat._sendBtn.disabled = false;
        }
    }
}
