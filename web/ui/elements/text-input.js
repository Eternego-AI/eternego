import Element from './element.js';

class TextInput extends Element {
    static _css = `
        text-input { display: flex; flex-direction: column; gap: var(--space-sm); }
        text-input .ti-label { font-size: var(--text-base); font-weight: 400; color: var(--text-secondary); }
        text-input .ti-hint { font-size: var(--text-sm); font-weight: 300; color: var(--text-dim); line-height: 1.6; }
        text-input .ti-hint strong { color: var(--text-muted); font-weight: 500; }
        text-input .ti-hint code { background: var(--surface-hover); padding: 0.1em 0.35em; border-radius: var(--radius-sm); font-size: var(--text-xs); }
        text-input .ti-field {
            width: 100%; padding: var(--space-md) var(--space-lg);
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            color: var(--text-body);
            font-family: var(--font); font-size: var(--text-base);
            outline: none; transition: border-color 0.3s var(--ease);
        }
        text-input .ti-field::placeholder { color: var(--text-faint); }
        text-input .ti-field:focus { border-color: var(--accent-border); }
        text-input textarea.ti-field { resize: vertical; min-height: 4em; line-height: 1.6; }
    `;

    render() {
        this.constructor._injectStyles();
        const { label, hint, placeholder, value, type, onChange, onSubmit } = this._props;
        this.innerHTML = '';
        if (label) { const l = document.createElement('label'); l.className = 'ti-label'; l.textContent = label; this.appendChild(l); }
        if (hint) { const p = document.createElement('p'); p.className = 'ti-hint'; p.innerHTML = hint; this.appendChild(p); }
        const isTA = type === 'textarea';
        const f = document.createElement(isTA ? 'textarea' : 'input');
        f.className = 'ti-field';
        if (!isTA) f.type = type || 'text';
        f.placeholder = placeholder || '';
        f.value = value || '';
        if (onChange) f.addEventListener('input', () => onChange(f.value));
        if (onSubmit) f.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !isTA) onSubmit(f.value.trim()); });
        this.appendChild(f);
        this._field = f;
    }

    get value() { return this._field?.value.trim() || ''; }
    set value(v) { if (this._field) this._field.value = v; }
    focus() { this._field?.focus(); }
}

customElements.define('text-input', TextInput);
export default TextInput;
