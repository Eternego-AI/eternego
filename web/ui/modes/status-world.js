import Mode from './mode.js';

/**
 * Status World — the persona's vital state, controls, and uptime.
 *
 * Where you go to declare what the persona should be: active, sick,
 * or hibernate. Below the controls, the body's last 24 hours of
 * health-check loops, the same minute-by-minute grid as before.
 * Lifecycle (start/stop/restart) lives on inner-world; here we set
 * state, not push buttons.
 */
class StatusWorld extends Mode {
    static _css = `
        status-world {
            position: fixed;
            inset: 0;
            display: flex;
            justify-content: center;
            overflow-y: auto;
            background:
                radial-gradient(ellipse at 50% 30%, rgba(140,160,255,0.025) 0%, transparent 55%),
                var(--bg);
            opacity: 0;
            transition: opacity 0.4s var(--ease);
        }
        status-world.visible { opacity: 1; }

        status-world .sw-content {
            width: 100%;
            max-width: 760px;
            padding: 50px 32px 100px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        status-world .sw-head {
            display: flex;
            flex-direction: column;
            gap: 8px;
            text-align: center;
        }
        status-world .sw-name {
            font-size: 18px;
            font-weight: 400;
            letter-spacing: 5px;
            text-transform: uppercase;
            color: var(--warm-text);
        }
        status-world .sw-tagline {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.7;
        }

        status-world .sw-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        status-world .sw-section-head {
            font-size: 11px;
            font-weight: 500;
            color: var(--accent-text);
            letter-spacing: 2px;
            text-transform: uppercase;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-default);
        }

        status-world .sw-state-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        status-world .sw-state-btn {
            flex: 1;
            min-width: 140px;
            padding: 16px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--text-body);
            font-family: var(--font);
            font-size: 12px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            transition: background 0.2s, border-color 0.2s, color 0.2s;
        }
        status-world .sw-state-btn:hover { border-color: var(--border-hover); color: var(--text-primary); }
        status-world .sw-state-btn.current.active {
            background: var(--vital-bg);
            border-color: var(--vital-border);
            color: var(--vital-text);
        }
        status-world .sw-state-btn.current.sick {
            background: var(--destructive-bg);
            border-color: var(--destructive-border);
            color: var(--destructive-text);
        }
        status-world .sw-state-btn.current.hibernate {
            background: var(--surface-active);
            border-color: var(--border-hover);
            color: var(--text-primary);
        }
        status-world .sw-state-meaning {
            font-size: 10px;
            font-weight: 400;
            text-transform: none;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }
        status-world .sw-state-btn.current .sw-state-meaning { color: inherit; opacity: 0.85; }

        status-world .sw-legend {
            display: flex;
            justify-content: center;
            gap: 20px;
            font-size: 10px;
            color: var(--text-muted);
            padding-top: 4px;
        }
        status-world .sw-legend-item { display: inline-flex; align-items: center; gap: 6px; }
        status-world .sw-legend-swatch { width: 10px; height: 10px; border-radius: 2px; }
        status-world .sw-legend-swatch.well { background: var(--accent); }
        status-world .sw-legend-swatch.trouble { background: var(--destructive-text); }
        status-world .sw-legend-swatch.off { background: var(--text-ghost); }

        status-world .sw-grid {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 16px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
        }
        status-world .sw-row { display: flex; align-items: center; gap: 10px; }
        status-world .sw-row-label {
            flex: 0 0 56px;
            font-size: 9px;
            color: var(--text-dim);
            font-variant-numeric: tabular-nums;
            letter-spacing: 0.5px;
            text-align: right;
        }
        status-world .sw-row.current .sw-row-label { color: var(--text-secondary); }
        status-world .sw-cells { flex: 1; display: flex; gap: 1px; min-width: 0; }
        status-world .sw-cell {
            flex: 1;
            height: 14px;
            border-radius: 1px;
            background: var(--text-ghost);
            opacity: 0.4;
            cursor: help;
            transition: opacity 0.1s, transform 0.1s;
            min-width: 0;
        }
        status-world .sw-cell:hover { opacity: 1; transform: scaleY(1.4); }
        status-world .sw-cell.well { background: var(--accent); opacity: 0.7; }
        status-world .sw-cell.trouble { background: var(--destructive-text); opacity: 0.85; }

        status-world .sw-summary {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.7;
            text-align: center;
            padding-top: 8px;
        }
        status-world .sw-empty {
            text-align: center;
            color: var(--text-dim);
            font-size: 12px;
            padding: 60px 0;
        }
    `;

