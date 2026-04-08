import Widget from './widget.js';

class SetupWidget extends Widget {
    static _css = `
        setup-widget {
            display: flex;
        }
        setup-widget .sw-label { font-size: 13px; font-weight: 400; color: var(--text-secondary); }
        setup-widget .sw-hint { font-size: 11px; font-weight: 300; color: var(--text-dim); line-height: 1.6; }
        setup-widget .sw-hint strong { color: var(--text-muted); font-weight: 500; }
        setup-widget .sw-hint code { background: var(--surface-hover); padding: 1px 5px; border-radius: var(--radius-sm); font-size: 10px; }
        setup-widget .sw-input {
            width: 100%; padding: 10px 14px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default);
            border-radius: var(--radius-lg); color: var(--text-body); font-family: var(--font); font-size: 13px; outline: none;
            transition: border-color 0.3s var(--ease);
        }
        setup-widget .sw-input::placeholder { color: var(--text-faint); }
        setup-widget .sw-input:focus { border-color: var(--accent-border); }
        setup-widget .sw-nav { display: flex; justify-content: space-between; align-items: center; padding-top: 20px; }
        setup-widget .sw-btn {
            padding: 8px 20px; background: var(--surface-hover); border: 1px solid var(--glass-border);
            border-radius: var(--radius-md); color: var(--text-secondary); font-family: var(--font); font-size: 12px;
            cursor: pointer; transition: border-color 0.2s, color 0.2s, background 0.2s;
        }
        setup-widget .sw-btn:hover { border-color: var(--border-hover); color: #fff; }
        setup-widget .sw-btn.primary { background: var(--accent-bg); border-color: var(--accent-border); color: var(--accent-text); }
        setup-widget .sw-btn.primary:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
        setup-widget .sw-btn:disabled { opacity: 0.3; cursor: not-allowed; }
        setup-widget .sw-error { padding: 10px 14px; background: var(--destructive-bg); border: 1px solid var(--destructive-border); border-radius: var(--radius-md); color: var(--destructive-text); font-size: 12px; }
        setup-widget .sw-phrase {
            display: block; padding: 16px; background: var(--surface-overlay); border: 1px solid var(--accent-border);
            border-radius: var(--radius-lg); color: var(--accent-text); font-family: var(--font); font-size: 13px;
            line-height: 1.8; word-spacing: 4px; user-select: all;
        }
        setup-widget .sw-spinner {
            width: 36px; height: 36px; border: 2px solid var(--border-default); border-top-color: var(--accent);
            border-radius: var(--radius-full); animation: sw-spin 0.8s linear infinite; margin: auto;
        }
        @keyframes sw-spin { to { transform: rotate(360deg); } }
        setup-widget .sw-choice {
            display: flex; gap: 12px; padding: 12px 0;
        }
        setup-widget .sw-choice-btn {
            flex: 1; padding: 16px; background: var(--surface-recessed); border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg); cursor: pointer; text-align: center;
            font-family: var(--font); font-size: 12px; color: var(--text-secondary);
            transition: border-color 0.2s, background 0.2s;
        }
        setup-widget .sw-choice-btn:hover { border-color: var(--border-hover); background: var(--surface-hover); }
        setup-widget .sw-choice-btn.selected { border-color: var(--accent-border); background: var(--accent-bg); color: var(--accent-text); }
        setup-widget .sw-dropzone {
            position: relative; padding: 24px; background: rgba(0,0,0,0.3); border: 1.5px dashed var(--glass-border);
            border-radius: var(--radius-lg); text-align: center; cursor: pointer; transition: border-color 0.3s, background 0.3s;
        }
        setup-widget .sw-dropzone:hover, setup-widget .sw-dropzone.dragover { border-color: var(--accent-border); background: var(--accent-bg); }
        setup-widget .sw-dropzone-text { font-size: 12px; color: var(--text-dim); pointer-events: none; }
        setup-widget .sw-file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    `;

