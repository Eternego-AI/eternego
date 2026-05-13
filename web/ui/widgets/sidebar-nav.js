/* <sidebar-nav> — left rail: breath + name + nav + persona list.
   setProps({ persona, model, status, active, items, personas, onSelect, onSwitchPersona, onAddPersona }) */

import { escapeHtml } from '../platform/escape.js';

class SidebarNav extends HTMLElement {
    setProps({ persona, model, status, active, items, personas, onSelect, onSwitchPersona, onAddPersona }) {
        this._persona = persona;
        this._model = model || '';
        this._status = status || 'resting';
        this._active = active;
        this._items = items || [];
        this._personas = personas || [];
        this._onSelect = onSelect;
        this._onSwitchPersona = onSwitchPersona;
        this._onAddPersona = onAddPersona;
        this.render();
    }
    render() {
        const personaName = this._persona?.name || '—';
        this.innerHTML = `
            <div class="w-top">
                <div class="w-name">
                    <breath-dot state="${this._status}"></breath-dot>
                    <span>${escapeHtml(personaName)}</span>
                </div>
                ${this._model ? `<div class="w-meta"><span>${escapeHtml(this._model)}</span></div>` : ''}
            </div>
            <div class="w-nav"></div>
            <div class="w-bottom"></div>
        `;

        const nav = this.querySelector('.w-nav');
        for (const item of this._items) {
            const link = document.createElement('menu-link');
            link.setProps({
                label: item.label,
                count: item.count,
                active: item.id === this._active,
                onClick: () => this._onSelect && this._onSelect(item.id),
            });
            nav.appendChild(link);
        }

        const bottom = this.querySelector('.w-bottom');
        for (const p of this._personas) {
            if (p.id === this._persona?.id) continue;
            const row = document.createElement('div');
            row.className = 'w-persona-row';
            row.innerHTML = `
                <span class="w-mark">${escapeHtml((p.name || '?')[0].toUpperCase())}</span>
                <span>${escapeHtml(p.name || '')}</span>
                <span class="w-meta">${p.status === 'hibernate' ? 'resting' : 'active'}</span>
            `;
            row.onclick = () => this._onSwitchPersona && this._onSwitchPersona(p.id);
            bottom.appendChild(row);
        }
        const add = document.createElement('div');
        add.className = 'w-persona-row';
        add.innerHTML = `<span class="w-mark is-add">+</span><span>add persona</span>`;
        add.onclick = () => this._onAddPersona && this._onAddPersona();
        bottom.appendChild(add);
    }
}
customElements.define('sidebar-nav', SidebarNav);
