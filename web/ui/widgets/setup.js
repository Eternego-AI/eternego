import Widget from './widget.js';

class SetupWidget extends Widget {
    static _css = `
        setup-widget {
            display: flex;
        }
        setup-widget .sw-label { font-size: 13px; font-weight: 400; color: var(--text-body); }
        setup-widget .sw-hint { font-size: 11px; font-weight: 300; color: var(--text-secondary); line-height: 1.6; }
        setup-widget .sw-hint strong { color: var(--text-body); font-weight: 500; }
        setup-widget .sw-hint code { background: var(--surface-hover); padding: 1px 5px; border-radius: var(--radius-sm); font-size: 10px; }
        setup-widget .sw-input {
            width: 100%; padding: 10px 14px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default);
            border-radius: var(--radius-lg); color: var(--text-body); font-family: var(--font); font-size: 13px; outline: none;
            transition: border-color 0.3s var(--ease);
        }
        setup-widget .sw-input::placeholder { color: var(--text-dim); }
        setup-widget .sw-url { font-size: 11px; color: var(--text-secondary); padding: 8px 14px; }
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
        setup-widget .sw-progress-bar {
            width: 100%; height: 4px; background: var(--surface-recessed); border-radius: 2px; overflow: hidden; margin-top: 16px;
        }
        setup-widget .sw-progress-fill {
            height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s var(--ease); width: 0%;
        }
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
        setup-widget .sw-dropzone-text { font-size: 12px; color: var(--text-secondary); pointer-events: none; }
        setup-widget .sw-file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    `;

