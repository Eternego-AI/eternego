import Widget from './widget.js';
import { cornerDownLeft, image as imageIcon, x as xIcon, send, hash, globe } from '../icons.js';

const CHANNEL_ICONS = { telegram: send, discord: hash, web: globe };
const CHANNEL_LABELS = { telegram: 'Telegram', discord: 'Discord', web: 'Web' };

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
            gap: var(--space-sm);
            padding: var(--space-lg) var(--space-lg) var(--space-md);
        }

        /* Turn — label column + body column */
        conversation-widget .cw-turn {
            display: flex;
            gap: var(--space-md);
            align-items: baseline;
            padding: 2px 0;
            animation: cw-arrive 0.3s var(--ease);
        }
        @keyframes cw-arrive { from { opacity: 0; transform: translateY(3px); } }
        conversation-widget .cw-label {
            flex: 0 0 72px;
            text-align: right;
            font-size: var(--text-sm);
            color: var(--text-muted);
            text-transform: lowercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        conversation-widget .cw-turn.cw-person .cw-label { color: var(--accent-text); }
        conversation-widget .cw-turn.cw-persona .cw-label { color: var(--text-secondary); }
        conversation-widget .cw-body {
            flex: 1;
            min-width: 0;
            line-height: 1.65;
            word-wrap: break-word;
            overflow-wrap: anywhere;
            white-space: pre-wrap;
        }
        conversation-widget .cw-turn.cw-person .cw-body { color: var(--accent-text); }
        conversation-widget .cw-turn.cw-persona .cw-body { color: var(--text-body); font-weight: 300; }

        /* Inline meta — time + channel icon at end of message */
        conversation-widget .cw-meta {
            display: inline-flex;
            align-items: center;
            gap: var(--space-xs);
            margin-left: var(--space-sm);
            color: var(--text-dim);
            font-size: var(--text-xs);
            vertical-align: baseline;
            white-space: nowrap;
        }
        conversation-widget .cw-channel {
            display: inline-flex;
            align-items: center;
            color: var(--text-muted);
            cursor: help;
        }
        conversation-widget .cw-channel svg { display: block; }

        /* Inline media */
        conversation-widget .cw-img {
            display: block;
            max-width: 100%;
            max-height: 320px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-subtle);
            background: var(--surface-recessed);
            cursor: zoom-in;
            margin-bottom: var(--space-xs);
            object-fit: contain;
        }
        conversation-widget .cw-img:hover { border-color: var(--border-hover); }

        /* System card — full-width orientation note */
        conversation-widget .cw-system {
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-left: 2px solid var(--accent-border);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-size: var(--text-base);
            line-height: 1.7;
            white-space: pre-wrap;
            margin: var(--space-sm) 0;
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

    setPersona(personaId, name, birthday) {
        if (personaId === this._personaId) return;
        this._personaId = personaId;
        this._personaName = name;
        this._personaBirthday = birthday || null;
        this._lastSpeaker = null;
        this._tail.innerHTML = '';
        this._loadHistory();
    }

    activate() {
        setTimeout(() => this._input.focus(), 100);
    }

    deactivate() {}

    addMessage(role, content, time, channel) {
        if (role === 'system') {
            const card = document.createElement('div');
            card.className = 'cw-system';
            card.textContent = content;
            this._tail.append(card);
            this._lastSpeaker = null;
            return;
        }
        const timeStr = time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const turn = this._buildTurn(role);
        const body = turn.querySelector('.cw-body');
        body.appendChild(document.createTextNode(content));
        body.appendChild(this._buildMeta(timeStr, channel));
        this._tail.append(turn);
        this._lastSpeaker = role;
    }

    addMediaMessage(role, source, caption, time, channel) {
        const timeStr = time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const turn = this._buildTurn(role);
        const body = turn.querySelector('.cw-body');

        const img = document.createElement('img');
        img.className = 'cw-img';
        img.src = source;
        img.alt = caption || 'image';
        img.addEventListener('click', () => window.open(source, '_blank'));
        body.appendChild(img);

        if (caption) body.appendChild(document.createTextNode(caption));
        body.appendChild(this._buildMeta(timeStr, channel));
        this._tail.append(turn);
        this._lastSpeaker = role;
    }

    _buildTurn(role) {
        const turn = document.createElement('div');
        turn.className = `cw-turn cw-${role}`;
        const label = document.createElement('span');
        label.className = 'cw-label';
        label.textContent = role === 'person' ? 'you' : (this._personaName || 'persona');
        const body = document.createElement('span');
        body.className = 'cw-body';
        turn.appendChild(label);
        turn.appendChild(body);
        return turn;
    }

    _buildMeta(timeStr, channel) {
        const meta = document.createElement('span');
        meta.className = 'cw-meta';
        if (channel && CHANNEL_ICONS[channel]) {
            const ch = document.createElement('span');
            ch.className = 'cw-channel';
            ch.title = `sent on ${CHANNEL_LABELS[channel] || channel}`;
            ch.innerHTML = CHANNEL_ICONS[channel](12);
            meta.appendChild(ch);
        }
        if (timeStr) {
            const t = document.createElement('span');
            t.className = 'cw-time';
            t.textContent = timeStr;
            meta.appendChild(t);
        }
        return meta;
    }

    receiveMessage(content, channel) {
        this.addMessage('persona', content, undefined, channel);
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
            if (this._isFirstDay()) {
                this._showWelcome();
            }
            for (const msg of messages) {
                const time = msg.time ? new Date(msg.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null;
                const role = msg.role === 'person' ? 'person' : 'persona';
                const channel = msg.channel?.type || (typeof msg.channel === 'string' ? msg.channel : null) || null;
                if (msg.media && msg.media.source) {
                    const url = this._props.mediaUrl ? this._props.mediaUrl(msg.media.source) : msg.media.source;
                    this.addMediaMessage(role, url, msg.media.caption || msg.content || '', time, channel);
                } else {
                    this.addMessage(role, msg.content, time, channel);
                }
            }
            this._scrollReveal();
        } catch {}
    }

    _scrollReveal(duration = 1400) {
        const tail = this._tail;
        if (!tail) return;
        requestAnimationFrame(() => {
            const target = tail.scrollHeight - tail.clientHeight;
            if (target <= 8) return;
            tail.scrollTop = 0;
            tail._pinned = false;
            let cancelled = false;
            const cancel = () => { cancelled = true; };
            tail.addEventListener('wheel', cancel, { once: true, passive: true });
            tail.addEventListener('touchstart', cancel, { once: true, passive: true });
            tail.addEventListener('mousedown', cancel, { once: true });
            tail.addEventListener('keydown', cancel, { once: true });
            const start = performance.now();
            const step = (now) => {
                if (cancelled) return;
                const t = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - t, 3);
                tail.scrollTop = target * eased;
                if (t < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        });
    }

    _isFirstDay() {
        if (!this._personaBirthday) return false;
        const d = new Date();
        const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        return this._personaBirthday === today;
    }

    _showWelcome() {
        const name = this._personaName || 'your persona';
        const welcome = [
            `Welcome. You're in ${name}'s chat.`,
            ``,
            `Type below to talk; they'll reply here. Click the paperclip to share an image.`,
            ``,
            `The orb behind the conversation is ${name}'s mind — click it to step inside and see what they're holding.`,
            ``,
            `If you set up a Telegram or Discord bot during setup, look for the Pair button at the top-right to finish the connection.`,
            ``,
            `The tabs at the bottom switch between personas you've created.`,
        ].join('\n');
        this.addMessage('system', welcome);
    }
}

customElements.define('conversation-widget', ConversationWidget);
export default ConversationWidget;
