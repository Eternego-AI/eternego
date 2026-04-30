import Element from './element.js';

class InputText extends Element {
    static _styled = false;
    static _css = `
        input-text { display: block; }
        input-text .field {
            display: block;
            font-size: var(--text-sm);
            color: var(--text-secondary);
            margin-bottom: var(--space-xs);
            letter-spacing: 0.5px;
        }
        input-text .input {
            width: 100%;
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: var(--text-base);
            transition: border-color var(--time-quick), background var(--time-quick);
        }
        input-text .input:focus {
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }
        input-text .input::placeholder { color: var(--text-faint); }
        input-text .help, input-text .error {
            margin-top: var(--space-xs);
            font-size: var(--text-xs);
        }
        input-text .help { color: var(--text-muted); }
        input-text .error { color: var(--danger-text); }
        input-text[invalid] .input { border-color: var(--danger-border); }
    `;

    render() {
        this.innerHTML = `
            <div class="field" hidden></div>
            <input class="input" type="text">
            <div class="help" hidden></div>
            <div class="error" hidden></div>
        `;
        const fieldEl = this.querySelector('.field');
        const inputEl = this.querySelector('.input');
        const helpEl = this.querySelector('.help');
        const errorEl = this.querySelector('.error');

        const { label, value, placeholder, help, error, onChange, onSubmit, type, autocomplete } = this._props;

        if (label) { fieldEl.textContent = label; fieldEl.hidden = false; }
        if (type) inputEl.type = type;
        if (autocomplete) inputEl.autocomplete = autocomplete;
        inputEl.value = value || '';
        inputEl.placeholder = placeholder || '';
        if (help) { helpEl.textContent = help; helpEl.hidden = false; }
        if (error) { errorEl.textContent = error; errorEl.hidden = false; }
        this.toggleAttribute('invalid', !!error);

        inputEl.addEventListener('input', () => onChange && onChange(inputEl.value));
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && onSubmit) {
                e.preventDefault();
                onSubmit(inputEl.value);
            }
        });
    }
}

customElements.define('input-text', InputText);
export default InputText;
