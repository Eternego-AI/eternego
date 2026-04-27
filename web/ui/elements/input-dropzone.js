import Input from './input.js';

class InputDropzone extends Input {
    static _css = `
        input-dropzone { display: flex; flex-direction: column; gap: var(--space-md); width: 100%; }
        input-dropzone .id-zone {
            position: relative;
            padding: var(--space-xl);
            background: var(--surface-recessed);
            border: 1.5px dashed var(--glass-border);
            border-radius: var(--radius-lg);
            text-align: center;
            cursor: pointer;
            transition: border-color 0.25s, background 0.25s, color 0.25s;
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: var(--text-base);
        }
        input-dropzone .id-zone:hover, input-dropzone .id-zone.dragover {
            border-color: var(--accent-border);
            background: var(--accent-bg);
            color: var(--accent-text);
        }
        input-dropzone .id-file {
            position: absolute;
            inset: 0;
            opacity: 0;
            cursor: pointer;
        }
        input-dropzone .id-footer { display: flex; justify-content: flex-end; gap: var(--space-sm); }
        input-dropzone .id-btn {
            padding: var(--space-sm) var(--space-lg);
            background: var(--accent-bg);
            border: 1px solid var(--accent-border);
            border-radius: var(--radius-md);
            color: var(--accent-text);
            font-family: var(--font);
            font-size: var(--text-base);
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s, color 0.2s;
        }
        input-dropzone .id-btn:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
        input-dropzone .id-btn:disabled { opacity: 0.3; cursor: not-allowed; }
    `;

    render() {
        this.constructor._injectStyles();
        const p = this._props || {};
        this._picked = null;
        this.innerHTML = `
            <div class="id-zone">
                <input class="id-file" type="file" ${p.accept ? `accept="${this._esc(p.accept)}"` : ''}>
                <span class="id-label">${this._esc(p.label || 'Choose a file or drop it here')}</span>
            </div>
            <div class="id-footer">
                <button type="button" class="id-btn" disabled>${this._esc(p.submitLabel || 'Upload')}</button>
            </div>
        `;
        const zone = this.querySelector('.id-zone');
        const file = this.querySelector('.id-file');
        const label = this.querySelector('.id-label');
        const btn = this.querySelector('.id-btn');

        const setFile = (f) => {
            this._picked = f;
            label.textContent = f ? f.name : (p.label || 'Choose a file or drop it here');
            btn.disabled = !f;
        };

        file.addEventListener('change', () => {
            if (file.files && file.files.length) setFile(file.files[0]);
        });
        zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
        });
        btn.addEventListener('click', () => {
            if (!this._picked) return;
            this.submit(this._picked);
        });
    }
}

customElements.define('input-dropzone', InputDropzone);
export default InputDropzone;
