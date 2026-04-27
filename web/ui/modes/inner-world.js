import Mode from './mode.js';
import { moon, square, refreshCw, trash2, upload, x, play, download } from '../icons.js';

/**
 * Inner World — the window into a persona's consciousness.
 *
 * Not a dashboard. Not a settings page. You are reading a being's
 * journal: what it learned about you, what it observed, what it
 * remembers, what it can do.
 */
class InnerWorld extends Mode {
    static _css = `
        inner-world {
            position: fixed;
            inset: 0;
            display: flex;
            justify-content: center;
            overflow-y: auto;
            background: rgba(5, 5, 8, 0.97);
            opacity: 0;
            transition: opacity 0.4s var(--ease);
        }
        inner-world.visible { opacity: 1; }

        /* Content — the journal itself */
        .iw-content {
            width: 100%;
            max-width: 900px;
            padding: 50px 40px 80px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        /* Knowledge grid — two columns for the main sections */
        .iw-knowledge {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px 40px;
        }

        /* Close — barely there, top-right */
        .iw-close {
            position: fixed;
            top: 20px;
            right: 24px;
            z-index: 1;
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 8px;
            line-height: 0;
            transition: color 0.2s;
        }
        .iw-close:hover { color: var(--text-body); }

        /* Persona name — quiet presence at the top */
        .iw-persona-name {
            font-size: 18px;
            font-weight: 400;
            letter-spacing: 5px;
            text-transform: uppercase;
            color: var(--warm-text);
            text-align: center;
            padding-bottom: 6px;
        }
        .iw-persona-age {
            font-size: 11px;
            font-weight: 400;
            color: var(--text-secondary);
            text-align: center;
            padding-bottom: 16px;
        }

        /* Sections — each a quiet chapter */
        .iw-section {
            padding: 0;
        }
        .iw-heading {
            font-size: 11px;
            font-weight: 500;
            color: var(--accent-text);
            letter-spacing: 2px;
            text-transform: uppercase;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-default);
            margin-bottom: 12px;
        }

        /* Knowledge entries — thoughts written in dim ink */
        .iw-entry {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 13px;
            color: var(--text-body);
            line-height: 1.7;
            padding: 5px 0;
        }
        .iw-entry-text { flex: 1; }
        .iw-entry-rm {
            flex-shrink: 0;
            background: none;
            border: none;
            color: var(--text-dim);
            font-size: 14px;
            cursor: pointer;
            padding: 0 4px;
            line-height: 1.7;
            transition: color 0.2s;
        }
        .iw-entry-rm:hover { color: var(--destructive-text); }

        .iw-empty {
            font-size: 11px;
            color: var(--text-dim);
            font-style: italic;
            padding: 2px 0;
        }

        /* Destiny entries — scheduled whispers */
        .iw-destiny-entry {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.7;
            padding: 4px 0;
            font-variant-numeric: tabular-nums;
        }
        .iw-destiny-name {
            flex: 1;
        }
        .iw-destiny-entry .iw-entry-rm {
            color: var(--text-dim);
        }

        /* History entries — faded echoes of past days */
        .iw-history-entry {
            font-size: 10px;
            color: var(--text-dim);
            line-height: 1.8;
            padding: 1px 0;
        }

        /* Brain — the persona's models, what they think with */
        .iw-brain {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .iw-brain-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            transition: border-color 0.2s, background 0.2s;
        }
        .iw-brain-row:hover { border-color: var(--border-hover); }
        .iw-brain-role {
            flex: 0 0 90px;
            font-size: 11px;
            font-weight: 500;
            color: var(--accent-text);
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        .iw-brain-model {
            flex: 1;
            font-size: 13px;
            color: var(--text-body);
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .iw-brain-provider {
            font-size: 11px;
            color: var(--text-muted);
            margin-left: 6px;
        }
        .iw-brain-empty {
            color: var(--text-dim);
            font-style: italic;
        }
        .iw-brain-actions {
            display: flex;
            gap: 4px;
        }
        .iw-brain-btn {
            background: none;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: 11px;
            padding: 4px 10px;
            cursor: pointer;
            transition: color 0.2s, border-color 0.2s, background 0.2s;
        }
        .iw-brain-btn:hover {
            color: var(--text-primary);
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }
        .iw-brain-btn.iw-brain-clear:hover {
            color: var(--destructive-text);
            border-color: var(--destructive-border);
            background: var(--destructive-bg);
        }

        /* Brain editor — modal form */
        .iw-edit {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .iw-edit-title {
            font-size: 14px;
            font-weight: 500;
            color: var(--warm-text);
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        .iw-edit-hint {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.6;
        }
        .iw-edit-providers {
            display: flex;
            gap: 6px;
        }
        .iw-edit-provider {
            flex: 1;
            padding: 10px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: 12px;
            text-align: center;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s, color 0.2s;
        }
        .iw-edit-provider:hover {
            border-color: var(--border-hover);
            color: var(--text-primary);
        }
        .iw-edit-provider.selected {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        .iw-edit-input {
            padding: 10px 12px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-body);
            font-family: var(--font);
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }
        .iw-edit-input:focus { border-color: var(--accent-border); }
        .iw-edit-nav {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            padding-top: 4px;
        }
        .iw-edit-btn {
            padding: 8px 18px;
            background: var(--surface-hover);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-body);
            font-family: var(--font);
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s, color 0.2s;
        }
        .iw-edit-btn:hover { color: var(--text-primary); border-color: var(--border-hover); }
        .iw-edit-btn.primary {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        .iw-edit-btn.primary:hover {
            background: var(--accent-hover-bg);
            border-color: var(--accent-hover-border);
            color: #fff;
        }
        .iw-edit-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .iw-edit-error {
            padding: 10px 12px;
            background: var(--destructive-bg);
            border: 1px solid var(--destructive-border);
            border-radius: var(--radius-md);
            color: var(--destructive-text);
            font-size: 12px;
        }

        /* Vitals — the body, three lenses */
        .iw-vitals {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .iw-vitals-explain {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.7;
        }
        .iw-vitals-explain strong { color: var(--text-body); font-weight: 500; }
        .iw-vitals-explain .iw-vitals-state {
            text-transform: lowercase;
            letter-spacing: 0.5px;
        }
        .iw-vitals-explain .iw-vitals-state.sick { color: var(--destructive-text); }
        .iw-vitals-explain .iw-vitals-state.active { color: var(--accent-text); }
        .iw-vitals-explain .iw-vitals-state.hibernate { color: var(--text-muted); }
        .iw-vitals-strip {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .iw-vitals-strip-title {
            font-size: 9px;
            color: var(--text-muted);
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        .iw-vitals-bars {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 4px;
            height: 56px;
            padding: 4px 0;
        }
        .iw-vitals-bars.iw-vitals-week { gap: 12px; height: 72px; }
        .iw-vitals-bars.iw-vitals-day { gap: 3px; }
        .iw-vitals-bars.iw-vitals-hour { gap: 2px; height: 44px; }
        .iw-vitals-tick {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: stretch;
            gap: 6px;
            cursor: help;
            min-width: 0;
        }
        .iw-vitals-bar-track {
            flex: 1;
            display: flex;
            align-items: flex-end;
        }
        .iw-vitals-bar {
            width: 100%;
            border-radius: var(--radius-sm) var(--radius-sm) 2px 2px;
            background: var(--accent);
            opacity: 0.8;
            transition: opacity 0.15s, background 0.15s;
            min-height: 3px;
        }
        .iw-vitals-tick:hover .iw-vitals-bar { opacity: 1; }
        .iw-vitals-bar.troubled { background: var(--destructive-text); }
        .iw-vitals-bar.empty {
            background: var(--text-ghost);
            opacity: 0.5;
        }
        .iw-vitals-label {
            font-size: 9px;
            color: var(--text-dim);
            letter-spacing: 0.5px;
            text-align: center;
            font-variant-numeric: tabular-nums;
            text-transform: uppercase;
        }
        .iw-vitals-tick.now .iw-vitals-label { color: var(--text-secondary); }
        .iw-vitals-axis {
            display: flex;
            justify-content: space-between;
            font-size: 9px;
            color: var(--text-dim);
            font-variant-numeric: tabular-nums;
            letter-spacing: 0.5px;
            padding-top: 2px;
        }
        .iw-vitals-summary {
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.7;
            padding-top: 4px;
        }

        /* Skills — small, worn tags */
        .iw-skills {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding-top: 2px;
        }
        .iw-skill {
            font-size: 11px;
            color: var(--warm-text);
            background: var(--warm-bg);
            border: 1px solid var(--warm-border);
            border-radius: var(--radius-md);
            padding: 4px 10px;
            letter-spacing: 0.5px;
        }

        /* Actions — clear, findable */
        .iw-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .iw-action {
            flex: 1;
            min-width: 80px;
            padding: 14px 0;
            background: var(--surface-recessed);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-body);
            font-family: var(--font);
            font-size: 12px;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            transition: color 0.2s, border-color 0.2s, background 0.2s;
        }
        .iw-action:hover {
            color: var(--text-primary);
            border-color: var(--accent-border);
            background: var(--accent-bg);
        }
        .iw-action.iw-danger:hover {
            color: var(--destructive-text);
            border-color: var(--destructive-border);
            background: var(--destructive-bg);
        }
        .iw-action-icon { display: flex; line-height: 0; }

        /* Teach — compact, unobtrusive */
        .iw-teach {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .iw-teach select {
            flex: 1;
            padding: 6px 10px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-muted);
            font-family: var(--font);
            font-size: 10px;
            outline: none;
        }
        .iw-teach label {
            cursor: pointer;
            display: flex;
            align-items: center;
            padding: 6px 10px;
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-muted);
            font-size: 10px;
            transition: border-color 0.2s, color 0.2s;
        }
        .iw-teach label:hover {
            border-color: var(--border-hover);
            color: var(--text-secondary);
        }
    `;

