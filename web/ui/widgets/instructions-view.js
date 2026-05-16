/* <instructions-view> — meanings catalog.
   setProps({ items }). items is a list of {intention, body, source}. */

import { toHTML } from '../platform/markdown.js';

class InstructionsView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._items = null;
        this.render();
    }
    setProps({ items }) {
        if (items !== undefined) this._items = items;
        this.render();
    }
    render() {
        const all = this._items;
        if (all === null) {
            this.innerHTML = `<div class="w-instr"><p class="w-instr-loading">loading…</p></div>`;
            return;
        }
        const builtin = all.filter(i => i.source === 'builtin');
        const custom  = all.filter(i => i.source === 'custom');

        this.innerHTML = `
            <div class="w-instr">
                <div class="w-instr-intro">
                    <h2 class="w-instr-h">Her instructions</h2>
                    <p class="w-instr-sub">When she meets a moment she recognizes, she loads its path. Built-in meanings ship with her; she writes the rest as she lives.</p>
                </div>

                ${this._section('Hers — written from living', custom)}
                ${this._section('Built-in — shipped with her', builtin)}
            </div>
        `;
        for (const det of this.querySelectorAll('details.w-instr-item')) {
            det.addEventListener('toggle', () => {
                /* let the browser handle open/close; no extra logic. */
            });
        }
    }
    _section(title, list) {
        if (!list.length) return '';
        return `
            <section class="w-instr-section">
                <h3 class="w-instr-section-h">${escapeHtml(title)}</h3>
                <div class="w-instr-list">
                    ${list.map(m => `
                        <details class="w-instr-item">
                            <summary class="w-instr-item-h">${escapeHtml(m.intention)}</summary>
                            <div class="w-instr-item-body">${toHTML(m.body || '')}</div>
                        </details>
                    `).join('')}
                </div>
            </section>
        `;
    }
}
function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
customElements.define('instructions-view', InstructionsView);
