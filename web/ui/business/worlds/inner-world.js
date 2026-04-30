import World from './world.js';
import '../../platform/layouts/simple-form.js';
import '../../platform/elements/action-button.js';

class InnerWorld extends World {
    static _styled = false;
    static _css = `
        inner-world {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: var(--space-xl);
            height: 100%;
            min-height: 0;
            padding: var(--space-xl);
            overflow: hidden;
        }
        inner-world .sections {
            display: flex;
            flex-direction: column;
            gap: var(--space-xs);
            overflow-y: auto;
            padding-right: var(--space-md);
            border-right: 1px solid var(--border-subtle);
        }
        inner-world .section {
            display: flex;
            align-items: center;
            justify-content: space-between;
            text-align: left;
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-sm);
            transition: all var(--time-quick);
            cursor: pointer;
            background: transparent;
            border: 1px solid transparent;
        }
        inner-world .section:hover { background: var(--surface-hover); }
        inner-world .section.active {
            background: var(--warm-bg);
            border-color: var(--warm-border);
        }
        inner-world .section .label {
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            color: var(--text-primary);
        }
        inner-world .section.active .label { color: var(--warm-text); }
        inner-world .section .count {
            font-size: var(--text-xs);
            color: var(--text-dim);
            font-family: var(--font-mono);
        }
        inner-world .divider {
            height: 1px;
            background: var(--border-subtle);
            margin: var(--space-md) 0;
        }
        inner-world .section.action .label { color: var(--accent-text); }
        inner-world .section.action.active {
            background: var(--accent-bg);
            border-color: var(--accent-border);
        }
        inner-world .content {
            overflow-y: auto;
            padding-right: var(--space-md);
        }
        inner-world .rows {
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
        }
        inner-world .row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: var(--space-md);
            padding: var(--space-md) var(--space-lg);
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-body);
            line-height: 1.6;
            font-size: var(--text-base);
        }
        inner-world .row .text { flex: 1; }
        inner-world .row-delete {
            padding: 2px 10px;
            color: var(--text-dim);
            font-size: var(--text-base);
            border-radius: var(--radius-sm);
            transition: all var(--time-quick);
            opacity: 0;
            cursor: pointer;
            background: transparent;
        }
        inner-world .row:hover .row-delete { opacity: 1; }
        inner-world .row-delete:hover {
            color: var(--danger-text);
            background: var(--danger-bg);
        }
        inner-world .empty {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-dim);
            font-size: var(--text-sm);
        }
        inner-world .intro {
            color: var(--text-muted);
            font-size: var(--text-sm);
            line-height: 1.6;
            margin-bottom: var(--space-lg);
        }
        inner-world .inline-error {
            margin-bottom: var(--space-lg);
            padding: var(--space-md) var(--space-lg);
            background: var(--danger-bg);
            border: 1px solid var(--danger-border);
            border-radius: var(--radius-md);
            color: var(--danger-text);
            font-size: var(--text-sm);
        }
        inner-world .inline-success {
            margin-bottom: var(--space-lg);
            padding: var(--space-md) var(--space-lg);
            background: var(--vital-bg);
            border: 1px solid var(--vital-border);
            border-radius: var(--radius-md);
            color: var(--vital-text);
            font-size: var(--text-sm);
        }
        inner-world .settings-group {
            margin-bottom: var(--space-2xl);
        }
        inner-world .settings-group h3 {
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--cool-text);
            margin-bottom: var(--space-md);
            font-weight: 500;
        }
        inner-world .save-row {
            display: flex;
            justify-content: flex-end;
            margin-top: var(--space-lg);
        }
    `;

    build() {
        const { id, api } = this._props;
        this.personaId = id;
        this.api = api;
        this.persona = null;
        this.data = null;
        this.selectedKey = 'person';
        this.feedValues = {};
        this.feedError = null;
        this.feedMessage = null;
        this.feeding = false;
        this.settingsValues = null;
        this.settingsError = null;
        this.settingsMessage = null;
        this.savingSettings = false;
    }

    async activate() {
        this.persona = await this.api.getPersona(this.personaId);
        this.data = await this.api.getOversee(this.personaId);
        this.render();
    }

