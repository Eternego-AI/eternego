import OS from '../../../../os.js';

class CreateWidget extends HTMLElement {
    connectedCallback() {
        this._step = 0;
        this._data = { name: '', model: '', botToken: '', frontierModel: '', frontierKey: '' };
        this._models = [];

        this.innerHTML = `
            <div class="wizard">
                <div class="wizard-steps"></div>
                <div class="wizard-loading"><div class="spinner"></div></div>
                <div class="wizard-result"></div>
            </div>
        `;

        this._stepsEl = this.querySelector('.wizard-steps');
        this._loadingEl = this.querySelector('.wizard-loading');
        this._resultEl = this.querySelector('.wizard-result');

        this._render();

        OS.onNavigate(({ app }) => {
            if (app === 'new-persona') this._reset();
        });
    }

    _reset() {
        this._step = 0;
        this._data = { name: '', model: '', botToken: '', frontierModel: '', frontierKey: '' };
        this._models = [];
        this._render();
    }

    _render() {
        this._loadingEl.style.display = 'none';
        this._resultEl.style.display = 'none';
        this._stepsEl.style.display = '';

        const steps = [
            this._stepName,
            this._stepModel,
            this._stepTelegram,
            this._stepFrontier,
        ];

        this._stepsEl.innerHTML = '';
        steps[this._step].call(this);
    }

    // ── Step 1: Name ────────────────────────────────────────

    _stepName() {
        this._stepsEl.innerHTML = `
            <label class="wizard-label">What should we call your persona?</label>
            <input class="wizard-input" type="text" placeholder="Name" value="${this._esc(this._data.name)}" autofocus>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-next">Next</button>
            </div>
        `;

        const input = this._stepsEl.querySelector('input');
        const next = this._stepsEl.querySelector('#wz-next');

        setTimeout(() => input.focus(), 50);

        const go = () => {
            const val = input.value.trim();
            if (!val) return;
            this._data.name = val;
            this._step = 1;
            this._render();
            this._fetchModels();
        };

        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        next.addEventListener('click', go);
    }

    // ── Step 2: Model ───────────────────────────────────────

    async _fetchModels() {
        if (this._models.length > 0) return;
        try {
            const res = await fetch('/api/models');
            const data = await res.json();
            this._models = data.models || [];
            this._render();
        } catch {}
    }

    _stepModel() {
        if (this._models.length === 0) {
            this._stepsEl.innerHTML = `
                <label class="wizard-label">Loading available models...</label>
                <div class="wizard-nav">
                    <button class="wizard-btn" id="wz-back">Back</button>
                    <span></span>
                </div>
            `;
            this._stepsEl.querySelector('#wz-back').addEventListener('click', () => {
                this._step = 0; this._render();
            });
            return;
        }

        const options = this._models.map(m => {
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

        this._stepsEl.innerHTML = `
            <label class="wizard-label">Choose a base model</label>
            <div class="wizard-options">${options}</div>
            <div class="wizard-nav">
                <button class="wizard-btn" id="wz-back">Back</button>
                <button class="wizard-btn primary" id="wz-next" ${!this._data.model ? 'disabled' : ''}>Next</button>
            </div>
        `;

        const nextBtn = this._stepsEl.querySelector('#wz-next');

        this._stepsEl.querySelectorAll('.wizard-option').forEach(el => {
            el.addEventListener('click', () => {
                this._data.model = el.dataset.model;
                this._stepsEl.querySelectorAll('.wizard-option').forEach(o => o.classList.remove('selected'));
                el.classList.add('selected');
                nextBtn.removeAttribute('disabled');
            });
        });

        const go = () => {
            if (!this._data.model) return;
            this._step = 2;
            this._render();
            // Fire-and-forget model preparation
            fetch('/api/environment/prepare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: this._data.model }),
            }).catch(() => {});
        };

        nextBtn.addEventListener('click', go);
        this._stepsEl.querySelector('#wz-back').addEventListener('click', () => {
            this._step = 0; this._render();
        });
    }

    // ── Step 3: Telegram ────────────────────────────────────

    _stepTelegram() {
        this._stepsEl.innerHTML = `
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

        const input = this._stepsEl.querySelector('input');
        setTimeout(() => input.focus(), 50);

        const go = () => {
            const val = input.value.trim();
            if (!val) return;
            this._data.botToken = val;
            this._step = 3;
            this._render();
        };

        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        this._stepsEl.querySelector('#wz-next').addEventListener('click', go);
        this._stepsEl.querySelector('#wz-back').addEventListener('click', () => {
            this._step = 1; this._render();
        });
    }

    // ── Step 4: Frontier ────────────────────────────────────

    _stepFrontier() {
        this._stepsEl.innerHTML = `
            <label class="wizard-label">Frontier Model (optional)</label>
            <p class="wizard-hint">
                A frontier model is used when your persona encounters something it can't handle
                on its own — like learning your preferences or dealing with unfamiliar requests.
                This is optional. Leave blank to skip.
            </p>
            <input class="wizard-input" type="text" placeholder="Model (e.g. claude-opus-4-6)" value="${this._esc(this._data.frontierModel)}">
            <input class="wizard-input" type="password" placeholder="API Key" value="${this._esc(this._data.frontierKey)}" style="margin-top: 12px;">
            <div class="wizard-nav">
                <button class="wizard-btn" id="wz-back">Back</button>
                <button class="wizard-btn primary" id="wz-create">Create</button>
            </div>
        `;

        const inputs = this._stepsEl.querySelectorAll('input');
        setTimeout(() => inputs[0].focus(), 50);

        const create = () => {
            this._data.frontierModel = inputs[0].value.trim();
            this._data.frontierKey = inputs[1].value.trim();
            this._submit();
        };

        inputs[1].addEventListener('keydown', (e) => { if (e.key === 'Enter') create(); });
        this._stepsEl.querySelector('#wz-create').addEventListener('click', create);
        this._stepsEl.querySelector('#wz-back').addEventListener('click', () => {
            this._step = 2; this._render();
        });
    }

    // ── Submit ──────────────────────────────────────────────

    async _submit() {
        this._stepsEl.style.display = 'none';
        this._loadingEl.style.display = 'flex';

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
        } catch (e) {
            this._showError('Network error');
        }
    }

    _showError(msg) {
        this._loadingEl.style.display = 'none';
        this._stepsEl.style.display = '';
        // Stay on current step, show error
        const existing = this._stepsEl.querySelector('.wizard-error');
        if (existing) existing.remove();
        const el = document.createElement('p');
        el.className = 'wizard-error';
        el.textContent = msg;
        this._stepsEl.prepend(el);
    }

    _showResult(phrase, personaId) {
        this._loadingEl.style.display = 'none';
        this._resultEl.style.display = '';

        this._resultEl.innerHTML = `
            <label class="wizard-label">Recovery Phrase</label>
            <p class="wizard-hint">Write down this phrase and keep it safe. You'll need it to recover your persona.</p>
            <code class="wizard-phrase">${this._esc(phrase)}</code>
            <div class="wizard-nav">
                <span></span>
                <button class="wizard-btn primary" id="wz-done">I wrote down my phrases</button>
            </div>
        `;

        this._resultEl.querySelector('#wz-done').addEventListener('click', () => {
            // Refresh personas and navigate
            OS.fetchPersonas().then(() => {
                OS.open('persona', { personaId });
            });
        });
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}

customElements.define('create-widget', CreateWidget);
