import World from './world.js';
import '../../platform/elements/action-button.js';
import '../../platform/elements/status-dot.js';
import '../../platform/elements/input-text.js';

class StatusWorld extends World {
    static _styled = false;
    static _css = `
        status-world {
            display: flex;
            flex-direction: column;
            height: 100%;
            min-height: 0;
            padding: var(--space-xl);
            gap: var(--space-xl);
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            overflow: hidden;
        }
        status-world .bar {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            padding: var(--space-md) var(--space-lg);
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
        }
        status-world .bar .name {
            font-size: var(--text-md);
            color: var(--warm-text);
            font-weight: 500;
        }
        status-world .bar .label {
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-muted);
        }
        status-world .states {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: var(--space-sm);
        }
        status-world .state {
            display: flex;
            flex-direction: column;
            align-items: stretch;
            gap: var(--space-xs);
            padding: var(--space-md);
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all var(--time-quick);
            font-family: var(--font-mono);
            color: var(--text-primary);
        }
        status-world .state:hover {
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }
        status-world .state.current {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
            cursor: default;
        }
        status-world .state .name {
            font-size: var(--text-sm);
            text-transform: lowercase;
            letter-spacing: 0.5px;
        }
        status-world .state .meaning {
            font-size: var(--text-xs);
            color: var(--text-muted);
            line-height: 1.4;
        }
        status-world .state.current .meaning {
            color: var(--accent-text);
            opacity: 0.8;
        }
        status-world .pair {
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
            padding: var(--space-lg);
            background: var(--surface);
            border: 1px solid var(--cool-border);
            border-radius: var(--radius-md);
        }
        status-world .pair-title {
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--cool-text);
        }
        status-world .pair-help {
            font-size: var(--text-sm);
            color: var(--text-muted);
            line-height: 1.55;
        }
        status-world .pair-row {
            display: flex;
            gap: var(--space-md);
            align-items: flex-end;
        }
        status-world .pair-row input-text { flex: 1; }
        status-world .pair-error {
            font-size: var(--text-xs);
            color: var(--danger-text);
        }
        status-world .pair-success {
            font-size: var(--text-xs);
            color: var(--vital-text);
        }
        status-world .uptime {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: var(--space-lg);
        }
        status-world .uptime-title {
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-muted);
            margin-bottom: var(--space-md);
        }
        status-world .grid {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        status-world .grid-row {
            display: grid;
            grid-template-columns: 60px 1fr;
            gap: var(--space-sm);
            align-items: center;
        }
        status-world .grid-row .stamp {
            font-size: 10px;
            color: var(--text-dim);
            font-family: var(--font-mono);
            letter-spacing: 0.5px;
            text-align: right;
        }
        status-world .grid-row .cells {
            display: grid;
            grid-template-columns: repeat(60, 1fr);
            gap: 1px;
            height: 14px;
        }
        status-world .cell {
            background: var(--surface-recessed);
            border-radius: 1px;
        }
        status-world .cell.alive { background: var(--vital); opacity: 0.45; }
        status-world .cell.fault { background: var(--danger); }
        status-world .empty {
            padding: var(--space-xl);
            color: var(--text-dim);
            text-align: center;
        }
        status-world .controls {
            display: flex;
            gap: var(--space-sm);
            flex-wrap: wrap;
            justify-content: space-between;
        }
        status-world .controls .left,
        status-world .controls .right {
            display: flex;
            gap: var(--space-sm);
        }
    `;

    build() {
        const { id, api } = this._props;
        this.personaId = id;
        this.api = api;
        this.persona = null;
        this.diagnose = null;
        this.pairCode = '';
        this.pairing = false;
        this.pairError = null;
        this.pairSuccess = null;

        this.innerHTML = `
            <div class="bar"></div>
            <div class="states"></div>
            <div class="pair" hidden></div>
            <div class="uptime"></div>
            <div class="controls">
                <div class="left"></div>
                <div class="right"></div>
            </div>
        `;
    }