    render() {
        this.innerHTML = `
            <div class="sections"></div>
            <div class="content"></div>
        `;
        const sectionsEl = this.querySelector('.sections');
        const contentEl = this.querySelector('.content');

        const sections = [
            { key: 'person',    label: 'About you' },
            { key: 'traits',    label: 'How she is' },
            { key: 'context',   label: 'Where she is' },
            { key: 'wishes',    label: 'What she wants' },
            { key: 'struggles', label: 'What she struggles with' },
            { key: 'history',   label: 'History' },
            { key: 'destiny',   label: 'Destiny' },
        ];

        for (const sec of sections) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'section' + (sec.key === this.selectedKey ? ' active' : '');
            btn.innerHTML = `<span class="label"></span><span class="count"></span>`;
            btn.querySelector('.label').textContent = sec.label;
            btn.querySelector('.count').textContent = (this.data?.[sec.key] || []).length;
            btn.addEventListener('click', () => { this.selectedKey = sec.key; this.render(); });
            sectionsEl.appendChild(btn);
        }

        const divider = document.createElement('div');
        divider.className = 'divider';
        sectionsEl.appendChild(divider);

        const settingsBtn = document.createElement('button');
        settingsBtn.type = 'button';
        settingsBtn.className = 'section action' + (this.selectedKey === '__settings' ? ' active' : '');
        settingsBtn.innerHTML = `<span class="label">Settings</span>`;
        settingsBtn.addEventListener('click', () => {
            this.selectedKey = '__settings';
            this.settingsMessage = null;
            this.settingsError = null;
            this.settingsValues = null;
            this.render();
        });
        sectionsEl.appendChild(settingsBtn);

        const feedBtn = document.createElement('button');
        feedBtn.type = 'button';
        feedBtn.className = 'section action' + (this.selectedKey === '__feed' ? ' active' : '');
        feedBtn.innerHTML = `<span class="label">+ Feed history</span>`;
        feedBtn.addEventListener('click', () => {
            this.selectedKey = '__feed';
            this.feedMessage = null;
            this.feedError = null;
            this.render();
        });
        sectionsEl.appendChild(feedBtn);

        if (this.selectedKey === '__feed') {
            this.renderFeed(contentEl);
            return;
        }
        if (this.selectedKey === '__settings') {
            this.renderSettings(contentEl);
            return;
        }

        const rows = this.data?.[this.selectedKey] || [];
        if (rows.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty';
            empty.textContent = 'Nothing yet.';
            contentEl.appendChild(empty);
            return;
        }

