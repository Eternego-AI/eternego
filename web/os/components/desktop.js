import OS from '../os.js';

class Desktop extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <div class="desktop">
                <div class="app-icon-layer">
                    <div class="app-icon-strip"></div>
                </div>
                <persona-app></persona-app>
                <system-app></system-app>
                <new-persona-app></new-persona-app>
            </div>
        `;

        this._desktop = this.querySelector('.desktop');
        this._iconLayer = this.querySelector('.app-icon-layer');
        this._strip = this.querySelector('.app-icon-strip');
        this._items = [];
        this._selectedIndex = 0;

        // Hide icons when an app is open
        OS.onNavigate(({ app }) => {
            if (app) this._iconLayer.classList.add('hidden');
            else this._iconLayer.classList.remove('hidden');
        });

        // Keyboard: home-level only
        document.addEventListener('keydown', (e) => {
            if (!OS.booted || OS.currentApp || this._items.length === 0) return;
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                this._selectedIndex = (this._selectedIndex + 1) % this._items.length;
                this._renderStrip();
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this._selectedIndex = (this._selectedIndex - 1 + this._items.length) % this._items.length;
                this._renderStrip();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this._openSelected();
            }
        });

        // Wait for boot
        document.addEventListener('booted', () => {
            this._buildItems();
            this._renderStrip();
            this._desktop.classList.add('visible');
        });
    }

    _buildItems() {
        this._items = [];
        this._items.push({ id: '_system', name: 'System', icon: '\u2699', type: 'system' });
        for (const p of OS.personas) {
            this._items.push({ id: p.id, name: p.name, icon: p.name.charAt(0).toUpperCase(), type: '' });
        }
        this._items.push({ id: '_new', name: 'New', icon: '+', type: 'action' });
        this._selectedIndex = OS.personas.length > 0 ? 1 : 0;
    }

    _renderStrip() {
        this._strip.innerHTML = '';
        this._items.forEach((item, i) => {
            const el = document.createElement('app-icon');
            el.setAttribute('icon', item.icon);
            el.setAttribute('label', item.name);
            if (item.type) el.setAttribute('type', item.type);
            if (i === this._selectedIndex) el.setAttribute('selected', '');

            el.addEventListener('click', () => {
                this._selectedIndex = i;
                this._openSelected();
            });
            this._strip.appendChild(el);
        });
    }

    _openSelected() {
        const item = this._items[this._selectedIndex];
        if (!item) return;
        if (item.id === '_new') OS.open('new-persona');
        else if (item.id === '_system') OS.open('system');
        else OS.open('persona', { personaId: item.id });
    }
}

customElements.define('os-desktop', Desktop);
