import Element from './element.js';

class InputOptions extends Element {
    static _styled = false;
    static _css = `
        input-options { display: block; }
        input-options .field {
            display: block;
            font-size: var(--text-sm);
            color: var(--text-secondary);
            margin-bottom: var(--space-sm);
            letter-spacing: 0.5px;
        }
        input-options .group {
            display: flex;
            flex-wrap: wrap;
            gap: var(--space-sm);
        }
        input-options .chip {
            padding: var(--space-sm) var(--space-lg);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: all var(--time-quick);
        }
        input-options .chip:hover {
            border-color: var(--border-hover);
            color: var(--text-primary);
        }
        input-options .chip.active {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        input-options .help, input-options .error {
            margin-top: var(--space-xs);
            font-size: var(--text-xs);
        }
        input-options .help { color: var(--text-muted); }
        input-options .error { color: var(--danger-text); }
    `;

    render() {
        this.innerHTML = `
            <div class="field" hidden></div>
            <div class="group"></div>
            <div class="help" hidden></div>
            <div class="error" hidden></div>
        `;
        const fieldEl = this.querySelector('.field');
        const groupEl = this.querySelector('.group');
        const helpEl = this.querySelector('.help');
        const errorEl = this.querySelector('.error');

        const { label, value, options = [], help, error, onChange } = this._props;

        if (label) { fieldEl.textContent = label; fieldEl.hidden = false; }
        if (help) { helpEl.textContent = help; helpEl.hidden = false; }
        if (error) { errorEl.textContent = error; errorEl.hidden = false; }

        for (const opt of options) {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'chip' + (opt.value === value ? ' active' : '');
            chip.textContent = opt.label;
            chip.addEventListener('click', () => {
                groupEl.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                onChange && onChange(opt.value);
            });
            groupEl.appendChild(chip);
        }
    }
}

customElements.define('input-options', InputOptions);
export default InputOptions;
