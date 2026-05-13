/* <field-input name="..." label="..." type="text|password|email" placeholder="..." help="..." required>
   Form input with label + help text + optional error. Emits 'input' with detail.value. */

import { escapeHtml } from '../platform/escape.js';

class FieldInput extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        const name        = this.getAttribute('name') || '';
        const label       = this.getAttribute('label') || '';
        const type        = this.getAttribute('type') || 'text';
        const placeholder = this.getAttribute('placeholder') || '';
        const help        = this.getAttribute('help') || '';
        const value       = this.getAttribute('value') || '';
        const required    = this.hasAttribute('required');

        this.innerHTML = `
            <label>
                <span class="el-label">
                    ${escapeHtml(label)}
                    ${required ? '<span class="el-req">required</span>' : '<span class="el-opt">optional</span>'}
                    <span class="el-err" hidden></span>
                </span>
                <input class="el-input"
                       type="${type}"
                       name="${escapeHtml(name)}"
                       placeholder="${escapeHtml(placeholder)}"
                       value="${escapeHtml(value)}">
                ${help ? `<span class="el-help">${escapeHtml(help)}</span>` : ''}
            </label>
        `;
        this._input = this.querySelector('input');
        this._err   = this.querySelector('.el-err');
        this._input.addEventListener('input', () => {
            this.dispatchEvent(new CustomEvent('input', { detail: { value: this._input.value } }));
        });
    }

    get value() { return this._input?.value || ''; }
    set value(v) { if (this._input) this._input.value = v; }
    setError(msg) {
        if (!this._err) return;
        if (msg) {
            this._err.textContent = msg;
            this._err.hidden = false;
            this.setAttribute('error', '');
        } else {
            this._err.hidden = true;
            this.removeAttribute('error');
        }
    }
    focus() { this._input?.focus(); }
}
customElements.define('field-input', FieldInput);