    async activate() {
        this.persona = await this.api.getPersona(this.personaId);
        this.diagnose = await this.api.getDiagnose(this.personaId);
        this.render();
    }

    render() {
        this.renderBar();
        this.renderStates();
        this.renderPair();
        this.renderUptime();
        this.renderControls();
    }

    renderStates() {
        const el = this.querySelector('.states');
        el.innerHTML = '';

        const current = this.persona?.status || 'active';
        const states = [
            { id: 'active',    meaning: 'present, listening' },
            { id: 'sick',      meaning: 'something is wrong' },
            { id: 'hibernate', meaning: 'resting, not reachable' },
        ];

        for (const s of states) {
            const btn = document.createElement('div');
            btn.className = 'state';
            if (s.id === current) btn.classList.add('current');

            const name = document.createElement('span');
            name.className = 'name';
            name.textContent = s.id;
            btn.appendChild(name);

            const meaning = document.createElement('span');
            meaning.className = 'meaning';
            meaning.textContent = s.meaning;
            btn.appendChild(meaning);

            btn.addEventListener('click', () => this.setStatus(s.id, current));
            el.appendChild(btn);
        }
    }

    async setStatus(next, current) {
        if (next === current) return;
        const result = await this.api.updatePersona(this.personaId, { status: next });
        if (!result.success) return;
        this.persona = await this.api.getPersona(this.personaId);
        this.diagnose = await this.api.getDiagnose(this.personaId);
        this.render();
    }

    renderBar() {
        const barEl = this.querySelector('.bar');
        barEl.innerHTML = '';

        const dot = document.createElement('status-dot');
        const state = this.persona?.status === 'sick' ? 'danger'
            : this.persona?.status === 'hibernate' ? 'sleeping'
            : this.persona?.running ? 'vital'
            : 'sleeping';
        dot.init({ state });
        barEl.appendChild(dot);

        const name = document.createElement('span');
        name.className = 'name';
        name.textContent = this.persona?.name || '—';
        barEl.appendChild(name);

        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = this.persona?.status || (this.persona?.running ? 'active' : 'stopped');
        barEl.appendChild(label);
    }

    renderPair() {
        const pairEl = this.querySelector('.pair');
        pairEl.innerHTML = '';

        const unverified = (this.persona?.channels || []).filter((c) => !c.verified);
        if (unverified.length === 0) {
            pairEl.hidden = true;
            return;
        }
        pairEl.hidden = false;

        const title = document.createElement('div');
        title.className = 'pair-title';
        title.textContent = `Pending channel${unverified.length > 1 ? 's' : ''}: ${unverified.map((c) => c.type).join(', ')}`;
        pairEl.appendChild(title);

        const help = document.createElement('div');
        help.className = 'pair-help';
        help.textContent = 'Talk to her bot, get the pairing code, type it here.';
        pairEl.appendChild(help);

        const row = document.createElement('div');
        row.className = 'pair-row';
        const input = document.createElement('input-text');
        input.init({
            value: this.pairCode,
            placeholder: 'pairing code',
            onChange: (v) => { this.pairCode = v; },
        });
        row.appendChild(input);
        const btn = document.createElement('action-button');
        btn.init({
            label: this.pairing ? '...' : 'Pair',
            variant: 'primary',
            disabled: this.pairing,
            onClick: () => this.pair(),
        });
        row.appendChild(btn);
        pairEl.appendChild(row);

        if (this.pairError) {
            const err = document.createElement('div');
            err.className = 'pair-error';
            err.textContent = this.pairError;
            pairEl.appendChild(err);
        }
        if (this.pairSuccess) {
            const ok = document.createElement('div');
            ok.className = 'pair-success';
            ok.textContent = this.pairSuccess;
            pairEl.appendChild(ok);
        }
    }

