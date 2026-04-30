import Layout from './layout.js';

class TextComposer extends Layout {
    static _styled = false;
    static _css = `
        text-composer {
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border-top: 1px solid var(--border-subtle);
        }
        text-composer .pending {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            background: var(--surface);
            border-radius: var(--radius-md);
            font-size: var(--text-sm);
            color: var(--text-muted);
        }
        text-composer .pending .filename { color: var(--warm-text); flex: 1; }
        text-composer .pending .clear {
            color: var(--text-dim);
            font-size: var(--text-base);
            padding: 2px 8px;
        }
        text-composer .pending .clear:hover { color: var(--danger-text); }
        text-composer .row {
            display: flex;
            gap: var(--space-sm);
            align-items: flex-end;
        }
        text-composer .input {
            flex: 1;
            padding: var(--space-sm) var(--space-md);
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: var(--text-base);
            line-height: 1.5;
            resize: none;
            min-height: 38px;
            max-height: 200px;
            transition: border-color var(--time-quick);
        }
        text-composer .input:focus { border-color: var(--border-hover); }
        text-composer .input::placeholder { color: var(--text-faint); }
        text-composer .icon {
            width: 38px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: transparent;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            cursor: pointer;
            font-size: var(--text-md);
            transition: all var(--time-quick);
        }
        text-composer .icon:hover {
            border-color: var(--border-hover);
            color: var(--text-primary);
        }
        text-composer .icon.send {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        text-composer .icon.send:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }
        text-composer input[type=file] { display: none; }
    `;

    arrange() {
        const { text = '', pending, placeholder = '', onTextChange, onPickFile, onClearFile, onSend } = this._props;
        this.innerHTML = `
            <div class="pending" hidden>
                <span class="filename"></span>
                <button class="clear" type="button">×</button>
            </div>
            <div class="row">
                <textarea class="input" rows="1"></textarea>
                <button class="icon attach" type="button" title="Attach image">+</button>
                <input type="file" accept="image/*">
                <button class="icon send" type="button" title="Send">↑</button>
            </div>
        `;

        const pendingEl = this.querySelector('.pending');
        const filenameEl = this.querySelector('.filename');
        const clearEl = this.querySelector('.clear');
        const inputEl = this.querySelector('.input');
        const attachEl = this.querySelector('.attach');
        const fileEl = this.querySelector('input[type=file]');
        const sendEl = this.querySelector('.send');

        if (pending) {
            pendingEl.hidden = false;
            filenameEl.textContent = pending.name || 'image';
        }

        inputEl.value = text;
        inputEl.placeholder = placeholder;
        requestAnimationFrame(() => {
            inputEl.style.height = 'auto';
            inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
        });

        sendEl.disabled = !text.trim() && !pending;

        clearEl.addEventListener('click', () => onClearFile && onClearFile());
        inputEl.addEventListener('input', () => {
            inputEl.style.height = 'auto';
            inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
            sendEl.disabled = !inputEl.value.trim() && !pending;
            onTextChange && onTextChange(inputEl.value);
        });
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (inputEl.value.trim() || pending) {
                    onSend && onSend({ text: inputEl.value, file: pending });
                }
            }
        });
        attachEl.addEventListener('click', () => fileEl.click());
        fileEl.addEventListener('change', () => {
            if (fileEl.files[0]) onPickFile && onPickFile(fileEl.files[0]);
        });
        sendEl.addEventListener('click', () => {
            if (inputEl.value.trim() || pending) {
                onSend && onSend({ text: inputEl.value, file: pending });
            }
        });
    }
}

customElements.define('text-composer', TextComposer);
export default TextComposer;
