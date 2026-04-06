import Widget from './widget.js';
import { cornerDownLeft } from '../icons.js';

class ConversationWidget extends Widget {
    static _css = `
        conversation-widget {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0;
        }

        /* Messages */
        conversation-widget .cw-messages {
            gap: var(--space-xs);
            padding: var(--space-lg) var(--space-lg) var(--space-md);
        }

        /* Speaker labels */
        conversation-widget .cw-speaker {
            font-size: var(--text-xs);
            color: var(--text-muted);
            letter-spacing: 1px;
            text-transform: lowercase;
            padding: var(--space-md) 0 var(--space-xs);
        }

        /* Compose */
        conversation-widget .cw-compose {
            display: flex;
            gap: 8px;
            padding-top: 8px;
            padding-right: 8px;
        }
        conversation-widget .cw-input {
            flex: 1;
            padding: 14px 18px;
            background: rgba(0,0,0,0.35);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-xl);
            color: var(--text-body);
            font-family: var(--font);
            font-size: 13px;
            line-height: 1.5;
            outline: none;
            resize: none;
            overflow-y: hidden;
            min-height: 46px;
            max-height: 200px;
            transition: border-color 0.3s var(--ease), background 0.3s var(--ease);
        }
        conversation-widget .cw-input::placeholder { color: var(--text-faint); }
        conversation-widget .cw-input:focus { border-color: var(--accent-border); background: rgba(0,0,0,0.45); }
        conversation-widget .cw-send {
            width: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: none;
            border: 1px solid var(--border-default);
            border-radius: var(--radius-xl);
            color: var(--text-muted);
            cursor: pointer;
            transition: color 0.2s, border-color 0.2s;
        }
        conversation-widget .cw-send:hover { color: var(--accent-text); border-color: var(--accent-border); }
    `;

    // init({ onSend(text), loadHistory(personaId) })
    build() {
        this.constructor._injectStyles();
        this._personaId = null;
        this._personaName = null;
        this._lastSpeaker = null;

        // Messages
        this._tail = document.createElement('tail-layout');
        this._tail.init({});
        this._tail.className = 'cw-messages';

        // Compose
        const compose = document.createElement('div');
        compose.className = 'cw-compose';

        this._input = document.createElement('textarea');
        this._input.className = 'cw-input';
        this._input.placeholder = 'Say something...';
        this._input.rows = 1;

        this._sendBtn = document.createElement('button');
        this._sendBtn.className = 'cw-send';
        this._sendBtn.innerHTML = cornerDownLeft(16);

        const autoResize = () => {
            this._input.style.height = 'auto';
            this._input.style.height = Math.min(this._input.scrollHeight, 200) + 'px';
            this._input.style.overflowY = this._input.scrollHeight > 200 ? 'auto' : 'hidden';
        };

        const send = () => {
            const text = this._input.value.trim();
            if (!text || !this._personaId) return;
            this._input.value = '';
            autoResize();
            this.addMessage('person', text);
            if (this._props.onSend) this._props.onSend(text);
        };

        this._input.addEventListener('input', autoResize);
        this._input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
        });
        this._sendBtn.addEventListener('click', send);

        compose.appendChild(this._input);
        compose.appendChild(this._sendBtn);

        this.appendChild(this._tail);
        this.appendChild(compose);
    }

    setPersona(personaId, name) {
        if (personaId === this._personaId) return;
        this._personaId = personaId;
        this._personaName = name;
        this._lastSpeaker = null;
        this._tail.innerHTML = '';
        this._loadHistory();
    }

    activate() {
        setTimeout(() => this._input.focus(), 100);
    }

    deactivate() {}

    addMessage(role, content, time) {
        if (role !== 'system' && role !== this._lastSpeaker) {
            const label = document.createElement('div');
            label.className = 'cw-speaker';
            label.textContent = role === 'person' ? 'you' : (this._personaName || 'persona');
            this._tail.append(label);
            this._lastSpeaker = role;
        }
        const timeStr = time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const el = document.createElement('role-message');
        el.init({ role, text: content, time: timeStr });
        this._tail.append(el);
    }

    receiveMessage(content) {
        this.addMessage('persona', content);
    }

    showError(message) {
        this.addMessage('system', message);
    }

    async _loadHistory() {
        if (!this._personaId || !this._props.loadHistory) return;
        try {
            const messages = await this._props.loadHistory(this._personaId);
            this._tail.innerHTML = '';
            this._lastSpeaker = null;
            for (const msg of messages) {
                const time = msg.time ? new Date(msg.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null;
                this.addMessage(msg.role === 'person' ? 'person' : 'persona', msg.content, time);
            }
        } catch {}
    }
}

customElements.define('conversation-widget', ConversationWidget);
export default ConversationWidget;
