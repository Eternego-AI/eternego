import Widget from './widget.js';

class MigrateWidget extends Widget {
    static columns = 3;
    static rows = 2;

    // init({ models, onMigrated })
    build() {
        this.setAttribute('widget', 'migrate');
        this.setAttribute('columns', MigrateWidget.columns);
        this.setAttribute('rows', MigrateWidget.rows);

        this._data = { file: null, phrase: '', model: '' };

        const card = document.createElement('card-layout');
        card.init({ title: 'Migrate' });

        const step = document.createElement('step-layout');
        step.init({ steps: ['diary', 'model'] });

        this._panels = {};
        for (const id of ['diary', 'model', 'loading', 'result']) {
            const panel = document.createElement('step-panel');
            panel.init({ id });
            step.addPanel(panel);
            this._panels[id] = panel;
        }

        card.body.appendChild(step);
        this.appendChild(card);
        this._card = card;
        this._step = step;

        this._renderDiary();
        this._renderModel();
        this._panels.loading.innerHTML = '<div class="spinner"></div>';
        step.go('diary');
    }

    reset() {
        this._data = { file: null, phrase: '', model: '' };
        this._renderDiary();
        this._renderModel();
        this._step.go('diary');
    }

    setFocused(focused) {
        this._card.setFocused(focused);
        this.classList.toggle('focused', focused);
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    _renderDiary() {
        const s = this._panels.diary;
        s.innerHTML = `
            <label class="wizard-label">Diary file</label>
            <div class="migrate-dropzone">
                <input type="file" class="migrate-file-input">
                <span class="migrate-dropzone-text">${this._data.file ? this._esc(this._data.file.name) : 'Choose or drop a diary file'}</span>
            </div>
            <label class="wizard-label">Recovery phrase</label>
            <textarea class="wizard-input wizard-textarea" placeholder="Enter your recovery phrase">${this._esc(this._data.phrase)}</textarea>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-next">Next</button>
            </div>
        `;

        const fileZone = s.querySelector('.migrate-dropzone');
        const fileInput = s.querySelector('.migrate-file-input');
        const fileText = s.querySelector('.migrate-dropzone-text');
        const phraseInput = s.querySelector('textarea');

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                this._data.file = fileInput.files[0];
                fileText.textContent = this._data.file.name;
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
            }
        });

        const go = () => {
            const phrase = phraseInput.value.trim();
            if (!this._data.file || !phrase) return;
            this._data.phrase = phrase;
            this._renderModel();
            this._step.go('model');
        };
        phraseInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); go(); }
        });
        s.querySelector('#wz-next').addEventListener('click', go);
    }

    _renderModel() {
        const s = this._panels.model;
        const models = this._props.models();

        if (models.length === 0) {
            s.innerHTML = `
                <label class="wizard-label">No models available</label>
                <div class="wizard-nav">
                    <button class="wizard-btn" id="wz-back">Back</button><span></span>
                </div>
            `;
            s.querySelector('#wz-back').addEventListener('click', () => this._step.go('diary'));
            return;
        }

        const options = models.map(m => {
            const fit = m.fits ? '✓' : '✗';
            const ram = m.ram_required_gb ? `${m.ram_required_gb}GB RAM` : '';
            const params = m.params_b ? `${m.params_b}B` : '';
            const meta = [params, ram].filter(Boolean).join(' · ');
            const selected = this._data.model === m.name ? 'selected' : '';
            return `<div class="wizard-option ${selected}" data-model="${this._esc(m.name)}">
                <span class="wizard-option-fit">${fit}</span>
                <span class="wizard-option-name">${this._esc(m.name)}</span>
                <span class="wizard-option-meta">${meta}</span>
            </div>`;
        }).join('');

        s.innerHTML = `
            <label class="wizard-label">Choose a base model for migration</label>
            <div class="wizard-options">${options}</div>
            <div class="wizard-nav">
                <button class="wizard-btn" id="wz-back">Back</button>
                <button class="wizard-btn primary" id="wz-migrate" ${!this._data.model ? 'disabled' : ''}>Migrate</button>
            </div>
        `;

        const migrateBtn = s.querySelector('#wz-migrate');
        s.querySelectorAll('.wizard-option').forEach(el => {
            el.addEventListener('click', () => {
                this._data.model = el.dataset.model;
                s.querySelectorAll('.wizard-option').forEach(o => o.classList.remove('selected'));
                el.classList.add('selected');
                migrateBtn.removeAttribute('disabled');
            });
        });
        migrateBtn.addEventListener('click', () => { if (this._data.model) this._submit(); });
        s.querySelector('#wz-back').addEventListener('click', () => this._step.go('diary'));
    }

    async _submit() {
        this._step.go('loading');
        const form = new FormData();
        form.append('diary', this._data.file);
        form.append('phrase', this._data.phrase);
        form.append('model', this._data.model);
        try {
            const res = await fetch('/api/persona/migrate', { method: 'POST', body: form });
            if (!res.ok) {
                const err = await res.json();
                this._showError(err.detail || 'Migration failed');
                return;
            }
            const data = await res.json();
            this._showResult(data.persona_id, data.name);
        } catch { this._showError('Network error'); }
    }

    _showError(msg) {
        this._step.go('model');
        const s = this._panels.model;
        const existing = s.querySelector('.wizard-error');
        if (existing) existing.remove();
        const el = document.createElement('p');
        el.className = 'wizard-error';
        el.textContent = msg;
        s.prepend(el);
    }

    _showResult(personaId, name) {
        const s = this._panels.result;
        s.innerHTML = `
            <label class="wizard-label">Migration complete</label>
            <p class="wizard-hint">
                <strong>${this._esc(name)}</strong> has been restored and is ready to use.
            </p>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-done">Open Persona</button>
            </div>
        `;
        s.querySelector('#wz-done').addEventListener('click', () => {
            if (this._props.onMigrated) this._props.onMigrated(personaId);
        });
        this._step.go('result');
    }
}

customElements.define('migrate-widget', MigrateWidget);
export default MigrateWidget;
