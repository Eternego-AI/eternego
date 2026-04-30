import Element from './element.js';

class InputDropzone extends Element {
    static _styled = false;
    static _css = `
        input-dropzone { display: block; }
        input-dropzone .field {
            display: block;
            font-size: var(--text-sm);
            color: var(--text-secondary);
            margin-bottom: var(--space-xs);
            letter-spacing: 0.5px;
        }
        input-dropzone .zone {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            padding: var(--space-2xl) var(--space-xl);
            background: var(--surface-recessed);
            border: 1px dashed var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            cursor: pointer;
            transition: border-color var(--time-quick), background var(--time-quick);
        }
        input-dropzone .zone:hover,
        input-dropzone .zone.over {
            border-color: var(--accent-border);
            background: var(--accent-bg);
            color: var(--accent-text);
        }
        input-dropzone .picked {
            color: var(--text-primary);
        }
        input-dropzone .filename {
            color: var(--warm-text);
            font-size: var(--text-base);
        }
        input-dropzone input[type=file] { display: none; }
        input-dropzone .help, input-dropzone .error {
            margin-top: var(--space-xs);
            font-size: var(--text-xs);
        }
        input-dropzone .help { color: var(--text-muted); }
        input-dropzone .error { color: var(--danger-text); }
    `;

    render() {
        this.innerHTML = `
            <div class="field" hidden></div>
            <label class="zone">
                <div class="prompt"></div>
                <div class="filename" hidden></div>
                <input type="file">
            </label>
            <div class="help" hidden></div>
            <div class="error" hidden></div>
        `;
        const fieldEl = this.querySelector('.field');
        const zoneEl = this.querySelector('.zone');
        const promptEl = this.querySelector('.prompt');
        const filenameEl = this.querySelector('.filename');
        const fileEl = this.querySelector('input[type=file]');
        const helpEl = this.querySelector('.help');
        const errorEl = this.querySelector('.error');

        const { label, prompt = 'Drop a file or click to choose', accept, help, error, onChange } = this._props;

        if (label) { fieldEl.textContent = label; fieldEl.hidden = false; }
        promptEl.textContent = prompt;
        if (accept) fileEl.accept = accept;
        if (help) { helpEl.textContent = help; helpEl.hidden = false; }
        if (error) { errorEl.textContent = error; errorEl.hidden = false; }

        const accept_file = (file) => {
            if (!file) return;
            promptEl.hidden = true;
            filenameEl.textContent = file.name;
            filenameEl.hidden = false;
            zoneEl.classList.add('picked');
            onChange && onChange(file);
        };

        fileEl.addEventListener('change', () => accept_file(fileEl.files[0]));
        zoneEl.addEventListener('dragover', (e) => { e.preventDefault(); zoneEl.classList.add('over'); });
        zoneEl.addEventListener('dragleave', () => zoneEl.classList.remove('over'));
        zoneEl.addEventListener('drop', (e) => {
            e.preventDefault();
            zoneEl.classList.remove('over');
            accept_file(e.dataTransfer.files[0]);
        });
    }
}

customElements.define('input-dropzone', InputDropzone);
export default InputDropzone;
