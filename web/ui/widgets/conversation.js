import Widget from './widget.js';
import { cornerDownLeft, image as imageIcon, x as xIcon } from '../icons.js';

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
        conversation-widget .cw-send, conversation-widget .cw-attach {
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
        conversation-widget .cw-send:hover, conversation-widget .cw-attach:hover {
            color: var(--accent-text);
            border-color: var(--accent-border);
        }
        conversation-widget .cw-pending {
            display: none;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-xs) var(--space-md);
            margin: 0 var(--space-sm) var(--space-xs);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
        }
        conversation-widget .cw-pending.active { display: inline-flex; }
        conversation-widget .cw-pending-thumb {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-md);
            object-fit: cover;
        }
        conversation-widget .cw-pending-name {
            font-size: var(--text-sm);
            color: var(--text-secondary);
            max-width: 260px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        conversation-widget .cw-pending-clear {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 0;
            display: flex;
        }
        conversation-widget .cw-pending-clear:hover { color: var(--destructive-text); }
    `;

    // init({ onSend(text), onSendImage(file, caption), mediaUrl(source), loadHistory(personaId) })
    build() {
        this.constructor._injectStyles();
        this._personaId = null;
        this._personaName = null;
        this._lastSpeaker = null;
        this._pendingFile = null;
        this._pendingPreviewUrl = null;

        // Messages
        this._tail = document.createElement('tail-layout');
        this._tail.init({});
        this._tail.className = 'cw-messages';

        // Pending attachment preview
        this._pending = document.createElement('div');
        this._pending.className = 'cw-pending';
        this._pending.innerHTML = `
            <img class="cw-pending-thumb" alt="">
            <span class="cw-pending-name"></span>
            <button type="button" class="cw-pending-clear" aria-label="Remove">${xIcon(14)}</button>
        `;
        this._pendingThumb = this._pending.querySelector('.cw-pending-thumb');
        this._pendingName = this._pending.querySelector('.cw-pending-name');
        this._pending.querySelector('.cw-pending-clear').addEventListener('click', () => this._clearPending());

        // Compose
        const compose = document.createElement('div');
        compose.className = 'cw-compose';

        this._attachBtn = document.createElement('button');
        this._attachBtn.className = 'cw-attach';
        this._attachBtn.type = 'button';
        this._attachBtn.setAttribute('aria-label', 'Attach image');
        this._attachBtn.innerHTML = imageIcon(16);

        this._fileInput = document.createElement('input');
        this._fileInput.type = 'file';
        this._fileInput.accept = 'image/*';
        this._fileInput.style.display = 'none';
        this._attachBtn.addEventListener('click', () => this._fileInput.click());
        this._fileInput.addEventListener('change', () => {
            if (this._fileInput.files && this._fileInput.files.length) {
                this._setPending(this._fileInput.files[0]);
                this._fileInput.value = '';
            }
        });

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
            if (!this._personaId) return;
            const text = this._input.value.trim();
            if (this._pendingFile) {
                const file = this._pendingFile;
                const previewUrl = this._pendingPreviewUrl;
                this._pendingFile = null;
                this._pendingPreviewUrl = null;
                this._pending.classList.remove('active');
                this._input.value = '';
                autoResize();
                this.addMediaMessage('person', previewUrl, text);
                if (this._props.onSendImage) this._props.onSendImage(file, text);
                return;
            }
            if (!text) return;
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

        compose.appendChild(this._attachBtn);
        compose.appendChild(this._fileInput);
        compose.appendChild(this._input);
        compose.appendChild(this._sendBtn);

        this.appendChild(this._tail);
        this.appendChild(this._pending);
        this.appendChild(compose);
    }

    _setPending(file) {
        if (this._pendingPreviewUrl) URL.revokeObjectURL(this._pendingPreviewUrl);
        this._pendingFile = file;
        this._pendingPreviewUrl = URL.createObjectURL(file);
        this._pendingThumb.src = this._pendingPreviewUrl;
        this._pendingName.textContent = file.name;
        this._pending.classList.add('active');
    }

    _clearPending() {
        if (this._pendingPreviewUrl) URL.revokeObjectURL(this._pendingPreviewUrl);
        this._pendingFile = null;
        this._pendingPreviewUrl = null;
        this._pending.classList.remove('active');
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

    addMediaMessage(role, source, caption, time) {
        if (role !== 'system' && role !== this._lastSpeaker) {
            const label = document.createElement('div');
            label.className = 'cw-speaker';
            label.textContent = role === 'person' ? 'you' : (this._personaName || 'persona');
            this._tail.append(label);
            this._lastSpeaker = role;
        }
        const timeStr = time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const el = document.createElement('media-attachment');
        el.init({ role, source, caption: caption || '', time: timeStr });
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
                const role = msg.role === 'person' ? 'person' : 'persona';
                if (msg.media && msg.media.source) {
                    const url = this._props.mediaUrl ? this._props.mediaUrl(msg.media.source) : msg.media.source;
                    this.addMediaMessage(role, url, msg.media.caption || msg.content || '', time);
                } else {
                    this.addMessage(role, msg.content, time);
                }
            }
        } catch {}
    }
}

customElements.define('conversation-widget', ConversationWidget);
export default ConversationWidget;
