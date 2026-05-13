/* <field-select name="..." label="..." help="...">
       <option value="x">X</option>
       ...
   </field-select>
   Form dropdown. Emits 'input' with detail.value. */

import { escapeHtml } from '../platform/escape.js';

class FieldSelect extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        const name     = this.getAttribute('name') || '';
        const label    = this.getAttribute('label') || '';
        const help     = this.getAttribute('help') || '';
        const required = this.hasAttribute('required');
        const options  = Array.from(this.querySelectorAll('option')).map((o) => ({
            value: o.getAttribute('value') || o.textContent,
            label: o.textContent,
        }));

        this.innerHTML = `
            <label>
                <span class="el-label">
                    ${escapeHtml(label)}
                    ${required ? '<span class="el-req">required</span>' : '<span class="el-opt">optional</span>'}
                    <span class="el-err" hidden></span>
                </span>
                <select class="el-select" name="${escapeHtml(name)}">
                    ${options.map(o => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`).join('')}
                </select>
                ${help ? `<span class="el-help">${escapeHtml(help)}</span>` : ''}
            </label>
        `;
        this._select = this.querySelector('select');
        this._err = this.querySelector('.el-err');
        this._select.addEventListener('change', () => {
            this.dispatchEvent(new CustomEvent('input', { detail: { value: this._select.value } }));
        });
    }

    get value() { return this._select?.value || ''; }
    set value(v) { if (this._select) this._select.value = v; }
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
}
customElements.define('field-select', FieldSelect);
