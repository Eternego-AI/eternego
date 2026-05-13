/* <role-message> — one message bubble with optional collapsible trace.
   setProps({ role, text, time, image, trace }). */

import { escapeHtml } from '../platform/escape.js';

class RoleMessage extends HTMLElement {
    setProps({ role, text, time, image, trace }) {
        this.setAttribute('role', role || 'system');
        this._text = text || '';
        this._time = time || '';
        this._image = image || '';
        this._trace = Array.isArray(trace) ? trace : null;
        this.render();
    }
    render() {
        const who = this.getAttribute('role') === 'me' ? 'you'
                  : this.getAttribute('role') === 'them' ? 'her'
                  : 'system';
        const img = this._image
            ? `<img class="el-image" src="${this._image}" alt="">`
            : '';
        const traceCount = this._trace?.length || 0;
        const traceToggle = traceCount > 0
            ? `<button class="el-trace-toggle" type="button">▸ what she did <span class="el-trace-count">${traceCount}</span></button>`
            : '';
        const traceBody = traceCount > 0
            ? `<div class="el-trace" hidden>${this._trace.map(t => this._renderTraceRow(t)).join('')}</div>`
            : '';
        this.innerHTML = `
            <div class="el-head">
                <span class="who">${who}</span>
                ${this._time ? `<span>${escapeHtml(this._time)}</span>` : ''}
            </div>
            <div class="el-body">${escapeHtml(this._text)}</div>
            ${img}
            ${traceToggle}
            ${traceBody}
        `;

        const imgEl = this.querySelector('.el-image');
        if (imgEl) imgEl.addEventListener('click', () => window.open(imgEl.src, '_blank'));

        const toggle = this.querySelector('.el-trace-toggle');
        const body = this.querySelector('.el-trace');
        if (toggle && body) {
            toggle.onclick = () => {
                const open = !body.hidden;
                body.hidden = open;
                toggle.innerHTML = open
                    ? `▸ what she did <span class="el-trace-count">${traceCount}</span>`
                    : `▾ what she did <span class="el-trace-count">${traceCount}</span>`;
            };
        }
    }

    _renderTraceRow(t) {
        const time = t.time || '';
        const type = t.type || '';
        const title = t.title || '';
        const detail = t.detail || '';
        return `<div class="el-trace-row">
            <span class="el-trace-time">${escapeHtml(time)}</span>
            <span class="el-trace-type el-trace-type-${escapeHtml(type.toLowerCase())}">${escapeHtml(type)}</span>
            <span class="el-trace-title">${escapeHtml(title)}</span>
            ${detail ? `<span class="el-trace-detail">${escapeHtml(detail)}</span>` : ''}
        </div>`;
    }
}
customElements.define('role-message', RoleMessage);
