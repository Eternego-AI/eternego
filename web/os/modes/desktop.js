import Mode from './mode.js';
import OS from '../index.js';

class DesktopMode extends Mode {
    // init({ apps: App[], signals: Feed })
    build() {
        this.innerHTML = `
            <div class="desktop">
                <div class="app-icon-layer">
                    <div class="app-icon-strip"></div>
                </div>
            </div>
        `;

        this._desktop = this.querySelector('.desktop');
        this._iconLayer = this.querySelector('.app-icon-layer');
        this._strip = this.querySelector('.app-icon-strip');
        this._items = [];
        this._selectedIndex = 0;
        this._appInstances = {};
        this._appGrids = {};

        // Create app instances and their grid layouts
        const apps = this._props.apps;
        for (const AppClass of apps) {
            const app = new AppClass();
            app.init({ signals: this._props.signals });
            this._appInstances[AppClass.appId] = app;

            // Create the page container: backdrop + minimize btn + grid
            const page = document.createElement('div');
            page.className = 'app-page';
            page.dataset.app = AppClass.appId;

            const backdrop = document.createElement('div');
            backdrop.className = 'page-backdrop';

            const btn = document.createElement('button');
            btn.className = 'minimize-btn';
            btn.innerHTML = '&minus;';
            btn.addEventListener('click', () => OS.minimize());

            const grid = document.createElement('grid-layout');
            grid.init({ onFocus: (name) => OS.focus(name) });

            for (const widget of app.widgets()) {
                grid.addWidget(widget);
            }

            page.appendChild(backdrop);
            page.appendChild(btn);
            page.appendChild(grid);
            this._desktop.appendChild(page);
            this._appGrids[AppClass.appId] = { page, grid };

            // Initial layout
            requestAnimationFrame(() => grid.relayout(null));
        }

        // Navigation handler
        OS.onNavigate(({ app, personaId, widget }) => {
            // Show/hide icon layer
            if (app) this._iconLayer.classList.add('hidden');
            else this._iconLayer.classList.remove('hidden');

            // Show/hide app pages
            for (const [id, { page, grid }] of Object.entries(this._appGrids)) {
                if (id === app) {
                    page.classList.add('app-focused');
                    page.classList.toggle('widget-focused', !!widget);
                    grid.relayout(widget || null);
                } else {
                    page.classList.remove('app-focused', 'widget-focused');
                }
            }

            // Notify app instances
            for (const [id, instance] of Object.entries(this._appInstances)) {
                if (id === app) {
                    if (id === 'persona' && personaId) instance.setPersona(personaId);
                    if (instance.activate) instance.activate(widget);
                    if (widget && instance.setFocused) instance.setFocused(widget);
                } else {
                    if (instance.deactivate) instance.deactivate();
                }
            }
        });

        // Keyboard navigation at home level
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
    }

    activate() {
        this._buildItems();
        this._renderStrip();
        this._desktop.classList.add('visible');
        OS.restore();
    }

    deactivate() {
        this._desktop.classList.remove('visible');
    }

    _buildItems() {
        this._items = [];
        this._items.push({ id: '_system', name: 'System', icon: '⚙', type: 'system' });
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
            el.init({
                icon: item.icon,
                label: item.name,
                type: item.type,
                selected: i === this._selectedIndex,
                onClick: () => {
                    this._selectedIndex = i;
                    this._openSelected();
                },
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

customElements.define('desktop-mode', DesktopMode);
export default DesktopMode;
