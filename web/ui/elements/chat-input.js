/* <chat-input placeholder="..."> — text + image composer.
   Emits 'send' with detail = { text, file }. */

class ChatInput extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._file = null;
        this.innerHTML = `
            <div class="el-pending" hidden>
                <img alt="">
                <span class="el-pending-name"></span>
                <button class="el-pending-clear" type="button" title="Clear">×</button>
            </div>
            <div class="el-row">
                <textarea class="el-input" rows="1" placeholder="${this.getAttribute('placeholder') || 'Say something to her…'}"></textarea>
                <button class="el-attach" type="button" title="Attach image">+</button>
                <input type="file" accept="image/*">
                <button class="el-send" type="button">SEND</button>
            </div>
        `;
        this._input = this.querySelector('.el-input');
        this._send = this.querySelector('.el-send');
        this._attach = this.querySelector('.el-attach');
        this._file_input = this.querySelector('input[type="file"]');
        this._pending = this.querySelector('.el-pending');
        this._pending_img = this._pending.querySelector('img');
        this._pending_name = this._pending.querySelector('.el-pending-name');
        this._pending_clear = this._pending.querySelector('.el-pending-clear');

        const sync = () => {
            this._input.style.height = 'auto';
            this._input.style.height = Math.min(this._input.scrollHeight, 200) + 'px';
            this._send.disabled = !this._input.value.trim() && !this._file;
        };
        const emit = () => {
            const text = this._input.value.trim();
            const file = this._file;
            if (!text && !file) return;
            this.dispatchEvent(new CustomEvent('send', { detail: { text, file } }));
            this._input.value = '';
            this.clearFile();
            sync();
        };

        this._input.addEventListener('input', sync);
        this._input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); emit(); }
        });
        this._send.addEventListener('click', emit);
        this._attach.addEventListener('click', () => this._file_input.click());
        this._file_input.addEventListener('change', () => {
            if (this._file_input.files[0]) this.setFile(this._file_input.files[0]);
        });
        this._pending_clear.addEventListener('click', () => this.clearFile());
        sync();
    }

    setFile(file) {
        this._file = file;
        this._pending_img.src = URL.createObjectURL(file);
        this._pending_name.textContent = file.name;
        this._pending.hidden = false;
        this._send.disabled = false;
    }
    clearFile() {
        if (this._file && this._pending_img.src) URL.revokeObjectURL(this._pending_img.src);
        this._file = null;
        this._file_input.value = '';
        this._pending.hidden = true;
        this._send.disabled = !this._input.value.trim();
    }
    focus() { this._input?.focus(); }
}
customElements.define('chat-input', ChatInput);
