/* <memory-view> — top-level page for the persona's readable memory.
   Renders horizontal sub-tabs (one per memory key) and the body of
   the active section via <prose-view>.

   setProps({ memory: {key: body, ...}, section: 'key' }).
   Emits 'select-section' { section } when a sub-tab is clicked. */

class MemoryView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._memory = {};
        this._section = null;
        this.innerHTML = `
            <div class="w-mem">
                <header class="w-mem-head">
                    <h2 class="w-mem-h">Memory</h2>
                    <p class="w-mem-sub">The files she keeps about you, herself, and what she's working through. She writes these.</p>
                </header>
                <nav class="w-mem-tabs" role="tablist"></nav>
                <div class="w-mem-body"></div>
            </div>
        `;
        this._tabs = this.querySelector('.w-mem-tabs');
        this._body = this.querySelector('.w-mem-body');
    }

    setProps({ memory, section }) {
        if (memory !== undefined) this._memory = memory || {};
        const keys = Object.keys(this._memory);
        if (section !== undefined && section !== null) this._section = section;
        if (!this._section || !keys.includes(this._section)) this._section = keys[0] || null;
        this.render();
    }

    render() {
        const keys = Object.keys(this._memory);
        this._tabs.innerHTML = keys.map(k => `
            <button class="w-mem-tab ${k === this._section ? 'is-active' : ''}" data-key="${escapeAttr(k)}" type="button">${escapeHtml(humanize(k))}</button>
        `).join('');
        for (const btn of this._tabs.querySelectorAll('.w-mem-tab')) {
            btn.onclick = () => this.dispatchEvent(new CustomEvent('select-section', {
                detail: { section: btn.dataset.key },
            }));
        }

        this._body.innerHTML = '';
        if (!this._section) {
            this._body.innerHTML = '<p class="w-mem-empty">She hasn\'t written anything down yet.</p>';
            return;
        }
        const prose = document.createElement('prose-view');
        this._body.appendChild(prose);   /* attach first so connectedCallback runs and won't clobber */
        prose.setProps({ title: '', body: this._memory[this._section] || '' });
    }
}

function humanize(key) {
    return String(key).replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeAttr(s) {
    return String(s).replace(/"/g, '&quot;');
}
customElements.define('memory-view', MemoryView);
