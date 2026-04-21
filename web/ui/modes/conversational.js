import Mode from './mode.js';

class ConversationalMode extends Mode {
    static _css = `
        conversational-mode {
            position: fixed;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: stretch;
            padding: var(--space-lg) var(--space-lg) calc(var(--space-lg) + 3em);
            background:
                radial-gradient(ellipse at 70% 30%, rgba(140,160,255,0.04) 0%, transparent 55%),
                radial-gradient(ellipse at 20% 70%, rgba(140,160,255,0.02) 0%, transparent 55%),
                var(--bg);
        }
    `;

    build() {
        this.constructor._injectStyles();
    }

    bind(speaker) {
        this.innerHTML = '';
        this._stream = document.createElement('message-stream');
        this._stream.init({ speaker });
        this.appendChild(this._stream);
    }

    unbind() {
        this.innerHTML = '';
        this._stream = null;
    }

    activate() {}
    deactivate() { this.unbind(); }
}

customElements.define('conversational-mode', ConversationalMode);
export default ConversationalMode;
