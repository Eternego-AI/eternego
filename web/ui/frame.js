/**
 * Frame — the visual shell.
 *
 * Header at the top: persona name (with dropdown picker), state badge,
 * mode tabs (chat / inner / status). Modes fill the remaining viewport.
 * No bottom switcher — chat input owns the bottom strip alone.
 */
import UI from './index.js';

class Frame extends HTMLElement {
    static _styled = false;

    static _css = `
        ui-frame { display: contents; }
        ui-frame > .ui-mode { display: none !important; }

        /* Outer stays beneath inner so the orb is visible through the fade */
        ui-frame[data-mode="outer"] > .ui-mode-outer,
        ui-frame[data-mode="inner"] > .ui-mode-outer { display: flex !important; }
        ui-frame[data-mode="inner"] > .ui-mode-outer { opacity: 0; pointer-events: none; }
        ui-frame[data-mode="inner"] > .ui-mode-inner { display: flex !important; }

        ui-frame[data-mode="setup"] > .ui-mode-setup { display: flex !important; }
        ui-frame[data-mode="status"] > .ui-mode-status { display: flex !important; }
        ui-frame[data-mode="welcome"] > .ui-mode-welcome { display: flex !important; }

        /* Header — hidden during setup and welcome */
        .ui-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 56px;
            z-index: 60;
            display: none;
            align-items: center;
            justify-content: space-between;
            padding: 0 var(--space-xl);
            background: linear-gradient(to bottom, rgba(11, 11, 20, 0.96) 60%, rgba(11, 11, 20, 0.7) 90%, transparent);
            border-bottom: 1px solid var(--border-subtle);
            backdrop-filter: blur(8px);
        }
        ui-frame[data-mode="outer"] .ui-header,
        ui-frame[data-mode="inner"] .ui-header,
        ui-frame[data-mode="status"] .ui-header { display: flex; }

        /* Push mode content below the header */
        ui-frame[data-mode="outer"] > .ui-mode-outer,
        ui-frame[data-mode="inner"] > .ui-mode-outer,
        ui-frame[data-mode="inner"] > .ui-mode-inner,
        ui-frame[data-mode="status"] > .ui-mode-status { top: 56px !important; }

        .ui-header-left {
            position: relative;
            display: flex;
            align-items: center;
        }

        /* Persona picker (left side of header) */
        .ui-persona-pick {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 6px 12px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-family: var(--font);
            font-size: 15px;
            cursor: pointer;
            transition: border-color 0.2s, background 0.2s;
        }
        .ui-persona-pick:hover {
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }
        .ui-persona-name {
            font-weight: 500;
            letter-spacing: 0.5px;
            color: var(--warm-text);
        }
        .ui-persona-state {
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            padding: 3px 8px;
            border-radius: var(--radius-sm);
            background: var(--surface-recessed);
            color: var(--text-muted);
            border: 1px solid var(--border-subtle);
        }
        .ui-persona-state.active {
            background: var(--vital-bg);
            color: var(--vital-text);
            border-color: var(--vital-border);
        }
        .ui-persona-state.sick {
            background: var(--destructive-bg);
            color: var(--destructive-text);
            border-color: var(--destructive-border);
        }
        .ui-persona-state.hibernate {
            background: var(--surface-recessed);
            color: var(--text-muted);
            border-color: var(--border-default);
        }
        .ui-persona-caret {
            font-size: 11px;
            color: var(--text-secondary);
        }
        .ui-persona-menu {
            position: absolute;
            top: 50px;
            left: 0;
            min-width: 240px;
            padding: 8px;
            background: var(--surface-overlay);
            border: 1px solid var(--border-hover);
            border-radius: var(--radius-md);
            box-shadow: 0 16px 48px rgba(0,0,0,0.6);
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 2px;
            z-index: 70;
        }
        .ui-persona-menu[hidden] { display: none; }
        .ui-persona-item {
            text-align: left;
            padding: 10px 14px;
            background: none;
            border: none;
            border-radius: var(--radius-sm);
            color: var(--text-body);
            font-family: var(--font);
            font-size: var(--text-base);
            cursor: pointer;
            transition: background 0.15s, color 0.15s;
        }
        .ui-persona-item:hover {
            background: var(--surface-active);
            color: var(--text-primary);
        }
        .ui-persona-item.current {
            color: var(--warm-text);
            background: var(--warm-bg);
        }
        .ui-persona-divider {
            height: 1px;
            background: var(--border-subtle);
            margin: 6px 4px;
        }
        .ui-persona-add {
            color: var(--accent-text);
            font-size: var(--text-sm);
        }
        .ui-persona-add:hover {
            background: var(--accent-bg);
            color: var(--text-primary);
        }

        /* Mode tabs (right side of header) */
        .ui-mode-tabs {
            display: inline-flex;
            gap: 2px;
            padding: 3px;
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
        }
        .ui-mode-tab {
            padding: 6px 16px;
            background: none;
            border: none;
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: 13px;
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: background 0.15s, color 0.15s;
        }
        .ui-mode-tab:hover { color: var(--text-primary); }
        .ui-mode-tab.active {
            background: var(--accent-bg);
            color: var(--accent-text);
        }

        /* Welcome */
        .ui-mode-welcome {
            position: fixed;
            inset: 0;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: var(--space-xl);
            cursor: pointer;
            background:
                radial-gradient(ellipse at 75% 50%, rgba(140,160,255,0.03) 0%, transparent 50%),
                radial-gradient(ellipse at 30% 50%, rgba(140,160,255,0.015) 0%, transparent 60%),
                var(--bg);
        }
        .ui-welcome-orb {
            width: 80px; height: 80px;
            border-radius: var(--radius-full);
            border: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--text-lg);
            color: var(--text-dim);
            transition: border-color 0.6s, color 0.6s, box-shadow 0.6s;
            animation: ui-wait 4s ease-in-out infinite;
        }
        @keyframes ui-wait {
            0%, 100% { border-color: var(--border-subtle); }
            50% { border-color: var(--border-default); }
        }
        .ui-mode-welcome:hover .ui-welcome-orb {
            color: var(--accent-text);
            border-color: var(--accent-border);
            box-shadow: 0 0 40px rgba(140,160,255,0.06);
            animation: none;
        }
        .ui-welcome-text {
            font-size: var(--text-base);
            color: var(--text-dim);
            letter-spacing: 1px;
            opacity: 0;
            transition: opacity 0.4s;
        }
        .ui-mode-welcome:hover .ui-welcome-text { opacity: 1; }
    `;

