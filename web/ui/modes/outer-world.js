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
        outer-world .ow-pair-tray {
            position: absolute;
            top: var(--space-lg);
            right: var(--space-lg);
            display: flex;
            gap: var(--space-sm);
            z-index: 2;
        }
        outer-world .ow-pair-btn {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
            padding: var(--space-xs) var(--space-md);
            background: var(--destructive-bg);
            border: 1px solid var(--destructive-border);
            border-radius: var(--radius-md);
            color: var(--destructive-text);
            font-family: var(--font);
            font-size: var(--text-sm);
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
        }
        outer-world .ow-pair-btn:hover { background: rgba(255, 80, 80, 0.14); border-color: rgba(255, 120, 120, 0.4); }
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
            onSendImage: (file, caption) => this._sendImage(file, caption),
            mediaUrl: (source) => this._props.api.mediaUrl(this._personaId, source),
            loadHistory: (id) => this._loadHistory(id),
        });
        this._conversation.style.cssText = 'position:relative;z-index:1;display:flex;flex-direction:column;flex:1;min-height:0;';

        this._pairTray = document.createElement('div');
        this._pairTray.className = 'ow-pair-tray';

        this.appendChild(this._mind);
        this.appendChild(this._conversation);
        this.appendChild(this._pairTray);

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

                if (title === 'heard' && details.content && details.channel?.type && details.channel.type !== 'web') {
                    this._conversation.addMessage('person', details.content);
                }

                if (title === 'seen' && details.source && details.channel?.type && details.channel.type !== 'web') {
                    const url = this._props.api.mediaUrl(this._personaId, details.source);
                    this._conversation.addMediaMessage('person', url, details.caption || '');
                }

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
            this._renderPairTray(data.channels || []);

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

    _renderPairTray(channels) {
        this._pairTray.innerHTML = '';
        for (const ch of channels) {
            if (ch.verified) continue;
            if (ch.type !== 'telegram' && ch.type !== 'discord') continue;
            const btn = document.createElement('button');
            btn.className = 'ow-pair-btn';
            btn.type = 'button';
            btn.textContent = `Pair ${ch.type}`;
            btn.addEventListener('click', () => this._openPair(ch.type));
            this._pairTray.appendChild(btn);
        }
    }

    _openPair(channelType) {
        const modal = document.createElement('modal-layout');
        modal.init({});
        document.body.appendChild(modal);

        const widget = document.createElement('pair-widget');
        widget.init({
            api: this._props.api,
            personaId: this._personaId,
            channelType,
            onDone: async () => {
                modal.remove();
                try {
                    const data = await this._props.api.fetchPersona(this._personaId);
                    this._renderPairTray(data.channels || []);
                } catch {}
            },
            onCancel: () => modal.remove(),
        });
        modal.setContent(widget);
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

    async _sendImage(file, caption) {
        this._mind.setState('thinking');
        try {
            const result = await this._props.api.seePersona(this._personaId, file, caption);
            if (!result.success) {
                this._conversation.showError(result.error || 'Upload failed');
                this._mind.setState('idle');
            }
        } catch (err) {
            this._conversation.showError(err.message || 'Upload failed');
            this._mind.setState('idle');
        }
    }

    _enterInner() {
        if (this._props.onEnterInner) this._props.onEnterInner();
    }
}

customElements.define('outer-world', OuterWorld);
export default OuterWorld;