    renderUptime() {
        const el = this.querySelector('.uptime');
        el.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'uptime-title';
        title.textContent = 'Last 24 hours';
        el.appendChild(title);

        const rows = this.diagnose?.uptime?.rows || [];
        const hasAny = rows.some((r) => r.cells && r.cells.some((c) => c.tick || c.fault));
        if (!hasAny) {
            const empty = document.createElement('div');
            empty.className = 'empty';
            empty.textContent = 'No health data yet.';
            el.appendChild(empty);
            return;
        }

        const grid = document.createElement('div');
        grid.className = 'grid';
        for (const row of rows) {
            const rowEl = document.createElement('div');
            rowEl.className = 'grid-row';

            const stamp = document.createElement('span');
            stamp.className = 'stamp';
            const from = row.from ? new Date(row.from) : null;
            stamp.textContent = from ? `${from.getHours().toString().padStart(2, '0')}:${from.getMinutes().toString().padStart(2, '0')}` : '';
            rowEl.appendChild(stamp);

            const cellsEl = document.createElement('div');
            cellsEl.className = 'cells';
            for (const cell of row.cells || []) {
                const cellEl = document.createElement('div');
                cellEl.className = 'cell';
                if (cell.fault) cellEl.classList.add('fault');
                else if (cell.tick) cellEl.classList.add('alive');
                if (cell.at) {
                    const t = new Date(cell.at);
                    cellEl.title = `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}${cell.fault ? ` — ${cell.fault}` : cell.tick ? ' — alive' : ''}`;
                }
                cellsEl.appendChild(cellEl);
            }
            rowEl.appendChild(cellsEl);
            grid.appendChild(rowEl);
        }
        el.appendChild(grid);
    }

    renderControls() {
        const leftEl = this.querySelector('.controls .left');
        const rightEl = this.querySelector('.controls .right');
        leftEl.innerHTML = '';
        rightEl.innerHTML = '';

        const running = !!this.persona?.running;
        const left = [
            { label: 'Sleep',   variant: 'secondary', disabled: !running, onClick: () => this.act('sleep') },
            { label: 'Restart', variant: 'secondary', disabled: !running, onClick: () => this.act('restart') },
            { label: running ? 'Stop' : 'Start', variant: 'secondary', onClick: () => this.act(running ? 'stop' : 'start') },
            { label: 'Export',  variant: 'ghost', onClick: () => this.api.exportPersona(this.personaId) },
        ];
        for (const c of left) {
            const btn = document.createElement('action-button');
            btn.init(c);
            leftEl.appendChild(btn);
        }

        const del = document.createElement('action-button');
        del.init({
            label: 'Delete',
            variant: 'danger',
            onClick: () => this.delete(),
        });
        rightEl.appendChild(del);
    }

    async act(action) {
        if (action === 'sleep')        await this.api.sleepPersona(this.personaId);
        else if (action === 'restart') await this.api.restartPersona(this.personaId);
        else if (action === 'stop')    await this.api.stopPersona(this.personaId);
        else if (action === 'start')   await this.api.startPersona(this.personaId);
        this.persona = await this.api.getPersona(this.personaId);
        this.diagnose = await this.api.getDiagnose(this.personaId);
        this.render();
    }

    async pair() {
        if (!this.pairCode.trim()) {
            this.pairError = 'Enter the code your bot gave you.';
            this.render();
            return;
        }
        this.pairing = true;
        this.pairError = null;
        this.pairSuccess = null;
        this.render();

        const result = await this.api.pairChannel(this.pairCode.trim(), this.personaId);
        this.pairing = false;

        if (result.success) {
            this.pairSuccess = 'Channel paired.';
            this.pairCode = '';
            this.persona = await this.api.getPersona(this.personaId);
        } else {
            this.pairError = result.error || 'Pairing failed.';
        }
        this.render();
    }

    async delete() {
        if (!confirm(`Delete ${this.persona?.name}? This cannot be undone.`)) return;
        await this.api.deletePersona(this.personaId);
    }
}

customElements.define('status-world', StatusWorld);
export default StatusWorld;
