import Widget from './widget.js';

class FeedWidget extends Widget {
    static widgetId = 'feed';
    static columns = 2;
    static rows = 2;

    // init({ onFeed(file, source) → Promise<{ success, message }> })
    build() {
        this._data = { file: null, source: '' };

        const card = document.createElement('card-layout');
        card.init({ title: 'Feed' });

        const step = document.createElement('step-layout');
        step.init({ steps: ['file'] });

        this._panels = {};
        for (const id of ['file', 'loading', 'result']) {
            const panel = document.createElement('step-panel');
            panel.init({ id });
            step.addPanel(panel);
            this._panels[id] = panel;
        }

        card.body.appendChild(step);
        this.appendChild(card);
        this._card = card;
        this._step = step;

        this._renderFile();
        this._panels.loading.innerHTML = '<div class="spinner"></div>';
        step.go('file');
    }

    reset() {
        this._data = { file: null, source: '' };
        this._renderFile();
        this._step.go('file');
    }

    setFocused(focused) {
        super.setFocused(focused);
        this._card.setFocused(focused);
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    _renderFile() {
        const s = this._panels.file;

        const sources = [
            { id: 'claude', name: 'Claude' },
            { id: 'chatgpt', name: 'ChatGPT' },
            { id: 'grok', name: 'Grok' },
        ];

        const options = sources.map(src => {
            const selected = this._data.source === src.id ? 'selected' : '';
            return `<div class="wizard-option ${selected}" data-source="${src.id}">
                <span class="wizard-option-name">${src.name}</span>
            </div>`;
        }).join('');

        s.innerHTML = `
            <label class="wizard-label">Source</label>
            <div class="wizard-options">${options}</div>
            <label class="wizard-label">Exported conversations</label>
            <div class="migrate-dropzone">
                <input type="file" accept=".json" class="migrate-file-input">
                <span class="migrate-dropzone-text">${this._data.file ? this._esc(this._data.file.name) : 'Choose or drop a JSON export'}</span>
            </div>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-feed" ${!this._data.file || !this._data.source ? 'disabled' : ''}>Feed</button>
            </div>
        `;

        const feedBtn = s.querySelector('#wz-feed');
        s.querySelectorAll('.wizard-option').forEach(el => {
            el.addEventListener('click', () => {
                this._data.source = el.dataset.source;
                s.querySelectorAll('.wizard-option').forEach(o => o.classList.remove('selected'));
                el.classList.add('selected');
                if (this._data.file) feedBtn.removeAttribute('disabled');
            });
        });

        const fileZone = s.querySelector('.migrate-dropzone');
        const fileInput = s.querySelector('.migrate-file-input');
        const fileText = s.querySelector('.migrate-dropzone-text');

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                this._data.file = fileInput.files[0];
                fileText.textContent = this._data.file.name;
                if (this._data.source) feedBtn.removeAttribute('disabled');
            }
        });
        fileZone.addEventListener('dragover', (e) => { e.preventDefault(); fileZone.classList.add('dragover'); });
        fileZone.addEventListener('dragleave', () => fileZone.classList.remove('dragover'));
        fileZone.addEventListener('drop', (e) => {
            e.preventDefault();
            fileZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this._data.file = e.dataTransfer.files[0];
                fileText.textContent = this._data.file.name;
                fileInput.files = e.dataTransfer.files;
                if (this._data.source) feedBtn.removeAttribute('disabled');
            }
        });

        feedBtn.addEventListener('click', () => {
            if (this._data.file && this._data.source) this._submit();
        });
    }

    async _submit() {
        this._step.go('loading');
        try {
            const result = await this._props.onFeed(this._data.file, this._data.source);
            if (result.success) {
                this._showResult(result.message || 'Persona fed successfully');
            } else {
                this._showError(result.message || 'Feeding failed');
            }
        } catch {
            this._showError('Network error');
        }
    }

    _showError(msg) {
        this._step.go('file');
        const s = this._panels.file;
        const existing = s.querySelector('.wizard-error');
        if (existing) existing.remove();
        const el = document.createElement('p');
        el.className = 'wizard-error';
        el.textContent = msg;
        s.prepend(el);
    }

    _showResult(msg) {
        const s = this._panels.result;
        s.innerHTML = `
            <label class="wizard-label">Done</label>
            <p class="wizard-hint">${this._esc(msg)}</p>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-done">Feed More</button>
            </div>
        `;
        s.querySelector('#wz-done').addEventListener('click', () => this.reset());
        this._step.go('result');
    }
}

customElements.define('feed-widget', FeedWidget);
export default FeedWidget;
