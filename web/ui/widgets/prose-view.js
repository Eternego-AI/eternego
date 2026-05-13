/* <prose-view> — render a single markdown body with a title.
   setProps({ title, body }). */

import { toHTML } from '../platform/markdown.js';

class ProseView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        if (this._title === undefined) this._title = '';
        if (this._body  === undefined) this._body  = '';
        this.render();
    }
    setProps({ title, body }) {
        if (title !== undefined) this._title = title;
        if (body  !== undefined) this._body  = body;
        this.render();
    }
    render() {
        const body = (this._body || '').trim();
        this.innerHTML = `
            <div class="w-prose">
                ${this._title ? `<h2 class="w-prose-h">${escapeHtml(this._title)}</h2>` : ''}
                ${body
                    ? `<div class="w-prose-body">${toHTML(body)}</div>`
                    : `<p class="w-prose-empty">(nothing here yet)</p>`
                }
            </div>
        `;
    }
}
function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
customElements.define('prose-view', ProseView);