    // init({ onCreate(data), onMigrate(data), onPrepare(model), onPair(code), onCancel, signals, api })
    build() {
        this.constructor._injectStyles();
        this._data = {};
        this._providerDefaults = { local: { url: 'http://localhost:11434' }, anthropic: { url: 'https://api.anthropic.com' }, openai: { url: 'https://api.openai.com' } };

        if (this._props.api?.fetchProviderConfig) {
            this._props.api.fetchProviderConfig().then(cfg => { this._providerDefaults = cfg; });
        }

        const card = document.createElement('card-layout');
        card.init({ title: 'Get started' });

        this._step = document.createElement('step-layout');
        this._step.init({ steps: ['name', 'model', 'vision', 'channel', 'frontier'] });

        this._panels = {};
        for (const id of ['choice', 'name', 'model', 'vision', 'channel', 'frontier', 'loading', 'result', 'pair', 'migrate-file', 'migrate-model']) {
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
                if (btn.dataset.action === 'create') { this._data = { name: '', thinkingModel: '', thinkingProvider: null, thinkingKey: '', thinkingUrl: '', visionModel: '', visionProvider: null, visionKey: '', visionUrl: '', channelType: 'telegram', botToken: '', frontierModel: '', frontierProvider: null, frontierKey: '', frontierUrl: '' }; this._history = []; this._history.push('choice'); this._renderName(); this._step.go('name'); }
                else { this._data = { file: null, phrase: '', model: '', provider: null, key: '', url: '' }; this._history = []; this._history.push('choice'); this._renderMigrateFile(); this._step.go('migrate-file'); }
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

    _back() {
        if (!this._history || this._history.length === 0) return;
        const prev = this._history.pop();
        if (prev === 'choice') { this._renderChoice(); this._step.go('choice'); }
        else if (prev === 'name') { this._renderName(); this._step.go('name'); }
        else if (prev === 'model') { this._renderModel(); this._step.go('model'); }
        else if (prev === 'vision') { this._renderVision(); this._step.go('vision'); }
        else if (prev === 'channel') { this._renderChannel(); this._step.go('channel'); }
        else if (prev === 'frontier') { this._renderFrontier(); this._step.go('frontier'); }
        else if (prev === 'migrate-file') { this._renderMigrateFile(); this._step.go('migrate-file'); }
        else if (prev === 'migrate-model') { this._renderMigrateModel(); this._step.go('migrate-model'); }
    }

    // ── Create flow ──────────────────────────────────────────

    _renderName() {
        const s = this._panels.name;
        s.innerHTML = `
            <label class="sw-label">What should we call your persona?</label>
            <input class="sw-input" type="text" placeholder="Name" value="${this._esc(this._data.name)}">
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><button class="sw-btn primary">Next</button></div>
        `;
        const input = s.querySelector('input');
        const go = () => { const v = input.value.trim(); if (!v) return; this._data.name = v; this._history.push('name'); this._renderModel(); this._step.go('model'); };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
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
                <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
            </div>
            <div class="sw-model-fields"></div>
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><button class="sw-btn primary">Next</button></div>
        `;

        const fieldsEl = s.querySelector('.sw-model-fields');
        const renderFields = (prov) => {
            const key = prov || 'local';
            const urlVal = this._data.thinkingUrl || (this._providerDefaults[key] || {}).url || '';
            if (!prov) {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Ollama model name (e.g. <code>qwen2.5:7b</code>)</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="qwen2.5:7b" value="${this._esc(this._data.thinkingModel)}" style="margin-top:12px">
                `;
            } else if (prov === 'anthropic') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Claude model name and your Anthropic API key.</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="claude-sonnet-4-20250514" value="${this._esc(this._data.thinkingModel)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.thinkingKey)}" style="margin-top:12px">
                `;
            } else {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Works with ChatGPT, NVIDIA NIM, Together AI, Groq, or any OpenAI-compatible API.</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="gpt-4o" value="${this._esc(this._data.thinkingModel)}" style="margin-top:12px">
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
                if (prov !== provider) { this._data.thinkingModel = ''; this._data.thinkingKey = ''; this._data.thinkingUrl = ''; }
                renderFields(prov);
            });
        });

        const go = () => {
            const inputs = fieldsEl.querySelectorAll('input');
            this._data.thinkingUrl = inputs[0]?.value.trim();
            const model = inputs[1]?.value.trim();
            if (!model) return;
            this._data.thinkingModel = model;
            if (this._data.thinkingProvider) {
                const key = inputs[2]?.value.trim();
                if (!key) return;
                this._data.thinkingKey = key;
            } else {
                this._data.thinkingKey = '';
            }
            this._history.push('model');
            this._renderVision();
            this._step.go('vision');
        };
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderVision() {
        const s = this._panels.vision;
        const provider = this._data.visionProvider;
        s.innerHTML = `
            <label class="sw-label">Vision model (optional)</label>
            <p class="sw-hint">Used when your persona receives images. Skip to fall back to the thinking model.</p>
            <div class="sw-choice">
                <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
            </div>
            <div class="sw-vision-fields"></div>
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><div style="display:flex;gap:8px"><button class="sw-btn" data-skip>Skip</button><button class="sw-btn primary">Next</button></div></div>
        `;

        const fieldsEl = s.querySelector('.sw-vision-fields');
        const renderFields = (prov) => {
            const key = prov || 'local';
            const urlVal = this._data.visionUrl || (this._providerDefaults[key] || {}).url || '';
            if (!prov) {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Ollama vision model name (e.g. <code>llava:7b</code>).</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="llava:7b" value="${this._esc(this._data.visionModel)}" style="margin-top:12px">
                `;
            } else if (prov === 'anthropic') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Claude vision model name and your Anthropic API key.</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="claude-sonnet-4-20250514" value="${this._esc(this._data.visionModel)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.visionKey)}" style="margin-top:12px">
                `;
            } else {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Works with any OpenAI-compatible vision endpoint.</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="gpt-4o" value="${this._esc(this._data.visionModel)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.visionKey)}" style="margin-top:12px">
                `;
            }
        };

        renderFields(provider);

        s.querySelectorAll('.sw-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                s.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const prov = btn.dataset.provider || null;
                this._data.visionProvider = prov;
                if (prov !== provider) { this._data.visionModel = ''; this._data.visionKey = ''; this._data.visionUrl = ''; }
                renderFields(prov);
            });
        });

        const go = () => {
            const inputs = fieldsEl.querySelectorAll('input');
            this._data.visionUrl = inputs[0]?.value.trim();
            const model = inputs[1]?.value.trim();
            if (!model) return;
            this._data.visionModel = model;
            if (this._data.visionProvider) {
                const key = inputs[2]?.value.trim();
                if (!key) return;
                this._data.visionKey = key;
            } else {
                this._data.visionKey = '';
            }
            this._history.push('vision');
            this._renderChannel();
            this._step.go('channel');
        };

        const skip = () => {
            this._data.visionModel = '';
            this._data.visionKey = '';
            this._data.visionUrl = '';
            this._data.visionProvider = null;
            this._history.push('vision');
            this._renderChannel();
            this._step.go('channel');
        };

        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-skip]').addEventListener('click', skip);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderChannel() {
        const s = this._panels.channel;
        const type = this._data.channelType || 'telegram';
        s.innerHTML = `
            <label class="sw-label">Messaging channel</label>
            <div class="sw-choice">
                <div class="sw-choice-btn${type === 'telegram' ? ' selected' : ''}" data-type="telegram">Telegram</div>
                <div class="sw-choice-btn${type === 'discord' ? ' selected' : ''}" data-type="discord">Discord</div>
                <div class="sw-choice-btn${type === 'web' ? ' selected' : ''}" data-type="web">Web only</div>
            </div>
            <div class="sw-channel-fields"></div>
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><button class="sw-btn primary">Next</button></div>
        `;

        const fieldsEl = s.querySelector('.sw-channel-fields');
        const renderFields = (t) => {
            if (t === 'telegram') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Open <strong>@BotFather</strong> on Telegram, send <code>/newbot</code>, and paste the token here.</p>
                    <input class="sw-input" type="text" placeholder="123456:ABC-DEF..." value="${this._esc(this._data.botToken)}">
                `;
            } else if (t === 'discord') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Create an application at <strong>discord.com/developers/applications</strong>, add a bot, enable the <strong>Message Content Intent</strong>, and paste the bot token here.</p>
                    <input class="sw-input" type="text" placeholder="MTA..." value="${this._esc(this._data.botToken)}">
                `;
            } else {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Your persona will talk only through this web interface.</p>
                `;
            }
        };

        this._data.channelType = type;
        renderFields(type);

        s.querySelectorAll('.sw-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                s.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const t = btn.dataset.type;
                this._data.channelType = t;
                renderFields(t);
            });
        });

        const go = () => {
            const input = fieldsEl.querySelector('input');
            this._data.botToken = input ? input.value.trim() : '';
            this._history.push('channel');
            this._renderFrontier();
            this._step.go('frontier');
        };
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderFrontier() {
        const s = this._panels.frontier;
        const provider = this._data.frontierProvider;
        s.innerHTML = `
            <label class="sw-label">Frontier model (optional)</label>
            <p class="sw-hint">Used when your persona encounters something it can't handle alone. Skip to leave unset.</p>
            <div class="sw-choice">
                <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
            </div>
            <div class="sw-frontier-fields"></div>
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><div style="display:flex;gap:8px"><button class="sw-btn" data-skip>Skip</button><button class="sw-btn primary">Create</button></div></div>
        `;

        const fieldsEl = s.querySelector('.sw-frontier-fields');
        const renderFields = (prov) => {
            const key = prov || 'local';
            const urlVal = this._data.frontierUrl || (this._providerDefaults[key] || {}).url || '';
            if (!prov) {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Ollama model name (e.g. <code>qwen2.5:32b</code>).</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="qwen2.5:32b" value="${this._esc(this._data.frontierModel)}" style="margin-top:12px">
                `;
            } else if (prov === 'anthropic') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Claude model name and your Anthropic API key.</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="claude-opus-4-6" value="${this._esc(this._data.frontierModel)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.frontierKey)}" style="margin-top:12px">
                `;
            } else {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Works with ChatGPT, NVIDIA NIM, Together AI, Groq, or any OpenAI-compatible API.</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="gpt-4o" value="${this._esc(this._data.frontierModel)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.frontierKey)}" style="margin-top:12px">
                `;
            }
        };

        renderFields(provider);

        s.querySelectorAll('.sw-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                s.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const prov = btn.dataset.provider || null;
                this._data.frontierProvider = prov;
                if (prov !== provider) { this._data.frontierModel = ''; this._data.frontierKey = ''; this._data.frontierUrl = ''; }
                renderFields(prov);
            });
        });

        const go = () => {
            const inputs = fieldsEl.querySelectorAll('input');
            this._data.frontierUrl = inputs[0]?.value.trim();
            const model = inputs[1]?.value.trim();
            if (!model) return;
            this._data.frontierModel = model;
            if (this._data.frontierProvider) {
                const key = inputs[2]?.value.trim();
                if (!key) return;
                this._data.frontierKey = key;
            } else {
                this._data.frontierKey = '';
            }
            this._submitCreate();
        };

        const skip = () => {
            this._data.frontierModel = '';
            this._data.frontierKey = '';
            this._data.frontierUrl = '';
            this._data.frontierProvider = null;
            this._submitCreate();
        };

        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-skip]').addEventListener('click', skip);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    async _submitCreate() {
        this._step.go('loading');
        const loadingPanel = this._panels.loading;
        loadingPanel.innerHTML = `
            <div class="sw-spinner"></div>
            <div class="sw-status" style="text-align:center;font-size:11px;color:var(--text-secondary);margin-top:16px;">Preparing environment...</div>
            <div class="sw-progress-bar" style="display:none"><div class="sw-progress-fill"></div></div>
        `;
        const statusEl = loadingPanel.querySelector('.sw-status');
        const progressBar = loadingPanel.querySelector('.sw-progress-bar');
        const progressFill = loadingPanel.querySelector('.sw-progress-fill');

        // Connect system WebSocket for progress signals
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        let ws;
        try {
            ws = new WebSocket(`${protocol}//${location.host}/ws/system`);
            ws.onmessage = (e) => {
                try {
                    const msg = JSON.parse(e.data);
                    if (msg.title === 'Model pull progress') {
                        const d = msg.details || {};
                        statusEl.textContent = d.status || 'Downloading...';
                        if (d.total && d.completed) {
                            progressBar.style.display = 'block';
                            const pct = Math.round((d.completed / d.total) * 100);
                            progressFill.style.width = pct + '%';
                            statusEl.textContent = `${d.status || 'Downloading'} — ${pct}%`;
                        }
                    } else if (msg.title === 'Model create progress') {
                        statusEl.textContent = (msg.details || {}).status || 'Setting up model...';
                        progressBar.style.display = 'none';
                    } else if (msg.title) {
                        const t = msg.title.toLowerCase();
                        if (t.includes('persona') || t.includes('creat') || t.includes('wak'))
                            statusEl.textContent = msg.title;
                    }
                } catch {}
            };
        } catch {}

        try {
            if (this._props.onCreate) {
                const result = await this._props.onCreate(this._data);
                if (ws) ws.close();
                if (result.success) {
                    this._personaId = result.persona_id;
                    this._showResult(result.recovery_phrase);
                } else {
                    this._showError('frontier', result.message);
                }
            }
        } catch (e) {
            if (ws) ws.close();
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
        s.querySelector('.sw-btn').addEventListener('click', () => {
            if (this._data.channelType === 'telegram' || this._data.channelType === 'discord') {
                this._renderPair();
                this._step.go('pair');
            } else {
                this._done();
            }
        });
        this._step.go('result');
    }

    _renderPair() {
        const s = this._panels.pair;
        const isDiscord = this._data.channelType === 'discord';
        const label = isDiscord ? 'Connect to Discord' : 'Connect to Telegram';
        const hint = isDiscord
            ? 'Open a direct message with your bot on Discord and send any text. It will reply with a pairing code.'
            : 'Send any message to your bot on Telegram. It will reply with a pairing code.';
        s.innerHTML = `
            <label class="sw-label">${label}</label>
            <p class="sw-hint">${hint}</p>
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
                const result = await this._props.onPair(code, this._personaId);
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
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><button class="sw-btn primary">Next</button></div>
        `;
        const fileInput = s.querySelector('.sw-file-input');
        const fileText = s.querySelector('.sw-dropzone-text');
        const zone = s.querySelector('.sw-dropzone');
        const phrase = s.querySelector('textarea');

        fileInput.addEventListener('change', () => { if (fileInput.files.length) { this._data.file = fileInput.files[0]; fileText.textContent = this._data.file.name; } });
        zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => { e.preventDefault(); zone.classList.remove('dragover'); if (e.dataTransfer.files.length) { this._data.file = e.dataTransfer.files[0]; fileText.textContent = this._data.file.name; } });

        const go = () => { if (!this._data.file || !phrase.value.trim()) return; this._data.phrase = phrase.value.trim(); this._history.push('migrate-file'); this._renderMigrateModel(); this._step.go('migrate-model'); };
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    _renderMigrateModel() {
        const s = this._panels['migrate-model'];
        const provider = this._data.provider;
        s.innerHTML = `
            <label class="sw-label">Thinking model</label>
            <div class="sw-choice">
                <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
            </div>
            <div class="sw-migrate-fields"></div>
            <div class="sw-nav"><div style="display:flex;gap:8px"><button class="sw-btn" data-back>Back</button><button class="sw-btn" data-cancel>Cancel</button></div><button class="sw-btn primary">Migrate</button></div>
        `;

        const fieldsEl = s.querySelector('.sw-migrate-fields');
        const renderFields = (prov) => {
            const key = prov || 'local';
            const urlVal = this._data.url || (this._providerDefaults[key] || {}).url || '';
            if (!prov) {
                fieldsEl.innerHTML = `
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="qwen2.5:7b" value="${this._esc(this._data.model)}" style="margin-top:12px">
                `;
            } else if (prov === 'anthropic') {
                fieldsEl.innerHTML = `
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="claude-sonnet-4-20250514" value="${this._esc(this._data.model)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.key)}" style="margin-top:12px">
                `;
            } else {
                fieldsEl.innerHTML = `
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="gpt-4o" value="${this._esc(this._data.model)}" style="margin-top:12px">
                    <input class="sw-input" type="password" placeholder="API Key" value="${this._esc(this._data.key)}" style="margin-top:12px">
                `;
            }
        };

        renderFields(provider);

        s.querySelectorAll('.sw-choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                s.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const prov = btn.dataset.provider || null;
                this._data.provider = prov;
                if (prov !== provider) { this._data.model = ''; this._data.key = ''; this._data.url = ''; }
                renderFields(prov);
            });
        });

        const go = () => {
            const inputs = fieldsEl.querySelectorAll('input');
            this._data.url = inputs[0]?.value.trim();
            const model = inputs[1]?.value.trim();
            if (!model) return;
            this._data.model = model;
            if (this._data.provider) {
                const key = inputs[2]?.value.trim();
                if (!key) return;
                this._data.key = key;
            }
            this._submitMigrate();
        };
        s.querySelector('.sw-btn.primary').addEventListener('click', go);
        s.querySelector('[data-back]').addEventListener('click', () => this._back());
        s.querySelector('[data-cancel]').addEventListener('click', () => this._cancel());
    }

    async _submitMigrate() {
        this._step.go('loading');
        const loadingPanel = this._panels.loading;
        loadingPanel.innerHTML = `
            <div class="sw-spinner"></div>
            <div class="sw-status" style="text-align:center;font-size:11px;color:var(--text-secondary);margin-top:16px;">Migrating persona...</div>
            <div class="sw-progress-bar" style="display:none"><div class="sw-progress-fill"></div></div>
        `;
        const statusEl = loadingPanel.querySelector('.sw-status');
        const progressBar = loadingPanel.querySelector('.sw-progress-bar');
        const progressFill = loadingPanel.querySelector('.sw-progress-fill');

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        let ws;
        try {
            ws = new WebSocket(`${protocol}//${location.host}/ws/system`);
            ws.onmessage = (e) => {
                try {
                    const msg = JSON.parse(e.data);
                    if (msg.title === 'Model pull progress') {
                        const d = msg.details || {};
                        statusEl.textContent = d.status || 'Downloading...';
                        if (d.total && d.completed) {
                            progressBar.style.display = 'block';
                            const pct = Math.round((d.completed / d.total) * 100);
                            progressFill.style.width = pct + '%';
                            statusEl.textContent = `${d.status || 'Downloading'} — ${pct}%`;
                        }
                    } else if (msg.title) {
                        const t = msg.title.toLowerCase();
                        if (t.includes('persona') || t.includes('migrat'))
                            statusEl.textContent = msg.title;
                    }
                } catch {}
            };
        } catch {}

        try {
            if (this._props.onMigrate) {
                const result = await this._props.onMigrate(this._data);
                if (ws) ws.close();
                if (result.success) {
                    this._personaId = result.persona_id;
                    this._done();
                } else {
                    this._showError('migrate-model', result.message);
                }
            }
        } catch (e) {
            if (ws) ws.close();
            this._showError('migrate-model', 'Something went wrong');
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
