/* <menu-link> — sidebar nav item. setProps({ label, count, active, onClick }). */

import { escapeHtml } from '../platform/escape.js';

class MenuLink extends HTMLElement {
    setProps({ label, count, onClick, active }) {
        this._label = label || '';
        this._count = count;
        if (active) this.setAttribute('active', '');
        else this.removeAttribute('active');
        if (onClick) this.onclick = onClick;
        this.render();
    }
    render() {
        const count = this._count != null
            ? `<span class="el-count">${this._count}</span>`
            : '';
        this.innerHTML = `<span>${escapeHtml(this._label)}</span>${count}`;
    }
}
customElements.define('menu-link', MenuLink);
