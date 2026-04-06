import Element from './element.js';

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
        role-message .rm-time {
            font-size: var(--text-xs);
            color: var(--text-dim);
            margin-left: var(--space-sm);
            white-space: nowrap;
        }

        role-message.rm-person { color: var(--accent-text); font-weight: 400; }
        role-message.rm-persona { color: var(--text-body); font-weight: 300; }
        role-message.rm-system { color: var(--text-muted); font-style: italic; font-size: var(--text-sm); max-width: 90%; }
    `;

    // init({ role, text, time })
    render() {
        this.constructor._injectStyles();
        this.className = `rm-${this._props.role}`;
        this.textContent = this._props.text;

        if (this._props.time) {
            const time = document.createElement('span');
            time.className = 'rm-time';
            time.textContent = this._props.time;
            this.appendChild(time);
        }
    }
}

customElements.define('role-message', RoleMessage);
export default RoleMessage;