        const list = document.createElement('ul');
        list.className = 'rows';
        for (const row of rows) {
            const li = document.createElement('li');
            li.className = 'row';
            const text = document.createElement('span');
            text.className = 'text';
            text.textContent = (row.content || row).replace(/^[-*]\s+/, '');
            li.appendChild(text);
            if (row.id) {
                const del = document.createElement('button');
                del.type = 'button';
                del.className = 'row-delete';
                del.textContent = '×';
                del.title = 'Remove';
                del.addEventListener('click', () => this.removeRow(row.id));
                li.appendChild(del);
            }
            list.appendChild(li);
        }
        contentEl.appendChild(list);
    }

    renderFeed(contentEl) {
        const intro = document.createElement('div');
        intro.className = 'intro';
        intro.textContent = 'Bring her past — export your chat history from another AI and give it here. She will read it and learn how you talk and what you care about.';
        contentEl.appendChild(intro);

        if (this.feedMessage) {
            const ok = document.createElement('div');
            ok.className = 'inline-success';
            ok.textContent = this.feedMessage;
            contentEl.appendChild(ok);
        }

        const form = document.createElement('simple-form');
        form.init({
            fields: [
                { name: 'source', type: 'options', label: 'Source', options: [
                    { value: 'ollama', label: 'Ollama' },
                    { value: 'anthropic', label: 'Anthropic' },
                    { value: 'openai', label: 'OpenAI compatible' },
                ]},
                { name: 'history', type: 'file', label: 'Export file', accept: '.json,.txt,.zip' },
            ],
            values: this.feedValues,
            error: this.feedError,
            submitting: this.feeding,
            submitLabel: this.feeding ? '...' : 'Feed',
            onSubmit: () => this.feed(),
        });
        contentEl.appendChild(form);
    }

    async feed() {
        if (!this.feedValues.history || !this.feedValues.source) {
            this.feedError = 'Both fields are required.';
            this.render();
            return;
        }
        this.feeding = true;
        this.feedError = null;
        this.feedMessage = null;
        this.render();

        const result = await this.api.feedPersona(this.personaId, this.feedValues.history, this.feedValues.source);
        this.feeding = false;

        if (result.success) {
            this.feedMessage = result.message || 'History fed successfully.';
            this.feedValues = {};
            this.data = await this.api.getOversee(this.personaId);
        } else {
            this.feedError = result.error || 'Feed failed.';
        }
        this.render();
    }

    renderSettings(contentEl) {
        const p = this.persona;
        if (!p) {
            contentEl.innerHTML = '<div class="empty">Loading…</div>';
            return;
        }

        if (!this.settingsValues) {
            this.settingsValues = {
                thinking_provider: p.thinking?.provider || 'local',
                thinking_model: p.thinking?.name || '',
                thinking_url: p.thinking?.url || '',
                thinking_api_key: '',
                vision_provider: p.vision?.provider || '',
                vision_model: p.vision?.name || '',
                vision_url: p.vision?.url || '',
                vision_api_key: '',
                frontier_provider: p.frontier?.provider || '',
                frontier_model: p.frontier?.name || '',
                frontier_url: p.frontier?.url || '',
                frontier_api_key: '',
            };
        }

        const intro = document.createElement('div');
        intro.className = 'intro';
        intro.textContent = 'Models that power her. Set provider to "None" to remove her eyes or teacher. API keys are not stored in plain text — leave empty to keep the existing key.';
        contentEl.appendChild(intro);

        if (this.settingsError) {
            const err = document.createElement('div');
            err.className = 'inline-error';
            err.textContent = this.settingsError;
            contentEl.appendChild(err);
        }
        if (this.settingsMessage) {
            const ok = document.createElement('div');
            ok.className = 'inline-success';
            ok.textContent = this.settingsMessage;
            contentEl.appendChild(ok);
        }

        contentEl.appendChild(this.modelGroup('Thinking', 'thinking', false));
        contentEl.appendChild(this.modelGroup('Eyes', 'vision', true));
        contentEl.appendChild(this.modelGroup('Teacher', 'frontier', true));

        const saveRow = document.createElement('div');
        saveRow.className = 'save-row';
        const save = document.createElement('action-button');
        save.init({
            label: this.savingSettings ? '...' : 'Save',
            variant: 'primary',
            disabled: this.savingSettings,
            onClick: () => this.saveSettings(),
        });
        saveRow.appendChild(save);
        contentEl.appendChild(saveRow);
    }

    modelGroup(title, prefix, optional) {
        const group = document.createElement('div');
        group.className = 'settings-group';
        const h = document.createElement('h3');
        h.textContent = title;
        group.appendChild(h);

        const providerOptions = optional
            ? [
                { value: '', label: 'None' },
                { value: 'local', label: 'Local (Ollama)' },
                { value: 'anthropic', label: 'Anthropic' },
                { value: 'openai', label: 'OpenAI compatible' },
            ]
            : [
                { value: 'local', label: 'Local (Ollama)' },
                { value: 'anthropic', label: 'Anthropic' },
                { value: 'openai', label: 'OpenAI compatible' },
            ];

        const form = document.createElement('simple-form');
        form.init({
            fields: [
                { name: `${prefix}_provider`, type: 'options', label: 'Provider', options: providerOptions },
                { name: `${prefix}_model`, type: 'text', label: 'Model' },
                { name: `${prefix}_url`, type: 'text', label: 'URL' },
                { name: `${prefix}_api_key`, type: 'text', label: 'API key', placeholder: 'leave empty to keep existing' },
            ],
            values: this.settingsValues,
        });
        group.appendChild(form);
        return group;
    }

    async saveSettings() {
        this.savingSettings = true;
        this.settingsError = null;
        this.settingsMessage = null;
        this.render();

        const v = this.settingsValues;
        const fields = {};

        if (v.thinking_provider && v.thinking_model) {
            fields.thinking = {
                provider: v.thinking_provider,
                model: v.thinking_model,
                url: v.thinking_url || null,
                api_key: v.thinking_api_key || null,
            };
        }

        if (v.vision_provider === '') {
            fields.clear_vision = true;
        } else if (v.vision_provider && v.vision_model) {
            fields.vision = {
                provider: v.vision_provider,
                model: v.vision_model,
                url: v.vision_url || null,
                api_key: v.vision_api_key || null,
            };
        }

        if (v.frontier_provider === '') {
            fields.clear_frontier = true;
        } else if (v.frontier_provider && v.frontier_model) {
            fields.frontier = {
                provider: v.frontier_provider,
                model: v.frontier_model,
                url: v.frontier_url || null,
                api_key: v.frontier_api_key || null,
            };
        }

        const result = await this.api.updatePersona(this.personaId, fields);
        this.savingSettings = false;

        if (result.success) {
            this.settingsMessage = 'Saved.';
            this.persona = await this.api.getPersona(this.personaId);
            this.settingsValues = null;
        } else {
            this.settingsError = result.error || 'Save failed.';
        }
        this.render();
    }

    async removeRow(id) {
        const result = await this.api.controlPersona(this.personaId, [id]);
        if (result.success) {
            this.data = await this.api.getOversee(this.personaId);
            this.render();
        }
    }
}

customElements.define('inner-world', InnerWorld);
export default InnerWorld;