    build() {
        this.constructor._injectStyles();
        this._personaId = null;
        this._personaName = null;
    }

    show(personaId, personaName, birthday, data, persona) {
        this._personaId = personaId;
        this._personaName = personaName;
        this._persona = persona || null;

        // Clear previous content
        this.innerHTML = '';

        // Content area
        const content = document.createElement('div');
        content.className = 'iw-content';
        this.appendChild(content);

        // Persona name at top
        const nameEl = document.createElement('div');
        nameEl.className = 'iw-persona-name';
        nameEl.textContent = personaName || 'persona';
        content.appendChild(nameEl);

        // Age indicator
        if (birthday) {
            const born = new Date(birthday);
            if (!isNaN(born.getTime())) {
                const days = Math.floor((Date.now() - born.getTime()) / 86400000);
                const ageEl = document.createElement('div');
                ageEl.className = 'iw-persona-age';
                ageEl.textContent = `born ${days} day${days !== 1 ? 's' : ''} ago`;
                content.appendChild(ageEl);
            }
        }

        // Render based on data availability
        if (data) {
            this._render(content, data);
        } else {
            this._renderStopped(content);
        }
    }

    activate() {
        requestAnimationFrame(() => this.classList.add('visible'));
    }

    deactivate() {
        this.classList.remove('visible');
    }