    static _injectStyles() {
        if (this._styled) return;
        this._styled = true;
        const s = document.createElement('style');
        s.textContent = this._css;
        document.head.appendChild(s);
    }

    init() {
        this.constructor._injectStyles();
        this._activeMode = null;
        this._menuOpen = false;

        // Modes
        this._outerWorld = document.createElement('outer-world');
        this._outerWorld.className = 'ui-mode ui-mode-outer';
        this._outerWorld.init({
            api: UI._api(),
            signals: UI.signals,
            onEnterInner: () => UI.enterInnerWorld(),
        });

        this._innerWorld = document.createElement('inner-world');
        this._innerWorld.className = 'ui-mode ui-mode-inner';
        this._innerWorld.init({
            api: UI._api(),
            signals: UI.signals,
            onExitInner: () => UI.enterOuterWorld(UI.currentPersonaId),
        });

        this._setupView = this._createSetupView();
        this._setupView.el.classList.add('ui-mode', 'ui-mode-setup');

        this._status = document.createElement('status-world');
        this._status.init({ api: UI._api(), signals: UI.signals });
        this._status.classList.add('ui-mode', 'ui-mode-status');

        this._welcome = document.createElement('div');
        this._welcome.className = 'ui-mode ui-mode-welcome';
        this._welcome.innerHTML = `
            <div class="ui-welcome-orb">+</div>
            <div class="ui-welcome-text">begin</div>
        `;
        this._welcome.addEventListener('click', () => UI.enterSetup());

        this.appendChild(this._outerWorld);
        this.appendChild(this._innerWorld);
        this.appendChild(this._setupView.el);
        this.appendChild(this._status);
        this.appendChild(this._welcome);

        // Header
        this._header = document.createElement('div');
        this._header.className = 'ui-header';
        this._header.innerHTML = `
            <div class="ui-header-left">
                <button class="ui-persona-pick" type="button" data-pick>
                    <span class="ui-persona-name">—</span>
                    <span class="ui-persona-state"></span>
                    <span class="ui-persona-caret">▾</span>
                </button>
                <div class="ui-persona-menu" hidden></div>
            </div>
            <nav class="ui-mode-tabs">
                <button class="ui-mode-tab" type="button" data-tab="chat">chat</button>
                <button class="ui-mode-tab" type="button" data-tab="inner">inner</button>
                <button class="ui-mode-tab" type="button" data-tab="status">status</button>
            </nav>
        `;
        this.appendChild(this._header);

        const pick = this._header.querySelector('[data-pick]');
        const menu = this._header.querySelector('.ui-persona-menu');
        pick.addEventListener('click', (e) => { e.stopPropagation(); this._toggleMenu(); });
        menu.addEventListener('click', (e) => e.stopPropagation());
        document.addEventListener('click', () => this._closeMenu());

        this._header.querySelectorAll('[data-tab]').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                if (tab === 'chat' && UI.currentPersonaId) UI.enterOuterWorld(UI.currentPersonaId);
                else if (tab === 'inner') UI.enterInnerWorld();
                else if (tab === 'status') UI.enterStatus();
            });
        });

        // Mode change reactor
        UI.onModeChange((detail) => {
            if (this._activeMode === 'outer') this._outerWorld.deactivate();
            if (this._activeMode === 'inner') this._innerWorld.deactivate();
            if (this._activeMode === 'status') this._status.deactivate();

            this.setAttribute('data-mode', detail.mode);
            this._activeMode = detail.mode;

            if (detail.mode === 'outer') {
                this._outerWorld.setPersona(detail.personaId);
                this._outerWorld.activate();
            } else if (detail.mode === 'inner') {
                const name = detail.persona?.name || '';
                const birthday = detail.persona?.birthday || null;
                this._innerWorld.show(detail.personaId, name, birthday, detail.data, detail.persona);
                this._innerWorld.activate();
            } else if (detail.mode === 'status') {
                this._status.setPersona(detail.personaId);
                this._status.activate();
            } else if (detail.mode === 'setup') {
                this._setupView.reset();
            }

            this._renderHeader();
        });

        // Refresh persona cache + header when state-relevant signals fire
        UI.signals.addEventListener('update', (e) => {
            let needsRefresh = false;
            for (const sig of e.detail) {
                const t = (sig.title || '').toLowerCase();
                if (t === 'persona updated' || t === 'persona became sick') {
                    needsRefresh = true;
                    break;
                }
            }
            if (needsRefresh) {
                UI.fetchPersonas().then(() => this._renderHeader());
            }
        });
    }

    _renderHeader() {
        const id = UI.currentPersonaId;
        const persona = UI.personas.find(p => p.id === id);
        const nameEl = this._header.querySelector('.ui-persona-name');
        const stateEl = this._header.querySelector('.ui-persona-state');

        if (persona) {
            nameEl.textContent = persona.name;
            const state = persona.running === false ? 'hibernate' : (persona.status || 'active');
            stateEl.textContent = state;
            stateEl.className = `ui-persona-state ${state}`;
        } else {
            nameEl.textContent = '—';
            stateEl.textContent = '';
            stateEl.className = 'ui-persona-state';
        }

        this._header.querySelectorAll('[data-tab]').forEach(btn => {
            const tab = btn.dataset.tab;
            const active = (tab === 'chat' && this._activeMode === 'outer')
                || (tab === 'inner' && this._activeMode === 'inner')
                || (tab === 'status' && this._activeMode === 'status');
            btn.classList.toggle('active', active);
        });

        if (this._menuOpen) this._renderMenu();
    }

    _toggleMenu() {
        this._menuOpen = !this._menuOpen;
        const menu = this._header.querySelector('.ui-persona-menu');
        if (this._menuOpen) {
            menu.hidden = false;
            this._renderMenu();
        } else {
            menu.hidden = true;
        }
    }

    _closeMenu() {
        if (!this._menuOpen) return;
        this._menuOpen = false;
        this._header.querySelector('.ui-persona-menu').hidden = true;
    }

    _renderMenu() {
        const menu = this._header.querySelector('.ui-persona-menu');
        menu.innerHTML = '';
        for (const p of UI.personas) {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'ui-persona-item' + (p.id === UI.currentPersonaId ? ' current' : '');
            item.textContent = p.name;
            item.addEventListener('click', () => {
                this._closeMenu();
                if (p.id !== UI.currentPersonaId || this._activeMode !== 'outer') {
                    UI.enterOuterWorld(p.id);
                }
            });
            menu.appendChild(item);
        }
        if (UI.personas.length > 0) {
            const sep = document.createElement('div');
            sep.className = 'ui-persona-divider';
            menu.appendChild(sep);
        }
        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'ui-persona-item ui-persona-add';
        add.textContent = '+ Add new persona';
        add.addEventListener('click', () => {
            this._closeMenu();
            UI.enterSetup();
        });
        menu.appendChild(add);
    }

    _createSetupView() {
        const setupApp = new UI._SetupApp();
        setupApp.init({
            api: UI._api(),
            onDone: (personaId) => {
                UI.fetchPersonas().then(() => UI.enterOuterWorld(personaId));
            },
            onCancel: () => {
                if (UI.personas.length > 0) {
                    UI.enterOuterWorld(UI.personas[0].id);
                } else {
                    UI._notifyModeChange({ mode: 'welcome' });
                }
            },
        });
        return setupApp;
    }
}

customElements.define('ui-frame', Frame);
export default Frame;
