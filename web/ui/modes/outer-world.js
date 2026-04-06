import Mode from './mode.js';

/**
 * Outer World — the conversation experience.
 *
 * The persona's external presence. You talk, it responds,
 * you see its mind breathing beside the dialogue.
 */
class OuterWorld extends Mode {
    static _css = `
        outer-world {
            position: fixed;
            inset: 0;
            padding: 2.5em 3em 3.5em;
            min-height: 0;
            background:
                radial-gradient(ellipse at 50% 45%, rgba(140,160,255,0.025) 0%, transparent 50%),
                var(--bg);
            transition: opacity 0.4s var(--ease);
        }
    `;

    // init({ api, signals, onEnterInner() })
    build() {
        this.constructor._injectStyles();

        this._personaId = null;
        this._personaName = null;
        this._personaBirthday = null;

        // Mind — centered behind everything, the persona's presence
        this._mind = document.createElement('mind-widget');
        this._mind.init({ onOpenMind: () => this._enterInner() });
        this._mind.style.cssText = 'position:absolute;inset:0;z-index:0;';

        // Conversation — on top, full width
        this._conversation = document.createElement('conversation-widget');
        this._conversation.init({
            onSend: (text) => this._send(text),
            loadHistory: (id) => this._loadHistory(id),
        });
        this._conversation.style.cssText = 'position:relative;z-index:1;display:flex;flex-direction:column;flex:1;min-height:0;';

        this.appendChild(this._mind);
        this.appendChild(this._conversation);

        // Chat handler — updates both conversation and mind
        this._chatHandler = (msg) => {
            if (msg.persona_id === this._personaId) {
                this._conversation.receiveMessage(msg.content);
                this._mind.setState('speaking');
                setTimeout(() => this._mind.setState('idle'), 800);
            }
        };

        // Signal handler — updates mind state from websocket events
        this._signalHandler = (e) => {
            for (const sig of e.detail) {
                const p = sig.details?.persona || sig.details?.persona_id || '';
                const pid = typeof p === 'object' ? (p.id || '') : String(p);
                if (!this._personaId || !pid.includes(this._personaId)) continue;

                const title = (sig.title || '').toLowerCase();
                const details = sig.details || {};

                if (title.includes('napping') || title.includes('nap complete')) this._mind.setState('stopped');
                else if (title.includes('asleep') || title.includes('sleeping')) this._mind.setState('sleeping');
                else if (title.includes('awake')) this._mind.setState('idle');
                else if (title.includes('hearing') || title.includes('heard')) this._mind.setState('thinking');
                else if (title.includes('answered') || title.includes('queried')) this._mind.setState('idle');

                if (title.startsWith('pipeline:') && details.stage) {
                    this._mind.activateStage(details.stage, details.impression, details.meaning);
                }
            }
        };
    }

    async setPersona(personaId) {
        if (personaId === this._personaId) return;
        this._personaId = personaId;
        this._props.api.connectPersona(personaId);
        try {
            const data = await this._props.api.fetchPersona(personaId);
            this._personaName = data.name;
            this._personaBirthday = data.birthday || null;
            this._conversation.setPersona(personaId, data.name);
            this._mind.setPersona(data.name);

            // Check if persona is running
            try {
                const mindData = await this._props.api.fetchMind(personaId);
                this._mind.setState('idle');
                this._mind.setGraph(mindData);
            } catch {
                this._mind.setState('stopped');
            }
        } catch {}
    }

    activate() {
        if (this._personaId) this._props.api.connectPersona(this._personaId);
        this._conversation.activate();
        this._props.api.onChat(this._chatHandler);
        this._props.signals.addEventListener('update', this._signalHandler);
    }

    deactivate() {
        this._conversation.deactivate();
        this._props.api.offChat(this._chatHandler);
        this._props.signals.removeEventListener('update', this._signalHandler);
        this._props.api.disconnectPersona();
    }

    async _loadHistory(personaId) {
        try {
            return await this._props.api.fetchConversation(personaId);
        } catch { return []; }
    }

    async _send(text) {
        this._mind.setState('thinking');
        try {
            await this._props.api.hearPersona(this._personaId, text);
        } catch (err) {
            this._conversation.showError(err.message || 'Network error');
            this._mind.setState('idle');
        }
    }

    _enterInner() {
        if (this._props.onEnterInner) this._props.onEnterInner();
    }
}

customElements.define('outer-world', OuterWorld);
export default OuterWorld;
