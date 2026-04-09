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
            font-size: 14px;
            font-weight: 300;
            letter-spacing: 5px;
            text-transform: uppercase;
            color: var(--text-primary);
            text-align: center;
            padding-bottom: 4px;
        }
        .iw-persona-age {
            font-size: 10px;
            font-weight: 300;
            color: var(--text-muted);
            text-align: center;
            padding-bottom: 16px;
        }

        /* Sections — each a quiet chapter */
        .iw-section {
            padding: 0;
        }
        .iw-heading {
            font-size: 10px;
            font-weight: 400;
            color: var(--text-muted);
            letter-spacing: 2px;
            text-transform: uppercase;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 10px;
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

        /* Skills — small, worn tags */
        .iw-skills {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding-top: 2px;
        }
        .iw-skill {
            font-size: 10px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-subtle);
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
            background: none;
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-muted);
            font-family: var(--font);
            font-size: 10px;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            transition: color 0.2s, border-color 0.2s;
        }
        .iw-action:hover {
            color: var(--text-secondary);
            border-color: var(--border-hover);
        }
        .iw-action.iw-danger:hover {
            color: var(--destructive-text);
            border-color: var(--destructive-border);
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

    show(personaId, personaName, birthday, data) {
        this._personaId = personaId;
        this._personaName = personaName;

        // Clear previous content
        this.innerHTML = '';

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'iw-close';
        closeBtn.innerHTML = x(18);
        closeBtn.addEventListener('click', () => this._props.onExitInner());
        this.appendChild(closeBtn);

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
            btn.addEventListener('click', () => {
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
