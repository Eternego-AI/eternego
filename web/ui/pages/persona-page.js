/* <persona-page> — sidebar + main panel. Menu is built dynamically:
   fixed system tabs (chat, calendar, status, settings) plus per-section
   tabs derived from the `knowledge` payload (memory keys → one tab each,
   instruction → one Instructions tab).

   setProps({ persona, personas, messages, tab, diagnose, knowledge, calendar }).
   Emits: send, stop, poweroff, restart, delete, refresh-diagnose,
          select (tab), switch (persona), add (open onboarding),
          calendar-navigate, update-status, update-model, clear-model, pair-channel. */

const WIDGET_FOR_KIND = {
    chat:        'chat-view',
    memory:      'memory-view',
    instruction: 'instructions-view',
    calendar:    'calendar-view',
    status:      'status-view',
    settings:    'settings-view',
};

function humanize(key) {
    return String(key).replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

class PersonaPage extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._tab = 'chat';
        this._persona = null;
        this._personas = [];
        this._messages = [];
        this._diagnose = null;
        this._knowledge = null;
        this._calendar = null;
        this.innerHTML = `
            <sidebar-nav></sidebar-nav>
            <div class="p-main"></div>
        `;
        this._sidebar = this.querySelector('sidebar-nav');
        this._main = this.querySelector('.p-main');
    }

    showSaveResult(slot, ok, message) {
        const widget = this._main.firstElementChild;
        widget?.showSaveResult?.(slot, ok, message);
    }

    showPairResult(ok, message) {
        const widget = this._main.firstElementChild;
        widget?.showPairResult?.(ok, message);
    }

    setProps({ persona, personas, messages, tab, diagnose, knowledge, calendar }) {
        if (persona !== undefined) this._persona = persona;
        if (personas !== undefined) this._personas = personas;
        if (messages !== undefined) this._messages = messages;
        if (diagnose !== undefined) this._diagnose = diagnose;
        if (knowledge !== undefined) this._knowledge = knowledge;
        if (calendar !== undefined) this._calendar = calendar;

        const oldTop = (this._tab || '').split('/')[0];
        if (tab) this._tab = tab;
        const newTop = (this._tab || '').split('/')[0];
        const topChanged = oldTop !== newTop;

        this.renderSidebar();
        const expected = WIDGET_FOR_KIND[this.currentItem().kind];
        const mounted = this._main.firstElementChild?.tagName?.toLowerCase();
        if (topChanged || !mounted || mounted !== expected) this.renderMain();
        else this.refreshMain();
    }

    appendMessage(msg) {
        this._messages.push(msg);
        if (this._tab === 'chat') {
            this._main.firstElementChild?.appendMessage?.(msg);
        }
    }

    setPending(on, detail, mode) {
        if (this._tab === 'chat') {
            this._main.firstElementChild?.setPending?.(on, detail, mode);
        }
    }

    menuItems() {
        const items = [];
        items.push({ id: 'chat',     label: 'Chat',     kind: 'chat' });
        items.push({ id: 'calendar', label: 'Calendar', kind: 'calendar' });

        const k = this._knowledge;
        if (k && k.memory && Object.keys(k.memory).length > 0) {
            items.push({ id: 'memory', label: 'Memory', kind: 'memory' });
        }
        if (k && Array.isArray(k.instruction) && k.instruction.length > 0) {
            items.push({ id: 'instruction', label: 'Instructions', kind: 'instruction' });
        }

        items.push({ id: 'status',   label: 'Status',   kind: 'status' });
        items.push({ id: 'settings', label: 'Settings', kind: 'settings' });
        return items;
    }

    currentItem() {
        const items = this.menuItems();
        /* `_tab` can be 'memory' or 'memory/<key>' — match on the top segment. */
        const top = (this._tab || '').split('/')[0];
        return items.find(i => i.id === top) || items[0];
    }

    currentSection() {
        /* For memory: returns the key after the slash, or first key. */
        const parts = (this._tab || '').split('/');
        if (parts.length > 1 && parts[1]) return parts[1];
        const keys = Object.keys(this._knowledge?.memory || {});
        return keys[0] || null;
    }

    renderSidebar() {
        const p = this._persona;
        const status = !p ? 'resting'
                      : p.status === 'sick' ? 'sick'
                      : p.status === 'hibernate' ? 'sleeping'
                      : p.running === false ? 'stopped'
                      : 'resting';
        this._sidebar.setProps({
            persona: p,
            model: p?.thinking?.name || '',
            status,
            active: (this._tab || '').split('/')[0],
            items: this.menuItems(),
            personas: this._personas,
            onSelect: (id) => this.dispatchEvent(new CustomEvent('select', { detail: { id } })),
            onSwitchPersona: (id) => this.dispatchEvent(new CustomEvent('switch', { detail: { id } })),
            onAddPersona: () => this.dispatchEvent(new CustomEvent('add')),
        });
    }

    renderMain() {
        const item = this.currentItem();
        const tag = WIDGET_FOR_KIND[item.kind] || 'chat-view';

        this._main.innerHTML = '';
        const widget = document.createElement(tag);
        this._main.appendChild(widget);

        if (tag === 'chat-view') {
            widget.addEventListener('send',     (e) => this.dispatchEvent(new CustomEvent('send', { detail: e.detail })));
            widget.addEventListener('stop',     ()  => this.dispatchEvent(new CustomEvent('stop')));
            widget.addEventListener('poweroff', ()  => this.dispatchEvent(new CustomEvent('poweroff')));
        }
        if (tag === 'status-view') {
            widget.addEventListener('refresh', () => this.dispatchEvent(new CustomEvent('refresh-diagnose')));
        }
        if (tag === 'settings-view') {
            widget.addEventListener('poweroff', () => this.dispatchEvent(new CustomEvent('poweroff')));
            widget.addEventListener('restart',  () => this.dispatchEvent(new CustomEvent('restart')));
            widget.addEventListener('delete',   () => this.dispatchEvent(new CustomEvent('delete')));
            widget.addEventListener('update-status', (e) => this.dispatchEvent(new CustomEvent('update-status', { detail: e.detail })));
            widget.addEventListener('update-model',  (e) => this.dispatchEvent(new CustomEvent('update-model',  { detail: e.detail })));
            widget.addEventListener('clear-model',   (e) => this.dispatchEvent(new CustomEvent('clear-model',   { detail: e.detail })));
            widget.addEventListener('pair-channel',  (e) => this.dispatchEvent(new CustomEvent('pair-channel',  { detail: e.detail })));
        }
        if (tag === 'calendar-view') {
            widget.addEventListener('navigate', (e) =>
                this.dispatchEvent(new CustomEvent('calendar-navigate', { detail: e.detail })));
        }
        if (tag === 'memory-view') {
            widget.addEventListener('select-section', (e) =>
                this.dispatchEvent(new CustomEvent('select', { detail: { id: `memory/${e.detail.section}` } })));
        }

        this.refreshMain();
    }

    refreshMain() {
        const widget = this._main.firstElementChild;
        if (!widget) return;
        const item = this.currentItem();
        const p = this._persona;
        const k = this._knowledge;
        switch (item.kind) {
            case 'chat':
                widget.setProps({ personaName: p?.name, messages: this._messages });
                break;
            case 'memory':
                widget.setProps({ memory: k?.memory || {}, section: this.currentSection() });
                break;
            case 'instruction':
                widget.setProps({ items: k?.instruction || [] });
                break;
            case 'status':
                widget.setProps({ persona: p, diagnose: this._diagnose });
                break;
            case 'settings':
                widget.setProps({ persona: p });
                break;
            case 'calendar':
                widget.setProps({ persona: p, calendar: this._calendar });
                break;
        }
    }
}

customElements.define('persona-page', PersonaPage);
