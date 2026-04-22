import Element from './element.js';
import { send, hash, globe } from '../icons.js';

const CHANNEL_ICONS = {
    telegram: send,
    discord: hash,
    web: globe,
};

class RoleMessage extends Element {
    static _css = `
        role-message {
            display: block;
            font-size: var(--text-base);
            line-height: 1.65;
            word-wrap: break-word;
            white-space: pre-wrap;
            padding: var(--space-xs) 0;
            max-width: 70%;
            animation: rm-arrive 0.3s var(--ease);
        }
        @keyframes rm-arrive {
            from { opacity: 0; transform: translateY(4px); }
        }
        role-message .rm-meta {
            display: inline-flex;
            align-items: center;
            gap: var(--space-xs);
            margin-left: var(--space-sm);
            color: var(--text-dim);
            white-space: nowrap;
            vertical-align: baseline;
        }
        role-message .rm-channel {
            display: inline-flex;
            align-items: center;
            color: var(--text-muted);
        }
        role-message .rm-channel svg { display: block; }
        role-message .rm-time {
            font-size: var(--text-xs);
        }

        role-message.rm-person { color: var(--accent-text); font-weight: 400; }
        role-message.rm-persona { color: var(--text-body); font-weight: 300; }
        role-message.rm-system {
            color: var(--text-secondary);
            font-size: var(--text-base);
            max-width: 90%;
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-left: 2px solid var(--accent-border);
            border-radius: var(--radius-md);
        }
    `;

    // init({ role, text, time, channel })
    render() {
        this.constructor._injectStyles();
        this.className = `rm-${this._props.role}`;
        this.textContent = this._props.text;

        const channelType = this._props.channel;
        const hasTime = !!this._props.time;
        const hasChannel = !!channelType && CHANNEL_ICONS[channelType];
        if (!hasTime && !hasChannel) return;

        const meta = document.createElement('span');
        meta.className = 'rm-meta';

        if (hasChannel) {
            const ch = document.createElement('span');
            ch.className = 'rm-channel';
            ch.title = channelType;
            ch.innerHTML = CHANNEL_ICONS[channelType](12);
            meta.appendChild(ch);
        }

        if (hasTime) {
            const time = document.createElement('span');
            time.className = 'rm-time';
            time.textContent = this._props.time;
            meta.appendChild(time);
        }

        this.appendChild(meta);
    }
}

customElements.define('role-message', RoleMessage);
export default RoleMessage;
