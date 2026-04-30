import Element from './element.js';

class InputTextarea extends Element {
    static _styled = false;
    static _css = `
        input-textarea { display: block; }
        input-textarea .field {
            display: block;
            font-size: var(--text-sm);
            color: var(--text-secondary);
            margin-bottom: var(--space-xs);
            letter-spacing: 0.5px;
        }
        input-textarea .input {
            width: 100%;
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: var(--text-base);
            line-height: 1.55;
            resize: vertical;
            transition: border-color var(--time-quick), background var(--time-quick);
        }
        input-textarea .input:focus {
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }
        input-textarea .input::placeholder { color: var(--text-faint); }
        input-textarea .help, input-textarea .error {
            margin-top: var(--space-xs);
            font-size: var(--text-xs);
        }
        input-textarea .help { color: var(--text-muted); }
        input-textarea .error { color: var(--danger-text); }
        input-textarea[invalid] .input { border-color: var(--danger-border); }
    `;

    render() {
        this.innerHTML = `
            <div class="field" hidden></div>
            <textarea class="input"></textarea>
            <div class="help" hidden></div>
            <div class="error" hidden></div>
        `;
        const fieldEl = this.querySelector('.field');
        const inputEl = this.querySelector('.input');
        const helpEl = this.querySelector('.help');
        const errorEl = this.querySelector('.error');

        const { label, value, placeholder, help, error, onChange, rows = 4 } = this._props;

        if (label) { fieldEl.textContent = label; fieldEl.hidden = false; }
        inputEl.rows = rows;
        inputEl.value = value || '';
        inputEl.placeholder = placeholder || '';
        if (help) { helpEl.textContent = help; helpEl.hidden = false; }
        if (error) { errorEl.textContent = error; errorEl.hidden = false; }
        this.toggleAttribute('invalid', !!error);

        inputEl.addEventListener('input', () => onChange && onChange(inputEl.value));
    }
}

customElements.define('input-textarea', InputTextarea);
export default InputTextarea;