    _renderStopped(content) {
        const msg = document.createElement('div');
        msg.style.cssText = 'text-align:center;color:var(--text-dim);font-size:13px;padding:40px 0;';
        msg.textContent = 'This persona is not running.';
        content.appendChild(msg);

        // Only show Start and Delete
        const section = document.createElement('div');
        section.className = 'iw-section';
        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'Actions';
        section.appendChild(heading);

        const row = document.createElement('div');
        row.className = 'iw-actions';

        for (const def of [
            { id: 'start', icon: play(13), label: 'Start' },
            { id: 'export', icon: download(13), label: 'Export' },
            { id: 'delete', icon: trash2(13), label: 'Delete', danger: true },
        ]) {
            const btn = document.createElement('button');
            btn.className = 'iw-action' + (def.danger ? ' iw-danger' : '');
            btn.innerHTML = `<span class="iw-action-icon">${def.icon}</span>${def.label}`;
            btn.addEventListener('click', async () => {
                if (def.id === 'export') {
                    btn.disabled = true;
                    btn.textContent = 'Exporting...';
                    await this._props.api.exportPersona(this._personaId);
                    btn.disabled = false;
                    btn.innerHTML = `<span class="iw-action-icon">${def.icon}</span>${def.label}`;
                    return;
                }
                const msg = {
                    start: 'Start this persona?',
                    delete: 'Permanently delete this persona and all its data?',
                };
                if (confirm(msg[def.id])) {
                    this._props.api.actionPersona(this._personaId, def.id);
                    if (def.id === 'start') this._props.onExitInner();
                }
            });
            row.appendChild(btn);
        }

        section.appendChild(row);
        content.appendChild(section);
    }

