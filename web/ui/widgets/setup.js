import Widget from './widget.js';

class SetupWidget extends Widget {
    static _css = `
        setup-widget { display: flex; }
        setup-widget .sw-label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
        setup-widget .sw-hint {
            font-size: 12px;
            font-weight: 300;
            color: var(--text-secondary);
            line-height: 1.7;
        }
        setup-widget .sw-hint strong { color: var(--text-body); font-weight: 500; }
        setup-widget .sw-hint em { color: var(--accent-text); font-style: normal; font-weight: 500; }
        setup-widget .sw-hint code {
            background: var(--surface-hover);
            padding: 1px 5px;
            border-radius: var(--radius-sm);
            font-size: 11px;
        }
        setup-widget .sw-hint p { margin-bottom: 8px; }
        setup-widget .sw-hint p:last-child { margin-bottom: 0; }
        setup-widget .sw-input {
            width: 100%;
            padding: 10px 14px;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            color: var(--text-body);
            font-family: var(--font);
            font-size: 13px;
            outline: none;
            transition: border-color 0.3s var(--ease);
        }
        setup-widget .sw-input::placeholder { color: var(--text-dim); }
        setup-widget .sw-url { font-size: 11px; color: var(--text-secondary); padding: 8px 14px; }
        setup-widget .sw-input:focus { border-color: var(--accent-border); }
        setup-widget .sw-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 20px;
        }
        setup-widget .sw-nav-group { display: flex; gap: 8px; }
        setup-widget .sw-btn {
            padding: 8px 20px;
            background: var(--surface-hover);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: 12px;
            cursor: pointer;
            transition: border-color 0.2s, color 0.2s, background 0.2s;
        }
        setup-widget .sw-btn:hover { border-color: var(--border-hover); color: #fff; }
        setup-widget .sw-btn.primary {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        setup-widget .sw-btn.primary:hover {
            background: var(--accent-hover-bg);
            border-color: var(--accent-hover-border);
            color: #fff;
        }
        setup-widget .sw-btn:disabled { opacity: 0.3; cursor: not-allowed; }
        setup-widget .sw-error {
            padding: 10px 14px;
            background: var(--destructive-bg);
            border: 1px solid var(--destructive-border);
            border-radius: var(--radius-md);
            color: var(--destructive-text);
            font-size: 12px;
        }
        setup-widget .sw-phrase {
            display: block;
            padding: 16px;
            background: var(--surface-overlay);
            border: 1px solid var(--accent-border);
            border-radius: var(--radius-lg);
            color: var(--accent-text);
            font-family: var(--font);
            font-size: 13px;
            line-height: 1.8;
            word-spacing: 4px;
            user-select: all;
        }
        setup-widget .sw-spinner {
            width: 36px;
            height: 36px;
            border: 2px solid var(--border-default);
            border-top-color: var(--accent);
            border-radius: var(--radius-full);
            animation: sw-spin 0.8s linear infinite;
            margin: auto;
        }
        @keyframes sw-spin { to { transform: rotate(360deg); } }
        setup-widget .sw-progress-bar {
            width: 100%;
            height: 4px;
            background: var(--surface-recessed);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 16px;
        }
        setup-widget .sw-progress-fill {
            height: 100%;
            background: var(--accent);
            border-radius: 2px;
            transition: width 0.3s var(--ease);
            width: 0%;
        }
        setup-widget .sw-choice { display: flex; gap: 12px; padding: 12px 0; }
        setup-widget .sw-choice-btn {
            flex: 1;
            padding: 16px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            cursor: pointer;
            text-align: center;
            font-family: var(--font);
            font-size: 12px;
            color: var(--text-secondary);
            transition: border-color 0.2s, background 0.2s;
        }
        setup-widget .sw-choice-btn:hover { border-color: var(--border-hover); background: var(--surface-hover); }
        setup-widget .sw-choice-btn.selected {
            border-color: var(--accent-border);
            background: var(--accent-bg);
            color: var(--accent-text);
        }
        setup-widget .sw-reuse {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 12px 0;
        }
        setup-widget .sw-reuse-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 14px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            cursor: pointer;
            font-size: 12px;
            color: var(--text-secondary);
            transition: border-color 0.2s, background 0.2s;
        }
        setup-widget .sw-reuse-row:hover { border-color: var(--border-hover); background: var(--surface-hover); }
        setup-widget .sw-reuse-row.checked {
            border-color: var(--accent-border);
            background: var(--accent-bg);
            color: var(--accent-text);
        }
        setup-widget .sw-reuse-box {
            width: 14px;
            height: 14px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-default);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: transparent;
        }
        setup-widget .sw-reuse-row.checked .sw-reuse-box {
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        setup-widget .sw-dropzone {
            position: relative;
            padding: 24px;
            background: rgba(0,0,0,0.3);
            border: 1.5px dashed var(--glass-border);
            border-radius: var(--radius-lg);
            text-align: center;
            cursor: pointer;
            transition: border-color 0.3s, background 0.3s;
        }
        setup-widget .sw-dropzone:hover, setup-widget .sw-dropzone.dragover {
            border-color: var(--accent-border);
            background: var(--accent-bg);
        }
        setup-widget .sw-dropzone-text { font-size: 12px; color: var(--text-secondary); pointer-events: none; }
        setup-widget .sw-file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    `;

