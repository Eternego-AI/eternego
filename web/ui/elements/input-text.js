import Input from './input.js';

class InputText extends Input {
    static _css = `
        input-text { display: flex; flex-direction: column; gap: var(--space-sm); width: 100%; }
        input-text .it-row { display: flex; gap: var(--space-sm); align-items: stretch; }
        input-text .it-field {
            flex: 1;
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            color: var(--text-body);
            font-family: var(--font);
            font-size: var(--text-base);
            outline: none;
            transition: border-color 0.25s var(--ease);
            resize: none;
        }
        input-text .it-field:focus { border-color: var(--accent-border); }
        input-text .it-field::placeholder { color: var(--text-dim); }
        input-text .it-send {
            padding: 0 var(--space-lg);
            background: var(--accent-bg);
            border: 1px solid var(--accent-border);
            border-radius: var(--radius-lg);
            color: var(--accent-text);
            font-family: var(--font);
            font-size: var(--text-base);
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s, color 0.2s;
        }
        input-text .it-send:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
        input-text .it-send:disabled { opacity: 0.3; cursor: not-allowed; }
    `;

    render() {
        this.constructor._injectStyles();
        const p = this._props || {};
        const multiline = !!p.multiline;
        const tag = multiline ? 'textarea' : 'input';
        const type = p.password ? 'password' : 'text';
        const rows = multiline ? (p.rows || 3) : '';
        this.innerHTML = `
            <div class="it-row">
                <${tag} class="it-field" ${multiline ? `rows="${rows}"` : `type="${type}"`} placeholder="${this._esc(p.placeholder || '')}">${this._esc(p.value || '')}</${tag}>
                <button class="it-send" type="button">${this._esc(p.submitLabel || 'Send')}</button>
            </div>
        `;
        if (!multiline) {
            const field = this.querySelector('.it-field');
            field.value = p.value || '';
        }
        this._field = this.querySelector('.it-field');
        this._btn = this.querySelector('.it-send');
        const send = () => {
            const v = (this._field.value || '').trim();
            if (!v && !p.allowEmpty) return;
            this.submit(v);
        };
        this._btn.addEventListener('click', send);
        this._field.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (!multiline || !e.shiftKey)) {
                e.preventDefault();
                send();
            }
        });
    }

    focusFirst() {
        if (this._field) setTimeout(() => this._field.focus(), 40);
    }
}

customElements.define('input-text', InputText);
export default InputText;
