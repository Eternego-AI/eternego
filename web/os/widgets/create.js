import Widget from './widget.js';

class CreateWidget extends Widget {
    static columns = 3;
    static rows = 2;

    // init({ models, onCreated })
    build() {
        this.setAttribute('widget', 'create');
        this.setAttribute('columns', CreateWidget.columns);
        this.setAttribute('rows', CreateWidget.rows);

        this._data = { name: '', model: '', botToken: '', frontierModel: '', frontierKey: '' };

        const card = document.createElement('card-layout');
        card.init({ title: 'Create' });

        const step = document.createElement('step-layout');
        step.init({ steps: ['name', 'model', 'telegram', 'frontier'] });

        this._panels = {};
        for (const id of ['name', 'model', 'telegram', 'frontier', 'loading', 'result']) {
            const panel = document.createElement('step-panel');
            panel.init({ id });
            step.addPanel(panel);
            this._panels[id] = panel;
        }

        card.body.appendChild(step);
        this.appendChild(card);
        this._card = card;
        this._step = step;

        this._renderName();
        this._renderModel();
        this._renderTelegram();
        this._renderFrontier();
        this._panels.loading.innerHTML = '<div class="spinner"></div>';
        step.go('name');
    }

    reset() {
        this._data = { name: '', model: '', botToken: '', frontierModel: '', frontierKey: '' };
        this._renderName();
        this._renderModel();
        this._renderTelegram();
        this._renderFrontier();
        this._step.go('name');
    }

    focusInput() {
        const active = this._step._activeId;
        const panel = this._panels[active];
        if (!panel) return;
        const input = panel.querySelector('input:not([type=hidden])');
        if (input) setTimeout(() => input.focus(), 50);
    }

    setFocused(focused) {
        this._card.setFocused(focused);
        this.classList.toggle('focused', focused);
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    _renderName() {
        const s = this._panels.name;
        s.innerHTML = `
            <label class="wizard-label">What should we call your persona?</label>
            <input class="wizard-input" type="text" placeholder="Name" value="${this._esc(this._data.name)}">
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-next">Next</button>
            </div>
        `;
        const input = s.querySelector('input');
        const go = () => {
            const val = input.value.trim();
            if (!val) return;
            this._data.name = val;
            this._renderModel();
            this._step.go('model');
        };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
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
            s.querySelector('#wz-back').addEventListener('click', () => this._step.go('name'));
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
            <label class="wizard-label">Choose a base model</label>
            <div class="wizard-options">${options}</div>
            <div class="wizard-nav">
                <button class="wizard-btn" id="wz-back">Back</button>
                <button class="wizard-btn primary" id="wz-next" ${!this._data.model ? 'disabled' : ''}>Next</button>
            </div>
        `;

        const nextBtn = s.querySelector('#wz-next');
        s.querySelectorAll('.wizard-option').forEach(el => {
            el.addEventListener('click', () => {
                this._data.model = el.dataset.model;
                s.querySelectorAll('.wizard-option').forEach(o => o.classList.remove('selected'));
                el.classList.add('selected');
                nextBtn.removeAttribute('disabled');
            });
        });

        const go = () => {
            if (!this._data.model) return;
            this._step.go('telegram');
            fetch('/api/environment/prepare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: this._data.model }),
            }).catch(() => {});
        };
        nextBtn.addEventListener('click', go);
        s.querySelector('#wz-back').addEventListener('click', () => this._step.go('name'));
    }

    _renderTelegram() {
        const s = this._panels.telegram;
        s.innerHTML = `
            <label class="wizard-label">Telegram Bot Token</label>
            <p class="wizard-hint">
                Open <strong>@BotFather</strong> on Telegram, send <code>/newbot</code>,
                follow the prompts, and paste the token here.
            </p>
            <input class="wizard-input" type="text" placeholder="123456:ABC-DEF..." value="${this._esc(this._data.botToken)}">
            <div class="wizard-nav">
                <button class="wizard-btn" id="wz-back">Back</button>
                <button class="wizard-btn primary" id="wz-next">Next</button>
            </div>
        `;
        const input = s.querySelector('input');
        const go = () => {
            const val = input.value.trim();
            if (!val) return;
            this._data.botToken = val;
            this._step.go('frontier');
        };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        s.querySelector('#wz-next').addEventListener('click', go);
        s.querySelector('#wz-back').addEventListener('click', () => {
            this._renderModel();
            this._step.go('model');
        });
    }

    _renderFrontier() {
        const s = this._panels.frontier;
        s.innerHTML = `
            <label class="wizard-label">Frontier Model (optional)</label>
            <p class="wizard-hint">
                A frontier model is used when your persona encounters something it can't handle
                on its own. This is optional. Leave blank to skip.
            </p>
            <input class="wizard-input" type="text" placeholder="Model (e.g. claude-opus-4-6)" value="${this._esc(this._data.frontierModel)}">
            <input class="wizard-input" type="password" placeholder="API Key" value="${this._esc(this._data.frontierKey)}" style="margin-top: 12px;">
            <div class="wizard-nav">
                <button class="wizard-btn" id="wz-back">Back</button>
                <button class="wizard-btn primary" id="wz-create">Create</button>
            </div>
        `;
        const inputs = s.querySelectorAll('input');
        const create = () => {
            this._data.frontierModel = inputs[0].value.trim();
            this._data.frontierKey = inputs[1].value.trim();
            this._submit();
        };
        inputs[1].addEventListener('keydown', (e) => { if (e.key === 'Enter') create(); });
        s.querySelector('#wz-create').addEventListener('click', create);
        s.querySelector('#wz-back').addEventListener('click', () => this._step.go('telegram'));
    }

    async _submit() {
        this._step.go('loading');
        const body = {
            name: this._data.name,
            model: this._data.model,
            channel_type: 'telegram',
            channel_credentials: { token: this._data.botToken },
        };
        if (this._data.frontierModel) {
            body.frontier_model = this._data.frontierModel;
            body.frontier_provider = 'anthropic';
            body.frontier_credentials = { api_key: this._data.frontierKey };
        }
        try {
            const res = await fetch('/api/persona/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json();
                this._showError(err.detail || 'Creation failed');
                return;
            }
            const data = await res.json();
            this._showResult(data.recovery_phrase, data.persona_id);
        } catch { this._showError('Network error'); }
    }

    _showError(msg) {
        this._step.go('frontier');
        const s = this._panels.frontier;
        const existing = s.querySelector('.wizard-error');
        if (existing) existing.remove();
        const el = document.createElement('p');
        el.className = 'wizard-error';
        el.textContent = msg;
        s.prepend(el);
    }

    _showResult(phrase, personaId) {
        const s = this._panels.result;
        s.innerHTML = `
            <label class="wizard-label">Recovery Phrase</label>
            <p class="wizard-hint">Write down this phrase and keep it safe. You'll need it to recover your persona.</p>
            <code class="wizard-phrase">${this._esc(phrase)}</code>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-done">I wrote down my phrases</button>
            </div>
        `;
        s.querySelector('#wz-done').addEventListener('click', () => {
            if (this._props.onCreated) this._props.onCreated(personaId);
        });
        this._step.go('result');
    }
}

customElements.define('create-widget', CreateWidget);
export default CreateWidget;
