import Element from './element.js';

class ActionButton extends Element {
    static _css = `
        action-button { display: inline-flex; }
        action-button .ab {
            padding: var(--space-sm) var(--space-xl);
            background: var(--surface-hover);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: var(--text-sm);
            cursor: pointer;
            transition: border-color 0.2s, color 0.2s, background 0.2s;
        }
        action-button .ab:hover { border-color: var(--border-hover); color: #fff; }
        action-button .ab-primary { background: var(--accent-bg); border-color: var(--accent-border); color: var(--accent-text); }
        action-button .ab-primary:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
        action-button .ab:disabled { opacity: 0.3; cursor: not-allowed; }
    `;

    // init({ label, type, onClick, disabled })
    render() {
        this.constructor._injectStyles();
        const { label, type, disabled, onClick } = this._props;
        const btn = document.createElement('button');
        btn.className = 'ab' + (type && type !== 'default' ? ` ab-${type}` : '');
        btn.textContent = label;
        if (disabled) btn.disabled = true;
        if (onClick) btn.addEventListener('click', onClick);
        this.innerHTML = '';
        this.appendChild(btn);
        this._btn = btn;
    }

    set disabled(v) { if (this._btn) this._btn.disabled = v; }
}

customElements.define('action-button', ActionButton);
export default ActionButton;
