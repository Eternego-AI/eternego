import Painted from '../platform/painted.js';
import './worlds/chooser-world.js';
import './worlds/create-world.js';
import './worlds/migrate-world.js';
import './worlds/outer-world.js';
import './worlds/inner-world.js';
import './worlds/status-world.js';

class AppFrame extends Painted {
    static _styled = false;
    static _css = `
        app-frame {
            display: flex;
            flex-direction: column;
            position: absolute;
            inset: 0;
        }
        app-frame .header {
            position: relative;
            display: flex;
            align-items: center;
            padding: 0 var(--space-xl);
            height: 56px;
            border-bottom: 1px solid var(--border-subtle);
            background: rgba(11, 11, 20, 0.7);
            backdrop-filter: blur(12px);
            z-index: 10;
        }
        app-frame[no-header] .header { display: none; }
        app-frame .picker {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: border-color var(--time-quick);
        }
        app-frame .picker:hover { border-color: var(--border-hover); }
        app-frame .picker .name {
            font-size: var(--text-md);
            color: var(--warm-text);
            font-weight: 500;
        }
        app-frame .picker .caret {
            font-size: var(--text-xs);
            color: var(--text-dim);
        }
        app-frame .menu {
            position: absolute;
            top: 50px;
            left: var(--space-xl);
            min-width: 240px;
            padding: var(--space-sm);
            background: var(--surface-overlay);
            border: 1px solid var(--border-hover);
            border-radius: var(--radius-md);
            box-shadow: 0 16px 48px rgba(0,0,0,0.6);
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 2px;
            z-index: 20;
        }
        app-frame .menu[hidden] { display: none; }
        app-frame .menu-item {
            text-align: left;
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-sm);
            color: var(--text-body);
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            cursor: pointer;
            transition: background var(--time-quick);
        }
        app-frame .menu-item:hover {
            background: var(--surface-active);
            color: var(--text-primary);
        }
        app-frame .menu-item.current {
            color: var(--warm-text);
            background: var(--warm-bg);
        }
        app-frame .menu-item.add {
            color: var(--accent-text);
            margin-top: var(--space-sm);
            padding-top: var(--space-md);
            border-top: 1px solid var(--border-subtle);
        }
        app-frame .spacer { flex: 1; }
        app-frame .tabs {
            display: flex;
            gap: 2px;
            padding: 3px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
        }
        app-frame .tab {
            padding: var(--space-sm) var(--space-lg);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: all var(--time-quick);
        }
        app-frame .tab:hover { color: var(--text-primary); }
        app-frame .tab.active {
            background: var(--accent-bg);
            color: var(--accent-text);
        }
        app-frame .host {
            flex: 1;
            min-height: 0;
            display: flex;
            position: relative;
        }
        app-frame .host > * {
            flex: 1;
            min-width: 0;
            min-height: 0;
        }
    `;

    init({ api, signals }) {
        this.constructor._injectStyles();
        this.api = api;
        this.signals = signals;
        this.activeWorld = null;
        this.currentWorldName = null;
        this.currentPersonaId = null;
        this.menuOpen = false;
        this.personas = [];

        this.innerHTML = `
            <div class="header">
                <button class="picker" type="button">
                    <span class="name">—</span>
                    <span class="caret">▾</span>
                </button>
                <div class="menu" hidden></div>
                <div class="spacer"></div>
                <nav class="tabs">
                    <button class="tab" type="button" data-world="outer">chat</button>
                    <button class="tab" type="button" data-world="inner">inner</button>
                    <button class="tab" type="button" data-world="status">status</button>
                </nav>
            </div>
            <div class="host"></div>
        `;

        const picker = this.querySelector('.picker');
        const menu = this.querySelector('.menu');
        picker.addEventListener('click', (e) => { e.stopPropagation(); this.toggleMenu(); });
        menu.addEventListener('click', (e) => e.stopPropagation());
        document.addEventListener('click', () => this.closeMenu());

        this.querySelectorAll('.tab').forEach((btn) => {
            btn.addEventListener('click', () => {
                if (!this.currentPersonaId) return;
                const w = btn.dataset.world;
                if (w === 'outer') this.api.goToOuter(this.currentPersonaId);
                else if (w === 'inner') this.api.goToInner(this.currentPersonaId);
                else if (w === 'status') this.api.goToStatus(this.currentPersonaId);
            });
        });

        this.signals.addEventListener('signal', (e) => {
            const { title } = e.detail || {};
            if (title === 'persona updated' || title === 'persona became sick' || title === 'persona deleted') {
                this.refreshPersonas();
            }
        });

        return this;
    }

    async show(worldName, params = {}) {
        if (this.activeWorld) {
            this.activeWorld.deactivate();
            this.activeWorld.remove();
            this.activeWorld = null;
        }

        this.currentWorldName = worldName;
        this.currentPersonaId = params.id || null;
        this.toggleAttribute('no-header', worldName === 'chooser' || worldName === 'create' || worldName === 'migrate');

        const tag = `${worldName}-world`;
        const world = document.createElement(tag);
        world.init({ api: this.api, signals: this.signals, ...params });
        this.querySelector('.host').appendChild(world);
        await world.activate();
        this.activeWorld = world;

        await this.refreshPersonas();
        this.renderHeader();
    }

    async refreshPersonas() {
        this.personas = await this.api.listPersonas();
        this.renderHeader();
    }

    renderHeader() {
        const persona = this.personas.find((p) => p.id === this.currentPersonaId);
        this.querySelector('.picker .name').textContent = persona?.name || '—';

        this.querySelectorAll('.tab').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.world === this.currentWorldName);
        });

        if (this.menuOpen) this.renderMenu();
    }

    toggleMenu() {
        this.menuOpen = !this.menuOpen;
        const menu = this.querySelector('.menu');
        if (this.menuOpen) {
            menu.hidden = false;
            this.renderMenu();
        } else {
            menu.hidden = true;
        }
    }

    closeMenu() {
        if (!this.menuOpen) return;
        this.menuOpen = false;
        this.querySelector('.menu').hidden = true;
    }

    renderMenu() {
        const menu = this.querySelector('.menu');
        menu.innerHTML = '';
        for (const p of this.personas) {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'menu-item' + (p.id === this.currentPersonaId ? ' current' : '');
            item.textContent = p.name;
            item.addEventListener('click', () => {
                this.closeMenu();
                this.api.goToOuter(p.id);
            });
            menu.appendChild(item);
        }
        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'menu-item add';
        add.textContent = '+ Add new persona';
        add.addEventListener('click', () => {
            this.closeMenu();
            this.api.goToSetup();
        });
        menu.appendChild(add);
    }
}

customElements.define('app-frame', AppFrame);
export default AppFrame;