    // init({ api, signals })
    build() {
        this.constructor._injectStyles();
    }

    setPersona(personaId) {
        this._personaId = personaId;
    }

    activate() {
        requestAnimationFrame(() => this.classList.add('visible'));
        this._render();
        if (this._props.signals && !this._signalHandler) {
            this._signalHandler = (e) => this._onSignals(e.detail);
            this._props.signals.addEventListener('update', this._signalHandler);
        }
    }

    deactivate() {
        this.classList.remove('visible');
        if (this._signalHandler && this._props.signals) {
            this._props.signals.removeEventListener('update', this._signalHandler);
            this._signalHandler = null;
        }
    }

    _onSignals(signals) {
        if (!this._personaId) return;
        for (const sig of signals) {
            const title = (sig.title || '').toLowerCase();
            const p = sig.details?.persona || sig.details?.persona_id || '';
            const pid = typeof p === 'object' ? (p.id || '') : String(p);
            if (!pid.includes(this._personaId)) continue;
            if (title === 'health checked' || title === 'persona became sick' || title === 'persona updated') {
                this._render();
                return;
            }
        }
    }

    async _render() {
        this.innerHTML = '';
        const content = document.createElement('div');
        content.className = 'sw-content';
        this.appendChild(content);

        if (!this._personaId) {
            const empty = document.createElement('div');
            empty.className = 'sw-empty';
            empty.textContent = 'No persona selected.';
            content.appendChild(empty);
            return;
        }

        const head = document.createElement('div');
        head.className = 'sw-head';
        const nameEl = document.createElement('div');
        nameEl.className = 'sw-name';
        nameEl.textContent = '—';
        const taglineEl = document.createElement('div');
        taglineEl.className = 'sw-tagline';
        taglineEl.textContent = "Their state, their controls, their last 24 hours of body.";
        head.appendChild(nameEl);
        head.appendChild(taglineEl);
        content.appendChild(head);

        const stateSection = document.createElement('div');
        stateSection.className = 'sw-section';
        const stateHead = document.createElement('div');
        stateHead.className = 'sw-section-head';
        stateHead.textContent = 'State';
        stateSection.appendChild(stateHead);
        const stateRow = document.createElement('div');
        stateRow.className = 'sw-state-row';
        stateSection.appendChild(stateRow);
        content.appendChild(stateSection);

        const uptimeSection = document.createElement('div');
        uptimeSection.className = 'sw-section';
        const uptimeHead = document.createElement('div');
        uptimeHead.className = 'sw-section-head';
        uptimeHead.textContent = 'Last 24 hours';
        uptimeSection.appendChild(uptimeHead);
        const legend = document.createElement('div');
        legend.className = 'sw-legend';
        legend.innerHTML = `
            <span class="sw-legend-item"><span class="sw-legend-swatch well"></span>well</span>
            <span class="sw-legend-item"><span class="sw-legend-swatch trouble"></span>trouble</span>
            <span class="sw-legend-item"><span class="sw-legend-swatch off"></span>not running</span>
        `;
        uptimeSection.appendChild(legend);
        const grid = document.createElement('div');
        grid.className = 'sw-grid';
        uptimeSection.appendChild(grid);
        const summary = document.createElement('div');
        summary.className = 'sw-summary';
        summary.textContent = 'Reading body…';
        uptimeSection.appendChild(summary);
        content.appendChild(uptimeSection);

        const [persona, diagnosis] = await Promise.all([
            this._props.api.fetchPersona(this._personaId),
            this._props.api.fetchDiagnose(this._personaId),
        ]);

        if (persona) nameEl.textContent = persona.name || '—';

        const currentState = (diagnosis && diagnosis.status) || (persona && persona.status) || 'active';
        this._renderStateControls(stateRow, currentState);

        if (!diagnosis || !diagnosis.uptime || !diagnosis.uptime.rows) {
            grid.innerHTML = '';
            const empty = document.createElement('div');
            empty.className = 'sw-empty';
            empty.textContent = 'No body history yet.';
            grid.appendChild(empty);
            summary.textContent = '';
            return;
        }

        grid.innerHTML = '';
        diagnosis.uptime.rows.forEach((row, idx) => grid.appendChild(this._buildRow(row, idx)));
        summary.textContent = this._summary(diagnosis.uptime.rows);
    }

