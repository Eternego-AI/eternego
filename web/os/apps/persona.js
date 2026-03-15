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

        const chat = document.createElement('chat-widget');
        chat.init({
            onSend: (personaId, text) => this._send(personaId, text),
            onChat: (fn) => OS.onChat(fn),
            offChat: (fn) => OS.offChat(fn),
        });

        const memory = document.createElement('info-widget');
        memory.init({ title: 'Memory', text: 'What your persona knows about you' });

        const skills = document.createElement('info-widget');
        skills.init({ title: 'Skills', text: 'Equipped abilities and meanings' });

        const signals = document.createElement('signal-log-widget');
        signals.init({
            signals: this._props.signals,
            getSignalsFor: (id) => OS.signalsFor(id),
        });

        this._chat = chat;
        this._signalLog = signals;
        this._el = div;
        this._widgets = [chat, memory, skills, signals];
        this._personaId = null;
    }

    setPersona(personaId) {
        if (personaId === this._personaId) return;
        this._personaId = personaId;
        this._chat.setPersona(personaId);
        this._signalLog.setPersona(personaId);
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
