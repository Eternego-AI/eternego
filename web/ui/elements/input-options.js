import Input from './input.js';

class InputOptions extends Input {
    static _css = `
        input-options { display: flex; flex-direction: column; gap: var(--space-md); width: 100%; }
        input-options .io-list { display: flex; flex-wrap: wrap; gap: var(--space-md); }
        input-options .io-opt {
            flex: 1 1 140px;
            padding: var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: var(--text-base);
            cursor: pointer;
            text-align: center;
            transition: border-color 0.2s, background 0.2s, color 0.2s, transform 0.15s;
        }
        input-options .io-opt:hover {
            border-color: var(--border-hover);
            background: var(--surface-hover);
            color: var(--text-body);
        }
        input-options .io-opt.selected {
            border-color: var(--accent-border);
            background: var(--accent-bg);
            color: var(--accent-text);
        }
        input-options .io-opt .io-hint {
            display: block;
            margin-top: var(--space-xs);
            font-size: var(--text-sm);
            color: var(--text-muted);
        }
        input-options .io-footer { display: flex; justify-content: flex-end; gap: var(--space-sm); }
        input-options .io-btn {
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
        input-options .io-btn:hover { border-color: var(--border-hover); color: #fff; }
        input-options .io-btn.primary { background: var(--accent-bg); border-color: var(--accent-border); color: var(--accent-text); }
        input-options .io-btn.primary:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
        input-options .io-btn:disabled { opacity: 0.3; cursor: not-allowed; }
    `;

    render() {
        this.constructor._injectStyles();
        const p = this._props || {};
        const options = p.options || [];
        const confirm = !!p.confirm;
        const canSkip = !!p.canSkip;
        let selectedId = p.value ?? null;

        const optsHtml = options.map(o => {
            const hint = o.hint ? `<span class="io-hint">${this._esc(o.hint)}</span>` : '';
            const sel = selectedId === o.id ? ' selected' : '';
            return `<div class="io-opt${sel}" data-id="${this._esc(String(o.id))}">${this._esc(o.label)}${hint}</div>`;
        }).join('');

        const footer = (confirm || canSkip) ? `
            <div class="io-footer">
                ${canSkip ? `<button type="button" class="io-btn" data-skip>${this._esc(p.skipLabel || 'Skip')}</button>` : ''}
                ${confirm ? `<button type="button" class="io-btn primary" data-confirm>${this._esc(p.submitLabel || 'Next')}</button>` : ''}
            </div>
        ` : '';

        this.innerHTML = `<div class="io-list">${optsHtml}</div>${footer}`;

        this.querySelectorAll('.io-opt').forEach(el => {
            el.addEventListener('click', () => {
                if (!confirm) {
                    this.submit(el.dataset.id);
                    return;
                }
                this.querySelectorAll('.io-opt').forEach(o => o.classList.remove('selected'));
                el.classList.add('selected');
                selectedId = el.dataset.id;
            });
        });

        const confirmBtn = this.querySelector('[data-confirm]');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (!selectedId) return;
                this.submit(selectedId);
            });
        }
        const skipBtn = this.querySelector('[data-skip]');
        if (skipBtn) {
            skipBtn.addEventListener('click', () => this.submit(null));
        }
    }
}

customElements.define('input-options', InputOptions);
export default InputOptions;
