import Input from './input.js';

class InputComposite extends Input {
    static _css = `
        input-composite { display: flex; flex-direction: column; gap: var(--space-md); width: 100%; }
        input-composite .ic-field {
            display: flex;
            flex-direction: column;
            gap: var(--space-xs);
        }
        input-composite .ic-label {
            font-size: var(--text-sm);
            color: var(--text-secondary);
            padding-left: var(--space-sm);
        }
        input-composite .ic-row {
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            color: var(--text-body);
            font-family: var(--font);
            font-size: var(--text-base);
            outline: none;
            transition: border-color 0.25s var(--ease);
            width: 100%;
        }
        input-composite .ic-row:focus { border-color: var(--accent-border); }
        input-composite .ic-row::placeholder { color: var(--text-dim); }
        input-composite .ic-footer { display: flex; justify-content: flex-end; gap: var(--space-sm); padding-top: var(--space-xs); }
        input-composite .ic-btn {
            padding: var(--space-sm) var(--space-lg);
            background: var(--surface-hover);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: var(--text-base);
            cursor: pointer;
            transition: border-color 0.2s, color 0.2s, background 0.2s;
        }
        input-composite .ic-btn:hover { border-color: var(--border-hover); color: #fff; }
        input-composite .ic-btn.primary { background: var(--accent-bg); border-color: var(--accent-border); color: var(--accent-text); }
        input-composite .ic-btn.primary:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
    `;

    render() {
        this.constructor._injectStyles();
        const p = this._props || {};
        const fields = p.fields || [];

        const rows = fields.map((f) => {
            const type = f.password ? 'password' : 'text';
            const label = f.label ? `<span class="ic-label">${this._esc(f.label)}</span>` : '';
            return `
                <div class="ic-field" data-name="${this._esc(f.name)}">
                    ${label}
                    <input class="ic-row" type="${type}" placeholder="${this._esc(f.placeholder || '')}" value="${this._esc(f.value || '')}">
                </div>
            `;
        }).join('');

        this.innerHTML = `
            ${rows}
            <div class="ic-footer">
                ${p.canSkip ? `<button type="button" class="ic-btn" data-skip>${this._esc(p.skipLabel || 'Skip')}</button>` : ''}
                <button type="button" class="ic-btn primary" data-submit>${this._esc(p.submitLabel || 'Next')}</button>
            </div>
        `;

        const inputs = {};
        this.querySelectorAll('.ic-field').forEach((f) => {
            inputs[f.dataset.name] = f.querySelector('.ic-row');
        });
        this._inputs = inputs;
        this._fields = fields;

        const submit = () => {
            const out = {};
            for (const f of fields) {
                const v = (inputs[f.name].value || '').trim();
                if (!v && !f.optional) {
                    inputs[f.name].focus();
                    return;
                }
                out[f.name] = v;
            }
            this.submit(out);
        };
        this.querySelector('[data-submit]').addEventListener('click', submit);

        const skipBtn = this.querySelector('[data-skip]');
        if (skipBtn) skipBtn.addEventListener('click', () => this.submit(null));

        for (const name in inputs) {
            inputs[name].addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); submit(); }
            });
        }
    }

    focusFirst() {
        const first = this._fields && this._fields[0];
        if (first && this._inputs[first.name]) {
            setTimeout(() => this._inputs[first.name].focus(), 40);
        }
    }
}

customElements.define('input-composite', InputComposite);
export default InputComposite;
