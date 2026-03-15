import Mode from './mode.js';
import OS from '../index.js';
import { house, settings, plus } from '../icons.js';

class DesktopMode extends Mode {
    // init({ apps: App[], signals: Feed })
    build() {
        this.innerHTML = `
            <div class="desktop">
                <div class="dock">
                    <div class="dock-strip"></div>
                </div>
            </div>
        `;

        this._desktop = this.querySelector('.desktop');
        this._dock = this.querySelector('.dock');
        this._strip = this.querySelector('.dock-strip');
        this._items = [];
        this._selectedIndex = 0;
        this._appInstances = {};
        this._appGrids = {};
        this._appFocus = {};

        // Create app instances and their grid layouts
        const apps = this._props.apps;
        for (const AppClass of apps) {
            const app = new AppClass();
            app.init({ signals: this._props.signals });
            this._appInstances[AppClass.appId] = app;

            const page = document.createElement('div');
            page.className = 'app-page';
            page.dataset.app = AppClass.appId;

            const backdrop = document.createElement('div');
            backdrop.className = 'page-backdrop';

            const grid = document.createElement('grid-layout');
            const appId = AppClass.appId;
            grid.init({
                onFocus: (name) => {
                    this._appFocus[appId] = name || null;
                    grid.relayout(name || null);
                    const instance = this._appInstances[appId];
                    if (instance?.setFocused) instance.setFocused(name || null);
                },
            });

            for (const widget of app.widgets()) {
                grid.addWidget(widget);
            }

            page.appendChild(backdrop);
            page.appendChild(grid);
            this._desktop.appendChild(page);
            this._appGrids[AppClass.appId] = { page, grid };

            requestAnimationFrame(() => grid.relayout(null));
        }

        // Navigation handler
        OS.onNavigate(({ app, personaId }) => {
            // Rebuild dock to reflect persona changes
            this._buildItems();
            this._renderStrip();

            // Dock state: home (centered) vs docked (bottom)
            this._dock.classList.toggle('docked', !!app);
            this._highlightDock(app);

            // Show/hide app pages
            for (const [id, { page, grid }] of Object.entries(this._appGrids)) {
                if (id === app) {
                    page.classList.add('app-focused');
                    // Reset focus when switching apps
                    this._appFocus[id] = null;
                    grid.relayout(null);
                } else {
                    page.classList.remove('app-focused');
                }
            }

            // Notify app instances
            for (const [id, instance] of Object.entries(this._appInstances)) {
                if (id === app) {
                    if (id === 'persona' && personaId) instance.setPersona(personaId);
                    if (instance.activate) instance.activate();
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
        // Home button — only visible in dock mode
        this._items.push({ id: '_home', name: 'Home', icon: house(24), type: 'home' });
        this._items.push({ id: '_system', name: 'System', icon: settings(24), type: 'system' });
        for (const p of OS.personas) {
            this._items.push({ id: p.id, name: p.name, icon: p.name.charAt(0).toUpperCase(), type: '' });
        }
        this._items.push({ id: '_new', name: 'New', icon: plus(24), type: 'action' });
        this._selectedIndex = OS.personas.length > 0 ? 2 : 1;
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
            el.dataset.id = item.id;
            this._strip.appendChild(el);
        });
    }

    _highlightDock(activeApp) {
        for (const icon of this._strip.children) {
            const id = icon.dataset.id;
            let isActive = false;
            if (activeApp === 'persona' && id !== '_home' && id !== '_system' && id !== '_new') {
                isActive = id === OS.currentPersonaId;
            } else if (id === '_system' && activeApp === 'system') {
                isActive = true;
            } else if (id === '_new' && activeApp === 'new-persona') {
                isActive = true;
            }
            icon.classList.toggle('active', isActive);
        }
    }

    _openSelected() {
        const item = this._items[this._selectedIndex];
        if (!item) return;
        if (item.id === '_home') OS.minimize();
        else if (item.id === '_new') OS.open('new-persona');
        else if (item.id === '_system') OS.open('system');
        else OS.open('persona', { personaId: item.id });
    }
}

customElements.define('desktop-mode', DesktopMode);
export default DesktopMode;