    _renderStateControls(row, currentState) {
        row.innerHTML = '';
        const states = [
            { id: 'active', meaning: 'present, listening' },
            { id: 'sick', meaning: 'something is wrong' },
            { id: 'hibernate', meaning: 'resting, not reachable' },
        ];
        for (const s of states) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'sw-state-btn';
            if (s.id === currentState) btn.classList.add('current', s.id);
            btn.innerHTML = `<span>${s.id}</span><span class="sw-state-meaning">${s.meaning}</span>`;
            btn.addEventListener('click', () => this._setState(s.id, currentState));
            row.appendChild(btn);
        }
    }

    async _setState(next, current) {
        if (next === current) return;
        try {
            await this._props.api.updatePersona(this._personaId, { status: next });
        } catch {}
        this._render();
    }

    _buildRow(row, idx) {
        const el = document.createElement('div');
        el.className = 'sw-row';
        if (idx === 0) el.classList.add('current');

        const label = document.createElement('div');
        label.className = 'sw-row-label';
        label.textContent = this._fmt(row.to);
        el.appendChild(label);

        const cells = document.createElement('div');
        cells.className = 'sw-cells';
        for (const cell of row.cells) {
            const c = document.createElement('div');
            c.className = 'sw-cell';
            if (cell.tick) c.classList.add(cell.fault ? 'trouble' : 'well');
            const time = this._fmt(cell.at);
            const parts = [time];
            if (!cell.tick) parts.push('not running');
            else if (cell.fault) parts.push(`fault — ${(cell.providers || []).join(', ') || 'unknown'}`);
            else parts.push('well');
            c.title = parts.join(' — ');
            cells.appendChild(c);
        }
        el.appendChild(cells);
        return el;
    }

    _fmt(iso) {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return iso;
        return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }

    _summary(rows) {
        let totalCells = 0;
        let runningCells = 0;
        let troubledCells = 0;
        const providers = new Map();
        for (const row of rows) {
            for (const cell of row.cells) {
                totalCells++;
                if (cell.tick) {
                    runningCells++;
                    if (cell.fault) {
                        troubledCells++;
                        for (const p of cell.providers || []) providers.set(p, (providers.get(p) || 0) + 1);
                    }
                }
            }
        }
        if (runningCells === 0) return 'No traces in the last 24 hours.';
        const offCells = totalCells - runningCells;
        const offHrs = Math.round(offCells / 60);
        const offText = offCells > 0 ? `${offHrs > 0 ? offHrs + 'h' : offCells + 'm'} not running` : '';
        if (troubledCells === 0) {
            return offText
                ? `${runningCells} clean loops, ${offText}.`
                : `${runningCells} clean loops in the last 24 hours.`;
        }
        const top = [...providers.entries()].sort((a, b) => b[1] - a[1]).map(p => p[0]);
        const provText = top.length ? ` — ${top.join(', ')} pressed` : '';
        return `${runningCells - troubledCells} clean of ${runningCells} loops${offText ? ', ' + offText : ''}. ${troubledCells} fault${troubledCells === 1 ? '' : 's'}${provText}.`;
    }
}

customElements.define('status-world', StatusWorld);
export default StatusWorld;