    _render(content, data) {
        // Brain — what they think with
        if (this._persona) this._renderBrain(content);

        // Knowledge grid — two columns
        const grid = document.createElement('div');
        grid.className = 'iw-knowledge';
        this._renderKnowledge(grid, 'About You', data.person);
        this._renderKnowledge(grid, 'How You Are', data.traits);
        this._renderKnowledge(grid, 'What You Want', data.wishes);
        this._renderKnowledge(grid, 'What\'s Hard', data.struggles);
        content.appendChild(grid);

        // Destiny and History side by side too
        const bottom = document.createElement('div');
        bottom.className = 'iw-knowledge';
        if (data.destiny) this._renderDestiny(bottom, data.destiny);
        if (data.history) this._renderHistory(bottom, data.history);
        if (bottom.children.length) content.appendChild(bottom);

        // Skills — what the persona can do
        if (data.skills) {
            this._renderSkills(content, data.skills);
        }

        // Teach — feed knowledge from other conversations
        this._renderTeach(content);

        // Actions — sleep, stop, restart, delete
        this._renderActions(content);
    }

    _renderKnowledge(container, title, items) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = title;
        section.appendChild(heading);

        const facts = (items || []).filter(i => i.content?.trim());
        if (facts.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'iw-empty';
            empty.textContent = 'Nothing yet';
            section.appendChild(empty);
        } else {
            for (const item of facts) {
                const entry = document.createElement('div');
                entry.className = 'iw-entry';

                const text = document.createElement('span');
                text.className = 'iw-entry-text';
                text.textContent = item.content;

                const rm = document.createElement('button');
                rm.className = 'iw-entry-rm';
                rm.textContent = '\u00d7';
                rm.addEventListener('click', async () => {
                    const result = await this._props.api.controlPersona(this._personaId, [item.id]);
                    if (result) {
                        entry.remove();
                        if (!section.querySelector('.iw-entry')) {
                            const empty = document.createElement('div');
                            empty.className = 'iw-empty';
                            empty.textContent = 'Nothing yet';
                            section.appendChild(empty);
                        }
                    }
                });

                entry.appendChild(text);
                entry.appendChild(rm);
                section.appendChild(entry);
            }
        }
        container.appendChild(section);
    }

    _parseDestiny(filename) {
        const base = filename.replace(/\.md$/, '');
        const parts = base.split('-');
        // Format: {type}-{year}-{month}-{day}-{hour}-{minute}-{timestamp}
        if (parts.length < 6) return filename;
        const type = parts[0];
        const month = parseInt(parts[2], 10);
        const day = parseInt(parts[3], 10);
        const hour = parseInt(parts[4], 10);
        const minute = parseInt(parts[5], 10);
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        const monthName = months[month - 1] || '';
        const h = hour % 12 || 12;
        const ampm = hour < 12 ? 'am' : 'pm';
        const mm = minute > 0 ? `:${String(minute).padStart(2, '0')}` : '';
        return `${type} \u2014 ${monthName} ${day}, ${h}${mm}${ampm}`;
    }

    _renderDestiny(container, entries) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'Destiny';
        section.appendChild(heading);

        if (!entries.length) {
            const empty = document.createElement('div');
            empty.className = 'iw-empty';
            empty.textContent = 'No scheduled entries';
            section.appendChild(empty);
        } else {
            for (const item of entries) {
                const entry = document.createElement('div');
                entry.className = 'iw-destiny-entry';

                const name = document.createElement('span');
                name.className = 'iw-destiny-name';
                const raw = item.content || item.id || '';
                name.textContent = raw.endsWith('.md') ? this._parseDestiny(raw) : raw;

                const rm = document.createElement('button');
                rm.className = 'iw-entry-rm';
                rm.textContent = '\u00d7';
                rm.addEventListener('click', async () => {
                    const result = await this._props.api.controlPersona(this._personaId, [item.id]);
                    if (result) {
                        entry.remove();
                        if (!section.querySelector('.iw-destiny-entry')) {
                            const empty = document.createElement('div');
                            empty.className = 'iw-empty';
                            empty.textContent = 'Nothing yet';
                            section.appendChild(empty);
                        }
                    }
                });

                entry.appendChild(name);
                entry.appendChild(rm);
                section.appendChild(entry);
            }
        }
        container.appendChild(section);
    }

    _renderHistory(container, entries) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'History';
        section.appendChild(heading);

        if (!entries.length) {
            const empty = document.createElement('div');
            empty.className = 'iw-empty';
            empty.textContent = 'No archived conversations';
            section.appendChild(empty);
        } else {
            for (const item of entries) {
                const entry = document.createElement('div');
                entry.className = 'iw-history-entry';
                entry.textContent = item.content || item.id;
                section.appendChild(entry);
            }
        }
        container.appendChild(section);
    }

    _renderBrain(container) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'Brain';
        section.appendChild(heading);

        const list = document.createElement('div');
        list.className = 'iw-brain';

        const roles = [
            { key: 'thinking', label: 'Thinking', required: true },
            { key: 'vision', label: 'Vision', required: false },
            { key: 'frontier', label: 'Frontier', required: false },
        ];
        for (const r of roles) {
            list.appendChild(this._renderBrainRow(r));
        }

        section.appendChild(list);
        container.appendChild(section);
    }

    _renderBrainRow({ key, label, required }) {
        const model = this._persona?.[key] || null;
        const row = document.createElement('div');
        row.className = 'iw-brain-row';

        const role = document.createElement('div');
        role.className = 'iw-brain-role';
        role.textContent = label;
        row.appendChild(role);

        const modelEl = document.createElement('div');
        modelEl.className = 'iw-brain-model';
        if (model) {
            modelEl.appendChild(document.createTextNode(model.name || ''));
            const provider = document.createElement('span');
            provider.className = 'iw-brain-provider';
            provider.textContent = `· ${model.provider || 'local'}`;
            modelEl.appendChild(provider);
        } else {
            const empty = document.createElement('span');
            empty.className = 'iw-brain-empty';
            empty.textContent = '— not set';
            modelEl.appendChild(empty);
        }
        row.appendChild(modelEl);

        const actions = document.createElement('div');
        actions.className = 'iw-brain-actions';

        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'iw-brain-btn';
        editBtn.textContent = model ? 'edit' : 'add';
        editBtn.addEventListener('click', () => this._openBrainEditor(key, label, model));
        actions.appendChild(editBtn);

        if (model && !required) {
            const clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'iw-brain-btn iw-brain-clear';
            clearBtn.textContent = '×';
            clearBtn.title = `Remove ${label.toLowerCase()} model`;
            clearBtn.addEventListener('click', () => this._clearBrainModel(key, label));
            actions.appendChild(clearBtn);
        }

        row.appendChild(actions);
        return row;
    }

    async _clearBrainModel(key, label) {
        if (!confirm(`Remove the ${label.toLowerCase()} model?`)) return;
        const fields = key === 'vision' ? { clear_vision: true } : { clear_frontier: true };
        await this._props.api.updatePersona(this._personaId, fields);
        this._refreshAfterUpdate();
    }

    async _refreshAfterUpdate() {
        try {
            await this._props.api.fetchPersonas();
            const persona = await this._props.api.fetchPersona(this._personaId);
            this._persona = persona;
            const data = await this._props.api.fetchOversee(this._personaId);
            this.innerHTML = '';
            this.show(this._personaId, persona?.name || this._personaName, persona?.birthday || null, data, persona);
        } catch {}
    }

    _openBrainEditor(key, label, current) {
        const modal = document.createElement('modal-layout');
        modal.init({});
        document.body.appendChild(modal);

        const wrap = document.createElement('div');
        wrap.className = 'iw-edit';

        const title = document.createElement('div');
        title.className = 'iw-edit-title';
        title.textContent = `${label} model`;
        wrap.appendChild(title);

        const hint = document.createElement('p');
        hint.className = 'iw-edit-hint';
        hint.textContent = key === 'thinking'
            ? 'The persona\'s core cognition. Saving will restart them so the new model takes effect.'
            : (key === 'vision'
                ? 'Used to interpret images. Saving will restart them so the new model takes effect.'
                : 'A teacher reached when the thinking model hits a wall. Saving will restart them.');
        wrap.appendChild(hint);

        const providers = document.createElement('div');
        providers.className = 'iw-edit-providers';
        const provDefs = [
            { id: '', label: 'Local (Ollama)' },
            { id: 'anthropic', label: 'Claude' },
            { id: 'openai', label: 'OpenAI-compatible' },
        ];

        const state = {
            provider: current?.provider || null,
            url: current?.url || '',
            model: current?.name || '',
            api_key: '',
        };

        const urlField = document.createElement('input');
        urlField.className = 'iw-edit-input';
        urlField.placeholder = 'URL';
        urlField.value = state.url;

        const modelField = document.createElement('input');
        modelField.className = 'iw-edit-input';
        modelField.placeholder = 'Model name (e.g. claude-sonnet-4-20250514)';
        modelField.value = state.model;

        const keyField = document.createElement('input');
        keyField.className = 'iw-edit-input';
        keyField.type = 'password';
        keyField.placeholder = 'API key';

        const error = document.createElement('div');
        error.className = 'iw-edit-error';
        error.style.display = 'none';

        const renderProviders = () => {
            providers.innerHTML = '';
            for (const p of provDefs) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'iw-edit-provider';
                if ((state.provider || '') === p.id) btn.classList.add('selected');
                btn.textContent = p.label;
                btn.addEventListener('click', () => {
                    state.provider = p.id || null;
                    renderProviders();
                    keyField.style.display = state.provider ? '' : 'none';
                });
                providers.appendChild(btn);
            }
        };
        renderProviders();
        keyField.style.display = state.provider ? '' : 'none';

        wrap.appendChild(providers);
        wrap.appendChild(urlField);
        wrap.appendChild(modelField);
        wrap.appendChild(keyField);
        wrap.appendChild(error);

        const nav = document.createElement('div');
        nav.className = 'iw-edit-nav';
        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'iw-edit-btn';
        cancel.textContent = 'Cancel';
        cancel.addEventListener('click', () => modal.remove());
        const save = document.createElement('button');
        save.type = 'button';
        save.className = 'iw-edit-btn primary';
        save.textContent = 'Save';
        save.addEventListener('click', async () => {
            error.style.display = 'none';
            const name = modelField.value.trim();
            if (!name) { error.textContent = 'Model name is required.'; error.style.display = ''; return; }
            const url = urlField.value.trim();
            const apiKey = keyField.value.trim();
            if (state.provider && !apiKey) {
                error.textContent = 'API key required for remote providers.';
                error.style.display = '';
                return;
            }
            const fields = {};
            const payload = { url, model: name, provider: state.provider };
            if (state.provider) payload.api_key = apiKey;
            fields[key] = payload;
            save.disabled = true;
            cancel.disabled = true;
            save.textContent = 'Saving…';
            const result = await this._props.api.updatePersona(this._personaId, fields);
            if (result && result.error) {
                error.textContent = result.error;
                error.style.display = '';
                save.disabled = false;
                cancel.disabled = false;
                save.textContent = 'Save';
                return;
            }
            modal.remove();
            this._refreshAfterUpdate();
        });
        nav.appendChild(cancel);
        nav.appendChild(save);
        wrap.appendChild(nav);

        modal.setContent(wrap);
        setTimeout(() => modelField.focus(), 60);
    }

    _renderSkills(container, skills) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'Skills';
        section.appendChild(heading);

        if (!skills.length) {
            const empty = document.createElement('div');
            empty.className = 'iw-empty';
            empty.textContent = 'No skills yet';
            section.appendChild(empty);
        } else {
            const tags = document.createElement('div');
            tags.className = 'iw-skills';
            for (const skill of skills) {
                const tag = document.createElement('span');
                tag.className = 'iw-skill';
                tag.textContent = typeof skill === 'string' ? skill : (skill.name || skill.id || '');
                tags.appendChild(tag);
            }
            section.appendChild(tags);
        }
        container.appendChild(section);
    }

    _renderTeach(container) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'Teach';
        section.appendChild(heading);

        const row = document.createElement('div');
        row.className = 'iw-teach';

        row.innerHTML = `
            <select>
                <option value="claude">Claude export</option>
                <option value="chatgpt">ChatGPT export</option>
                <option value="grok">Grok export</option>
            </select>
            <label>
                ${upload(12)} <span style="margin-left:4px;">Upload</span>
                <input type="file" accept=".json" style="display:none;">
            </label>
        `;

        const fileInput = row.querySelector('input[type=file]');
        const sourceSelect = row.querySelector('select');
        fileInput.addEventListener('change', () => {
            if (!fileInput.files.length) return;
            const file = fileInput.files[0];
            const source = sourceSelect.value;
            this._props.api.feedPersona(this._personaId, file, source);
            fileInput.value = '';
        });

        section.appendChild(row);
        container.appendChild(section);
    }

    _renderActions(container) {
        const section = document.createElement('div');
        section.className = 'iw-section';

        const heading = document.createElement('div');
        heading.className = 'iw-heading';
        heading.textContent = 'Actions';
        section.appendChild(heading);

        const row = document.createElement('div');
        row.className = 'iw-actions';

        const defs = [
            { id: 'start',   icon: play(13),       label: 'Start' },
            { id: 'sleep',   icon: moon(13),       label: 'Sleep' },
            { id: 'stop',    icon: square(13),      label: 'Stop' },
            { id: 'restart', icon: refreshCw(13),   label: 'Restart' },
            { id: 'export',  icon: download(13),    label: 'Export' },
            { id: 'delete',  icon: trash2(13),      label: 'Delete', danger: true },
        ];

        const confirmMessages = {
            sleep:   'The persona will consolidate conversations into knowledge and grow. This may take a moment.',
            stop:    'This will close all channels and stop the persona.',
            restart: 'This will restart the persona, closing and reopening all channels.',
            delete:  'Permanently delete this persona and all its data? This cannot be undone.',
        };

        for (const def of defs) {
            const btn = document.createElement('button');
            btn.className = 'iw-action' + (def.danger ? ' iw-danger' : '');
            btn.innerHTML = `<span class="iw-action-icon">${def.icon}</span>${def.label}`;
            btn.addEventListener('click', async () => {
                if (def.id === 'export') {
                    btn.disabled = true;
                    btn.textContent = 'Exporting...';
                    await this._props.api.exportPersona(this._personaId);
                    btn.disabled = false;
                    btn.innerHTML = `<span class="iw-action-icon">${def.icon}</span>${def.label}`;
                    return;
                }
                if (confirm(confirmMessages[def.id])) {
                    this._props.api.actionPersona(this._personaId, def.id);
                }
            });
            row.appendChild(btn);
        }

        section.appendChild(row);
        container.appendChild(section);
    }
}

customElements.define('inner-world', InnerWorld);
export default InnerWorld;