    // init({ onCreate(data), onMigrate(data), onPrepare(model), onPair(code), onCancel, signals })
    build() {
        this.constructor._injectStyles();
        this._data = {};

        const card = document.createElement('card-layout');
        card.init({ title: 'Get started' });

        this._step = document.createElement('step-layout');
        this._step.init({ steps: ['name', 'model', 'channel', 'frontier'] });

        this._panels = {};
        for (const id of ['choice', 'name', 'model', 'channel', 'frontier', 'loading', 'result', 'pair', 'migrate-file', 'migrate-model']) {
            const panel = document.createElement('step-panel');
            panel.init({ id });
            this._step.addPanel(panel);
            this._panels[id] = panel;
        }

        card.body.appendChild(this._step);
        this.appendChild(card);
        this._card = card;

        this._renderChoice();
        this._step.go('choice');
    }

    _renderChoice() {
        const s = this._panels.choice;
        s.innerHTML = `
            <label class="sw-label">What would you like to do?</label>
            <div class="sw-choice">
                <div class="sw-choice-btn" data-action="create">Create a new persona</div>
                <div class="sw-choice-btn" data-action="migrate">Restore from diary</div>
            </div>
            <div class="sw-nav"><span></span></div>
        `;
        s.querySelectorAll('.sw-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.dataset.action === 'create') { this._data = { name: '', thinkingModel: '', thinkingProvider: null, thinkingKey: '', botToken: '', frontierModel: '', frontierKey: '' }; this._renderName(); this._step.go('name'); }
                else { this._data = { file: null, phrase: '', model: '' }; this._renderMigrateFile(); this._step.go('migrate-file'); }
            });
        });
        if (this._props.onCancel) {
            const cancel = document.createElement('button');
            cancel.className = 'sw-btn';
            cancel.textContent = 'Cancel';
            cancel.addEventListener('click', () => this._props.onCancel());
            s.querySelector('.sw-nav').prepend(cancel);
        }
    }

    _cancel() {
        if (this._props.onCancel) this._props.onCancel();
    }

    // ── Create flow ──────────────────────────────────────────

    _renderName() {
        const s = this._panels.name;
        s.innerHTML = `
            <label class="sw-label">What should we call your persona?</label>
            <input class="sw-input" type="text" placeholder="Name" value="${this._esc(this._data.name)}">
            <div class="sw-nav"><button class="sw-btn" data-cancel>Cancel</button><button class="sw-btn primary">Next</button></div>
        `;
        const input = s.querySelector('input');
        const go = () => { const v = input.value.trim(); if (!v) return; this._data.name = v; this._renderModel(); this._step.go('model'); };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
        setTimeout(() => input.focus(), 50);
    }

    _renderModel() {
        const s = this._panels.model;
        const provider = this._data.thinkingProvider;
        s.innerHTML = `
            <label class="sw-label">Thinking model</label>
            <div class="sw-choice">
                <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">ChatGPT</div>
            </div>
            <div class="sw-model-fields"></div>
            <div class="sw-nav"><button class="sw-btn" data-cancel>Cancel</button><button class="sw-btn primary">Next</button></div>
        `;

        const fieldsEl = s.querySelector('.sw-model-fields');
        const renderFields = (prov) => {
            if (!prov) {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Ollama model name (e.g. <code>qwen2.5:7b</code>)</p>
                    <input class="sw-input" type="text" placeholder="qwen2.5:7b" value="${this._esc(this._data.thinkingModel)}">
                `;
            } else if (prov === 'anthropic') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Claude model name and your Anthropic API key.</p>
                    <input class="sw-input" type="text" placeholder="claude-sonnet-4-20250514" value="${this._esc(this._data.thinkingModel)}">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.thinkingKey)}" style="margin-top:12px">
                `;
            } else {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the OpenAI model name and your API key.</p>
                    <input class="sw-input" type="text" placeholder="gpt-4o" value="${this._esc(this._data.thinkingModel)}">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.thinkingKey)}" style="margin-top:12px">
                `;
            }
        };

        renderFields(provider);

        s.querySelectorAll('.sw-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                s.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const prov = btn.dataset.provider || null;
                this._data.thinkingProvider = prov;
                if (prov !== provider) { this._data.thinkingModel = ''; this._data.thinkingKey = ''; }
                renderFields(prov);
            });
        });

        const go = () => {
            const inputs = fieldsEl.querySelectorAll('input');
            const model = inputs[0]?.value.trim();
            if (!model) return;
            this._data.thinkingModel = model;
            if (this._data.thinkingProvider) {
                const key = inputs[1]?.value.trim();
                if (!key) return;
                this._data.thinkingKey = key;
            } else {
                this._data.thinkingKey = '';
            }
            this._renderChannel();
            this._step.go('channel');
        };
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderChannel() {
        const s = this._panels.channel;
        s.innerHTML = `
            <label class="sw-label">Telegram Bot Token</label>
            <p class="sw-hint">Open <strong>@BotFather</strong> on Telegram, send <code>/newbot</code>, and paste the token here.</p>
            <input class="sw-input" type="text" placeholder="123456:ABC-DEF..." value="${this._esc(this._data.botToken)}">
            <div class="sw-nav"><button class="sw-btn" data-cancel>Cancel</button><button class="sw-btn primary">Next</button></div>
        `;
        const input = s.querySelector('input');
        const go = () => { this._data.botToken = input.value.trim(); this._renderFrontier(); this._step.go('frontier'); };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderFrontier() {
        const s = this._panels.frontier;
        s.innerHTML = `
            <label class="sw-label">Frontier model (optional)</label>
            <p class="sw-hint">Used when your persona encounters something it can't handle alone. Leave blank to skip.</p>
            <input class="sw-input" type="text" placeholder="Model (e.g. claude-opus-4-6)" value="${this._esc(this._data.frontierModel)}">
            <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.frontierKey)}" style="margin-top:12px">
            <div class="sw-nav"><button class="sw-btn" data-cancel>Cancel</button><button class="sw-btn primary">Create</button></div>
        `;
        const inputs = s.querySelectorAll('input');
        const go = () => { this._data.frontierModel = inputs[0].value.trim(); this._data.frontierKey = inputs[1].value.trim(); this._submitCreate(); };
        inputs[1].addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    async _submitCreate() {
        this._step.go('loading');
        const loadingPanel = this._panels.loading;
        loadingPanel.innerHTML = `
            <div class="sw-spinner"></div>
            <div class="sw-status" style="text-align:center;font-size:11px;color:var(--text-dim);margin-top:16px;">Preparing environment...</div>
        `;
        const statusEl = loadingPanel.querySelector('.sw-status');

        // Listen for progress signals
        const signalHandler = this._props.signals ? (e) => {
            for (const sig of e.detail) {
                const title = sig.title || '';
                if (title.toLowerCase().includes('prepar') || title.toLowerCase().includes('pull') ||
                    title.toLowerCase().includes('engine') || title.toLowerCase().includes('model') ||
                    title.toLowerCase().includes('creat')) {
                    statusEl.textContent = title;
                }
            }
        } : null;
        if (signalHandler) this._props.signals.addEventListener('update', signalHandler);

        try {
            statusEl.textContent = 'Creating persona...';
            if (this._props.onCreate) {
                const result = await this._props.onCreate(this._data);
                if (signalHandler) this._props.signals.removeEventListener('update', signalHandler);
                if (result.success) {
                    this._personaId = result.persona_id;
                    this._showResult(result.recovery_phrase);
                } else {
                    this._showError('frontier', result.message);
                }
            }
        } catch (e) {
            if (signalHandler) this._props.signals.removeEventListener('update', signalHandler);
            this._showError('frontier', 'Something went wrong');
        }
    }

    _showResult(phrase) {
        const s = this._panels.result;
        s.innerHTML = `
            <label class="sw-label">Recovery phrase</label>
            <p class="sw-hint">Write this down and keep it safe. You need it to recover your persona.</p>
            <code class="sw-phrase">${this._esc(phrase)}</code>
            <div class="sw-nav"><span></span><button class="sw-btn primary">I saved my phrase</button></div>
        `;
        s.querySelector('.sw-btn').addEventListener('click', () => { this._renderPair(); this._step.go('pair'); });
        this._step.go('result');
    }

    _renderPair() {
        const s = this._panels.pair;
        s.innerHTML = `
            <label class="sw-label">Connect to Telegram</label>
            <p class="sw-hint">Send any message to your bot on Telegram. It will reply with a pairing code.</p>
            <input class="sw-input" type="text" placeholder="Pairing code" style="text-transform:uppercase">
            <div class="sw-nav"><button class="sw-btn" data-skip>Skip</button><button class="sw-btn primary">Pair</button></div>
        `;
        const input = s.querySelector('input');
        const pairBtn = s.querySelector('.sw-btn.primary');
        const doPair = async () => {
            const code = input.value.trim();
            if (!code) return;
            pairBtn.disabled = true;
            try {
                const result = await this._props.onPair(code);
                if (result.success) {
                    this._done();
                } else {
                    this._showError('pair', result.message || 'Pairing failed');
                    pairBtn.disabled = false;
                }
            } catch { this._showError('pair', 'Pairing failed'); pairBtn.disabled = false; }
        };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') doPair(); });
        pairBtn.addEventListener('click', doPair);
        s.querySelector('[data-skip]').addEventListener('click', () => this._done());
        setTimeout(() => input.focus(), 50);
    }

    // ── Migrate flow ─────────────────────────────────────────

    _renderMigrateFile() {
        const s = this._panels['migrate-file'];
        s.innerHTML = `
            <label class="sw-label">Diary file</label>
            <div class="sw-dropzone">
                <input type="file" class="sw-file-input">
                <span class="sw-dropzone-text">${this._data.file ? this._esc(this._data.file.name) : 'Choose or drop a diary file'}</span>
            </div>
            <label class="sw-label">Recovery phrase</label>
            <textarea class="sw-input" placeholder="Enter your recovery phrase" style="min-height:60px;resize:vertical">${this._esc(this._data.phrase || '')}</textarea>
            <div class="sw-nav"><button class="sw-btn" data-cancel>Cancel</button><button class="sw-btn primary">Next</button></div>
        `;
        const fileInput = s.querySelector('.sw-file-input');
        const fileText = s.querySelector('.sw-dropzone-text');
        const zone = s.querySelector('.sw-dropzone');
        const phrase = s.querySelector('textarea');

        fileInput.addEventListener('change', () => { if (fileInput.files.length) { this._data.file = fileInput.files[0]; fileText.textContent = this._data.file.name; } });
        zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => { e.preventDefault(); zone.classList.remove('dragover'); if (e.dataTransfer.files.length) { this._data.file = e.dataTransfer.files[0]; fileText.textContent = this._data.file.name; } });

        const go = () => { if (!this._data.file || !phrase.value.trim()) return; this._data.phrase = phrase.value.trim(); this._renderMigrateModel(); this._step.go('migrate-model'); };
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderMigrateModel() {
        const s = this._panels['migrate-model'];
        s.innerHTML = `
            <label class="sw-label">Base model</label>
            <p class="sw-hint">Enter the Ollama model name (e.g. <code>qwen2.5:7b</code>)</p>
            <input class="sw-input" type="text" placeholder="qwen2.5:7b" value="${this._esc(this._data.model)}">
            <div class="sw-nav"><button class="sw-btn" data-cancel>Cancel</button><button class="sw-btn primary">Migrate</button></div>
        `;
        const input = s.querySelector('input');
        const go = () => { const v = input.value.trim(); if (!v) return; this._data.model = v; this._submitMigrate(); };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    async _submitMigrate() {
        this._step.go('loading');
        this._panels.loading.innerHTML = '<div class="sw-spinner"></div>';
        if (this._props.onMigrate) {
            const result = await this._props.onMigrate(this._data);
            if (result.success) {
                this._personaId = result.persona_id;
                this._done();
            } else {
                this._showError('migrate-model', result.message);
            }
        }
    }

    // ── Shared ───────────────────────────────────────────────

    _showError(panelId, msg) {
        this._step.go(panelId);
        const s = this._panels[panelId];
        const existing = s.querySelector('.sw-error');
        if (existing) existing.remove();
        const el = document.createElement('p');
        el.className = 'sw-error';
        el.textContent = msg;
        s.prepend(el);
    }

    _done() {
        if (this._props.onDone) this._props.onDone(this._personaId);
    }
}

customElements.define('setup-widget', SetupWidget);
export default SetupWidget;
