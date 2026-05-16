/* <status-view> — lifecycle + models + working memory + uptime grid. Emits 'refresh'. */

import { escapeHtml } from '../platform/escape.js';

class StatusView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._persona = null;
        this._diagnose = null;
        this._signals = [];
        this.innerHTML = `
            <div class="w-status">
                <div class="w-status-head">
                    <h2 class="w-status-title">Status</h2>
                    <button class="w-status-refresh">REFRESH</button>
                </div>
                <div class="w-status-body"></div>
            </div>
        `;
        this.querySelector('.w-status-refresh').onclick = () =>
            this.dispatchEvent(new CustomEvent('refresh'));
    }
    setProps({ persona, diagnose, signals }) {
        if (persona !== undefined) this._persona = persona;
        if (diagnose !== undefined) this._diagnose = diagnose;
        if (signals !== undefined) this._signals = signals;
        this.render();
    }
    render() {
        const body = this.querySelector('.w-status-body');
        const p = this._persona;
        const d = this._diagnose;
        if (!p) { body.innerHTML = '<p class="w-dim">No persona.</p>'; return; }
        if (!d) { body.innerHTML = '<p class="w-dim">Checking…</p>'; return; }

        const status = d.status || p.status || '—';
        const running = p.running ?? '—';
        const mind = d.mind || {};
        const messages = mind.messages?.length ?? 0;
        const archive = mind.archive?.length ?? 0;
        const rows = d.uptime?.rows || [];

        body.innerHTML = `
            <section class="w-status-section">
                <h3>Lifecycle</h3>
                <dl>
                    <dt>status</dt><dd>${escapeHtml(String(status))}</dd>
                    <dt>running</dt><dd>${running === true ? 'yes' : running === false ? 'no' : '—'}</dd>
                </dl>
            </section>
            <section class="w-status-section">
                <h3>Models</h3>
                <dl>
                    <dt>thinking</dt><dd>${escapeHtml(p.thinking?.name || '—')}</dd>
                    <dt>vision</dt><dd>${escapeHtml(p.vision?.name || '—')}</dd>
                    <dt>frontier</dt><dd>${escapeHtml(p.frontier?.name || '—')}</dd>
                </dl>
            </section>
            <section class="w-status-section">
                <h3>Working memory</h3>
                <dl>
                    <dt>messages</dt><dd>${messages}</dd>
                    <dt>archived batches</dt><dd>${archive}</dd>
                </dl>
            </section>
            <section class="w-status-section">
                <h3>Uptime <span class="w-dim">— last 24 hours · each cell is one minute</span></h3>
                <div class="w-uptime-rows">
                    ${rows.map(row => {
                        const cells = row.cells || [];
                        const label = (row.to || '').slice(11, 16);
                        return `
                            <div class="w-uptime-row">
                                <span class="w-uptime-label">${escapeHtml(label)}</span>
                                <div class="w-uptime-row-cells">
                                    ${cells.map(c => {
                                        const state = c.fault ? 'bad' : c.tick ? 'ok' : 'gap';
                                        return `<span class="w-uptime-cell" data-state="${state}" title="${escapeHtml(c.at || '')} · tick=${c.tick ? 'y' : 'n'} · fault=${c.fault ? 'y' : 'n'}"></span>`;
                                    }).join('')}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </section>
            <section class="w-status-section">
                <h3>Recent signals <span class="w-dim">— last 50, newest first</span></h3>
                ${this._signals && this._signals.length ? `
                    <div class="w-signals">
                        ${[...this._signals].reverse().map(s => `
                            <div class="w-signals-row">
                                <span class="w-signals-time">${escapeHtml(s.time || '')}</span>
                                <span class="w-signals-type">${escapeHtml(s.type || '')}</span>
                                <span class="w-signals-title">${escapeHtml(s.title || '')}</span>
                                <span class="w-signals-detail">${escapeHtml(s.detail || '')}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : '<p class="w-dim">No signals yet.</p>'}
            </section>
        `;
    }
}
customElements.define('status-view', StatusView);