    // init({ onCreate(data), onMigrate(data), onDone(personaId), onCancel })
    build() {
        this.constructor._injectStyles();
        this._data = {};
        this._providerDefaults = { local: { url: 'http://localhost:11434' }, anthropic: { url: 'https://api.anthropic.com' }, openai: { url: 'https://api.openai.com' } };
        this._mode = 'create';

        if (this._props.api?.fetchProviderConfig) {
            this._props.api.fetchProviderConfig().then(cfg => { this._providerDefaults = cfg; });
        }

        const card = document.createElement('card-layout');
        card.init({ title: 'Get started' });

        this._step = document.createElement('step-layout');
        this._step.init({ steps: ['name', 'thinking', 'vision', 'frontier', 'telegram', 'discord'] });

        this._panels = {};
        for (const id of ['choice', 'name', 'thinking', 'vision', 'frontier', 'telegram', 'discord', 'loading', 'result', 'migrate-file']) {
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

    _initData() {
        return {
            name: '',
            thinkingProvider: null, thinkingUrl: '', thinkingModel: '', thinkingKey: '',
            visionUseThinking: false,
            visionProvider: null, visionUrl: '', visionModel: '', visionKey: '',
            frontierReuse: null, // null | 'thinking' | 'vision'
            frontierProvider: null, frontierUrl: '', frontierModel: '', frontierKey: '',
            telegramToken: '',
            discordToken: '',
            file: null, phrase: '',
        };
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
                this._data = this._initData();
                this._history = ['choice'];
                if (btn.dataset.action === 'create') {
                    this._mode = 'create';
                    this._renderName();
                    this._step.go('name');
                } else {
                    this._mode = 'migrate';
                    this._renderMigrateFile();
                    this._step.go('migrate-file');
                }
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
        else if (prev === 'thinking') { this._renderThinking(); this._step.go('thinking'); }
        else if (prev === 'vision') { this._renderVision(); this._step.go('vision'); }
        else if (prev === 'frontier') { this._renderFrontier(); this._step.go('frontier'); }
        else if (prev === 'telegram') { this._renderTelegram(); this._step.go('telegram'); }
        else if (prev === 'discord') { this._renderDiscord(); this._step.go('discord'); }
        else if (prev === 'migrate-file') { this._renderMigrateFile(); this._step.go('migrate-file'); }
    }

    _navBar({ back = true, skip = false, primaryLabel = 'Next' }) {
        const backBtn = back ? `<button class="sw-btn" data-back>Back</button>` : '';
        const skipBtn = skip ? `<button class="sw-btn" data-skip>Skip</button>` : '';
        return `
            <div class="sw-nav">
                <div class="sw-nav-group">
                    ${backBtn}
                    <button class="sw-btn" data-cancel>Cancel</button>
                </div>
                <div class="sw-nav-group">
                    ${skipBtn}
                    <button class="sw-btn primary">${primaryLabel}</button>
                </div>
            </div>
        `;
    }

    _wireNav(s, { onPrimary, onSkip, onBack }) {
        const primary = s.querySelector('.sw-btn.primary');
        if (primary && onPrimary) primary.addEventListener('click', onPrimary);
        const skipBtn = s.querySelector('[data-skip]');
        if (skipBtn && onSkip) skipBtn.addEventListener('click', onSkip);
        const backBtn = s.querySelector('[data-back]');
        if (backBtn) backBtn.addEventListener('click', onBack || (() => this._back()));
        const cancelBtn = s.querySelector('[data-cancel]');
        if (cancelBtn) cancelBtn.addEventListener('click', () => this._cancel());
    }

    // ── Create flow ──────────────────────────────────────────

    _renderName() {
        const s = this._panels.name;
        s.innerHTML = `
            <label class="sw-label">What should we call your persona?</label>
            <p class="sw-hint">A name your persona will answer to. Choose something you'll enjoy saying aloud — it'll become familiar.</p>
            <input class="sw-input" type="text" placeholder="Name" value="${this._esc(this._data.name)}">
            ${this._navBar({})}
        `;
        const input = s.querySelector('input');
        const go = () => {
            const v = input.value.trim();
            if (!v) return;
            this._data.name = v;
            this._history.push('name');
            this._renderThinking();
            this._step.go('thinking');
        };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        this._wireNav(s, { onPrimary: go });
        setTimeout(() => input.focus(), 50);
    }

    _renderThinking() {
        const s = this._panels.thinking;
        const provider = this._data.thinkingProvider;
        s.innerHTML = `
            <label class="sw-label">Thinking model</label>
            <div class="sw-hint">
                <p>Your persona's core cognition. Every thought, every response, every remembered word runs through this model.</p>
                <p>Pick where it lives — on your machine via <strong>Ollama</strong>, or through a remote API. Local keeps everything on your hardware; remote lets you start with a frontier model for pennies per conversation.</p>
            </div>
            <div class="sw-choice">
                <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
            </div>
            <div class="sw-model-fields"></div>
            ${this._navBar({})}
        `;

        const fieldsEl = s.querySelector('.sw-model-fields');
        const renderFields = (prov) => {
            const key = prov || 'local';
            const urlVal = this._data.thinkingUrl || (this._providerDefaults[key] || {}).url || '';
            if (!prov) {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Enter the Ollama endpoint and a model you've pulled (e.g. <code>qwen2.5:7b</code>).</p>
                    <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                    <input class="sw-input" type="text" placeholder="qwen2.5:7b" value="${this._esc(this._data.thinkingModel)}" style="margin-top:12px">
                `;
            } else if (prov === 'anthropic') {
                fieldsEl.innerHTML = `
                    <p class="sw-hint">Claude endpoint, a model name, and your Anthropic API key.</p>
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
            this._history.push('thinking');
            this._renderVision();
            this._step.go('vision');
        };
        this._wireNav(s, { onPrimary: go });
    }

    _renderVision() {
        const s = this._panels.vision;
        const provider = this._data.visionProvider;
        const reused = this._data.visionUseThinking;
        s.innerHTML = `
            <label class="sw-label">Vision model <em style="font-style:normal;color:var(--text-muted);font-size:11px">(optional)</em></label>
            <div class="sw-hint">
                <p>Lets your persona interpret images — any image, from any source. The thinking model asks questions about what's in front of it; the vision model answers, and that answer becomes part of what your persona knows.</p>
                <p>Tick <em>Use thinking model</em> if your thinking model already understands images (Claude, GPT-4o). Skip if your persona won't encounter images; they'll be ignored when they arrive.</p>
            </div>
            <div class="sw-reuse">
                <div class="sw-reuse-row${reused ? ' checked' : ''}" data-reuse="thinking">
                    <div class="sw-reuse-box">✓</div>
                    <div>Use thinking model for vision</div>
                </div>
            </div>
            <div class="sw-vision-section"></div>
            ${this._navBar({ skip: true })}
        `;

        const section = s.querySelector('.sw-vision-section');
        const renderSection = () => {
            if (this._data.visionUseThinking) {
                section.innerHTML = '';
                return;
            }
            section.innerHTML = `
                <div class="sw-choice" style="margin-top:12px">
                    <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                    <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                    <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
                </div>
                <div class="sw-vision-fields"></div>
            `;
            const fieldsEl = section.querySelector('.sw-vision-fields');
            const renderFields = (prov) => {
                const key = prov || 'local';
                const urlVal = this._data.visionUrl || (this._providerDefaults[key] || {}).url || '';
                if (!prov) {
                    fieldsEl.innerHTML = `
                        <p class="sw-hint">An Ollama vision-capable model (e.g. <code>llava:7b</code>).</p>
                        <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                        <input class="sw-input" type="text" placeholder="llava:7b" value="${this._esc(this._data.visionModel)}" style="margin-top:12px">
                    `;
                } else if (prov === 'anthropic') {
                    fieldsEl.innerHTML = `
                        <p class="sw-hint">Claude model name and your Anthropic API key.</p>
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

            section.querySelectorAll('.sw-choice-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    section.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    const prov = btn.dataset.provider || null;
                    this._data.visionProvider = prov;
                    if (prov !== provider) { this._data.visionModel = ''; this._data.visionKey = ''; this._data.visionUrl = ''; }
                    renderFields(prov);
                });
            });
        };

        renderSection();

        s.querySelector('[data-reuse="thinking"]').addEventListener('click', () => {
            this._data.visionUseThinking = !this._data.visionUseThinking;
            this._renderVision();
            this._step.go('vision');
        });

        const go = () => {
            if (this._data.visionUseThinking) {
                this._history.push('vision');
                this._renderFrontier();
                this._step.go('frontier');
                return;
            }
            const fieldsEl = section.querySelector('.sw-vision-fields');
            const inputs = fieldsEl?.querySelectorAll('input') || [];
            this._data.visionUrl = inputs[0]?.value.trim() || '';
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
            this._renderFrontier();
            this._step.go('frontier');
        };

        const skip = () => {
            this._data.visionUseThinking = false;
            this._data.visionProvider = null;
            this._data.visionModel = '';
            this._data.visionKey = '';
            this._data.visionUrl = '';
            this._history.push('vision');
            this._renderFrontier();
            this._step.go('frontier');
        };

        this._wireNav(s, { onPrimary: go, onSkip: skip });
    }

    _renderFrontier() {
        const s = this._panels.frontier;
        const provider = this._data.frontierProvider;
        const reuse = this._data.frontierReuse;
        const hasVision = this._data.visionUseThinking || !!this._data.visionModel;

        const visionOption = hasVision
            ? `<div class="sw-reuse-row${reuse === 'vision' ? ' checked' : ''}" data-reuse="vision">
                    <div class="sw-reuse-box">✓</div>
                    <div>Use vision model</div>
                </div>`
            : '';

        s.innerHTML = `
            <label class="sw-label">Frontier model <em style="font-style:normal;color:var(--text-muted);font-size:11px">(optional)</em></label>
            <div class="sw-hint">
                <p>A teacher for your thinking model. When your persona runs into something it doesn't know how to do, it reaches for the frontier — learns from it — and carries the lesson forward, so it's less likely to get stuck next time.</p>
                <p>Tick <em>Use thinking</em> or <em>Use vision</em> to reuse one; otherwise configure fresh credentials. Skip and your persona will try everything with its thinking alone.</p>
            </div>
            <div class="sw-reuse">
                <div class="sw-reuse-row${reuse === 'thinking' ? ' checked' : ''}" data-reuse="thinking">
                    <div class="sw-reuse-box">✓</div>
                    <div>Use thinking model</div>
                </div>
                ${visionOption}
            </div>
            <div class="sw-frontier-section"></div>
            ${this._navBar({ skip: true })}
        `;

        const section = s.querySelector('.sw-frontier-section');
        const renderSection = () => {
            if (this._data.frontierReuse) {
                section.innerHTML = '';
                return;
            }
            section.innerHTML = `
                <div class="sw-choice" style="margin-top:12px">
                    <div class="sw-choice-btn${!provider ? ' selected' : ''}" data-provider="">Local (Ollama)</div>
                    <div class="sw-choice-btn${provider === 'anthropic' ? ' selected' : ''}" data-provider="anthropic">Claude</div>
                    <div class="sw-choice-btn${provider === 'openai' ? ' selected' : ''}" data-provider="openai">OpenAI-compatible</div>
                </div>
                <div class="sw-frontier-fields"></div>
            `;
            const fieldsEl = section.querySelector('.sw-frontier-fields');
            const renderFields = (prov) => {
                const key = prov || 'local';
                const urlVal = this._data.frontierUrl || (this._providerDefaults[key] || {}).url || '';
                if (!prov) {
                    fieldsEl.innerHTML = `
                        <p class="sw-hint">A larger local model (e.g. <code>qwen2.5:32b</code>).</p>
                        <input class="sw-input sw-url" type="text" value="${this._esc(urlVal)}">
                        <input class="sw-input" type="text" placeholder="qwen2.5:32b" value="${this._esc(this._data.frontierModel)}" style="margin-top:12px">
                    `;
                } else if (prov === 'anthropic') {
                    fieldsEl.innerHTML = `
                        <p class="sw-hint">A strong Claude model and your Anthropic API key.</p>
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

            section.querySelectorAll('.sw-choice-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    section.querySelectorAll('.sw-choice-btn').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    const prov = btn.dataset.provider || null;
                    this._data.frontierProvider = prov;
                    if (prov !== provider) { this._data.frontierModel = ''; this._data.frontierKey = ''; this._data.frontierUrl = ''; }
                    renderFields(prov);
                });
            });
        };

        renderSection();

        s.querySelectorAll('[data-reuse]').forEach(row => {
            row.addEventListener('click', () => {
                const choice = row.dataset.reuse;
                this._data.frontierReuse = (this._data.frontierReuse === choice) ? null : choice;
                this._renderFrontier();
                this._step.go('frontier');
            });
        });

        const go = () => {
            if (this._data.frontierReuse) {
                this._history.push('frontier');
                this._renderTelegram();
                this._step.go('telegram');
                return;
            }
            const fieldsEl = section.querySelector('.sw-frontier-fields');
            const inputs = fieldsEl?.querySelectorAll('input') || [];
            this._data.frontierUrl = inputs[0]?.value.trim() || '';
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
            this._history.push('frontier');
            this._renderTelegram();
            this._step.go('telegram');
        };

        const skip = () => {
            this._data.frontierReuse = null;
            this._data.frontierProvider = null;
            this._data.frontierModel = '';
            this._data.frontierKey = '';
            this._data.frontierUrl = '';
            this._history.push('frontier');
            this._renderTelegram();
            this._step.go('telegram');
        };

        this._wireNav(s, { onPrimary: go, onSkip: skip });
    }

    _renderTelegram() {
        const s = this._panels.telegram;
        s.innerHTML = `
            <label class="sw-label">Telegram <em style="font-style:normal;color:var(--text-muted);font-size:11px">(optional)</em></label>
            <div class="sw-hint">
                <p>A Telegram bot you own, so you can talk to your persona from your phone.</p>
                <p>Open <strong>@BotFather</strong> in Telegram, send <code>/newbot</code>, follow the prompts, paste the token here. Skip if you'll only use this web page.</p>
            </div>
            <input class="sw-input" type="text" placeholder="123456:ABC-DEF..." value="${this._esc(this._data.telegramToken)}">
            ${this._navBar({ skip: true })}
        `;
        const input = s.querySelector('input');
        const go = () => {
            this._data.telegramToken = input.value.trim();
            this._history.push('telegram');
            this._renderDiscord();
            this._step.go('discord');
        };
        const skip = () => {
            this._data.telegramToken = '';
            this._history.push('telegram');
            this._renderDiscord();
            this._step.go('discord');
        };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
        this._wireNav(s, { onPrimary: go, onSkip: skip });
        setTimeout(() => input.focus(), 50);
    }

    _renderDiscord() {
        const s = this._panels.discord;
        const primaryLabel = this._mode === 'migrate' ? 'Restore' : 'Create';
        s.innerHTML = `
            <label class="sw-label">Discord <em style="font-style:normal;color:var(--text-muted);font-size:11px">(optional)</em></label>
            <div class="sw-hint">
                <p>A Discord bot you own, reachable via direct message.</p>
                <p>At <strong>discord.com/developers/applications</strong> → New Application → Bot → enable <em>Message Content Intent</em> → copy the token. Skip if Discord isn't your thing.</p>
            </div>
            <input class="sw-input" type="text" placeholder="MTA..." value="${this._esc(this._data.discordToken)}">
            ${this._navBar({ skip: true, primaryLabel })}
        `;
        const input = s.querySelector('input');
        const submit = () => {
            this._data.discordToken = input.value.trim();
            if (this._mode === 'migrate') this._submitMigrate();
            else this._submitCreate();
        };
        const skip = () => {
            this._data.discordToken = '';
            if (this._mode === 'migrate') this._submitMigrate();
            else this._submitCreate();
        };
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
        this._wireNav(s, { onPrimary: submit, onSkip: skip });
        setTimeout(() => input.focus(), 50);
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

        const ws = this._openProgressWs(statusEl, progressBar, progressFill);

        try {
            if (this._props.onCreate) {
                const result = await this._props.onCreate(this._data);
                if (ws) ws.close();
                if (result.success) {
                    this._personaId = result.persona_id;
                    this._showResult(result.recovery_phrase);
                } else {
                    this._showError('discord', result.message);
                }
            }
        } catch (e) {
            if (ws) ws.close();
            this._showError('discord', 'Something went wrong');
        }
    }

    _showResult(phrase) {
        const s = this._panels.result;
        s.innerHTML = `
            <label class="sw-label">Recovery phrase</label>
            <p class="sw-hint">Write this down somewhere you trust. It's the key to your persona — without it, a diary backup can't be restored. We don't store it; if you lose it, it's gone.</p>
            <code class="sw-phrase">${this._esc(phrase)}</code>
            <div class="sw-nav"><span></span><button class="sw-btn primary">I saved my phrase</button></div>
        `;
        s.querySelector('.sw-btn').addEventListener('click', () => this._done());
        this._step.go('result');
    }

    // ── Migrate flow ─────────────────────────────────────────

    _renderMigrateFile() {
        const s = this._panels['migrate-file'];
        s.innerHTML = `
            <label class="sw-label">Diary file</label>
            <p class="sw-hint">The <code>.diary</code> backup you exported previously — the encrypted carrier of your persona's memory.</p>
            <div class="sw-dropzone">
                <input type="file" class="sw-file-input">
                <span class="sw-dropzone-text">${this._data.file ? this._esc(this._data.file.name) : 'Choose or drop a diary file'}</span>
            </div>
            <label class="sw-label" style="margin-top:12px">Recovery phrase</label>
            <p class="sw-hint">The phrase you wrote down when the persona was created.</p>
            <textarea class="sw-input" placeholder="Enter your recovery phrase" style="min-height:60px;resize:vertical">${this._esc(this._data.phrase || '')}</textarea>
            ${this._navBar({})}
        `;
        const fileInput = s.querySelector('.sw-file-input');
        const fileText = s.querySelector('.sw-dropzone-text');
        const zone = s.querySelector('.sw-dropzone');
        const phrase = s.querySelector('textarea');

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                this._data.file = fileInput.files[0];
                fileText.textContent = this._data.file.name;
            }
        });
        zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this._data.file = e.dataTransfer.files[0];
                fileText.textContent = this._data.file.name;
            }
        });

        const go = () => {
            if (!this._data.file || !phrase.value.trim()) return;
            this._data.phrase = phrase.value.trim();
            this._history.push('migrate-file');
            this._renderThinking();
            this._step.go('thinking');
        };
        this._wireNav(s, { onPrimary: go });
    }

    async _submitMigrate() {
        this._step.go('loading');
        const loadingPanel = this._panels.loading;
        loadingPanel.innerHTML = `
            <div class="sw-spinner"></div>
            <div class="sw-status" style="text-align:center;font-size:11px;color:var(--text-secondary);margin-top:16px;">Restoring persona...</div>
            <div class="sw-progress-bar" style="display:none"><div class="sw-progress-fill"></div></div>
        `;
        const statusEl = loadingPanel.querySelector('.sw-status');
        const progressBar = loadingPanel.querySelector('.sw-progress-bar');
        const progressFill = loadingPanel.querySelector('.sw-progress-fill');

        const ws = this._openProgressWs(statusEl, progressBar, progressFill);

        try {
            if (this._props.onMigrate) {
                const result = await this._props.onMigrate(this._data);
                if (ws) ws.close();
                if (result.success) {
                    this._personaId = result.persona_id;
                    this._done();
                } else {
                    this._showError('discord', result.message);
                }
            }
        } catch (e) {
            if (ws) ws.close();
            this._showError('discord', 'Something went wrong');
        }
    }

    // ── Shared ───────────────────────────────────────────────

    _openProgressWs(statusEl, progressBar, progressFill) {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        try {
            const ws = new WebSocket(`${protocol}//${location.host}/ws/system`);
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
                        if (t.includes('persona') || t.includes('creat') || t.includes('migrat') || t.includes('wak')) {
                            statusEl.textContent = msg.title;
                        }
                    }
                } catch {}
            };
            return ws;
        } catch {
            return null;
        }
    }

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
