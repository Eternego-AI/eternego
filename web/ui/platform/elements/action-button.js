import Element from './element.js';

class ActionButton extends Element {
    static _styled = false;
    static _css = `
        action-button { display: inline-block; }
        action-button button {
            padding: var(--space-md) var(--space-xl);
            border-radius: var(--radius-md);
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: all var(--time-quick);
            border: 1px solid transparent;
        }
        action-button button:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }
        action-button[variant=primary] button {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        action-button[variant=primary] button:hover:not(:disabled) {
            background: var(--accent);
            color: var(--bg);
        }
        action-button[variant=secondary] button {
            background: var(--surface-recessed);
            border-color: var(--border-subtle);
            color: var(--text-primary);
        }
        action-button[variant=secondary] button:hover:not(:disabled) {
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }
        action-button[variant=ghost] button {
            background: transparent;
            border-color: transparent;
            color: var(--text-secondary);
        }
        action-button[variant=ghost] button:hover:not(:disabled) {
            color: var(--text-primary);
            background: var(--surface-hover);
        }
        action-button[variant=danger] button {
            background: var(--danger-bg);
            border-color: var(--danger-border);
            color: var(--danger-text);
        }
        action-button[variant=danger] button:hover:not(:disabled) {
            background: var(--danger);
            color: var(--bg);
        }
        action-button[variant=warm] button {
            background: var(--warm-bg);
            border-color: var(--warm-border);
            color: var(--warm-text);
        }
        action-button[variant=warm] button:hover:not(:disabled) {
            background: var(--warm);
            color: var(--bg);
        }
    `;

    render() {
        this.innerHTML = `<button type="button"></button>`;
        const btnEl = this.querySelector('button');

        const { label, variant = 'secondary', disabled, onClick } = this._props;

        btnEl.textContent = label || '';
        btnEl.disabled = !!disabled;
        this.setAttribute('variant', variant);

        btnEl.addEventListener('click', (e) => {
            if (disabled) return;
            onClick && onClick(e);
        });
    }
}

customElements.define('action-button', ActionButton);
export default ActionButton;
