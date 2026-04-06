/**
 * Frame — the visual shell. CSS controls visibility via data-mode attribute.
 * JS sets the attribute. CSS does the rest.
 */
import UI from './index.js';

class Frame extends HTMLElement {
    static _styled = false;

    static _css = `
        /* Frame: layers stack, visibility via data-mode */
        ui-frame { display: contents; }
        ui-frame > .ui-mode { display: none !important; }

        /* Outer world: visible in outer AND inner mode (it stays beneath) */
        ui-frame[data-mode="outer"] > .ui-mode-outer,
        ui-frame[data-mode="inner"] > .ui-mode-outer { display: flex !important; }

        /* When inner is active, outer fades to reveal inner beneath */
        ui-frame[data-mode="inner"] > .ui-mode-outer { opacity: 0; pointer-events: none; }

        /* Inner world: centered, shown above faded outer */
        ui-frame[data-mode="inner"] > .ui-mode-inner { display: flex !important; }

        /* Setup and welcome: standalone */
        ui-frame[data-mode="setup"] > .ui-mode-setup { display: flex !important; }
        ui-frame[data-mode="welcome"] > .ui-mode-welcome { display: flex !important; }

        /* Switcher */
        .ui-switcher {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 50;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: var(--space-xs);
            padding: 0 0 var(--space-md);
        }
        .ui-tab {
            padding: var(--space-xs) var(--space-lg);
            border-radius: var(--radius-md);
            border: none;
            background: none;
            color: var(--text-dim);
            font-family: var(--font);
            font-size: var(--text-base);
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: color 0.25s var(--ease), background 0.25s var(--ease);
        }
        .ui-tab:hover { color: var(--text-secondary); }
        .ui-tab.active { color: var(--text-body); background: rgba(255,255,255,0.05); }
        .ui-tab-add {
            width: 24px; height: 24px;
            border-radius: var(--radius-full);
            border: 1px dashed var(--border-default);
            background: none;
            color: var(--text-dim);
            font-size: var(--text-base);
            font-family: var(--font);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: var(--space-xs);
            transition: color 0.2s, border-color 0.2s;
        }
        .ui-tab-add:hover { color: var(--text-secondary); border-color: var(--border-hover); }

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

        // Create all views upfront — CSS controls visibility
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
        this.appendChild(this._welcome);

        // Switcher
        this._switcher = document.createElement('div');
        this._switcher.className = 'ui-switcher';
        this.appendChild(this._switcher);
        this._renderSwitcher();

        // Listen for mode changes — one attribute change, CSS does the rest
        UI.onModeChange((detail) => {
            // Deactivate previous mode
            if (this._activeMode === 'outer') this._outerWorld.deactivate();
            if (this._activeMode === 'inner') this._innerWorld.deactivate();

            // Set data-mode — CSS shows the right view
            this.setAttribute('data-mode', detail.mode);
            this._activeMode = detail.mode;

            // Activate new mode
            if (detail.mode === 'outer') {
                this._outerWorld.setPersona(detail.personaId);
                this._outerWorld.activate();
            } else if (detail.mode === 'inner') {
                const name = detail.persona?.name || '';
                const birthday = detail.persona?.birthday || null;
                this._innerWorld.show(detail.personaId, name, birthday, detail.data);
                this._innerWorld.activate();
            } else if (detail.mode === 'setup') {
                this._setupView.reset();
            }

            this._renderSwitcher();
        });
    }

    _renderSwitcher() {
        this._switcher.innerHTML = '';
        for (const p of UI.personas) {
            const tab = document.createElement('button');
            tab.className = 'ui-tab';
            tab.textContent = p.name;
            if (UI.currentPersonaId === p.id) tab.classList.add('active');
            tab.addEventListener('click', () => {
                if (UI.currentPersonaId === p.id && UI.currentMode === 'outer') {
                    // Already on this persona's outer world — toggle to inner
                    UI.enterInnerWorld();
                } else if (UI.currentPersonaId === p.id && UI.currentMode === 'inner') {
                    // Already on this persona's inner world — toggle back to outer
                    UI.enterOuterWorld(p.id);
                } else {
                    // Different persona — go to outer world
                    UI.enterOuterWorld(p.id);
                }
            });
            this._switcher.appendChild(tab);
        }
        const add = document.createElement('button');
        add.className = 'ui-tab-add';
        add.textContent = '+';
        add.addEventListener('click', () => {
            if (UI.currentMode === 'setup') {
                if (UI.personas.length > 0) UI.enterOuterWorld(UI.personas[0].id);
            } else {
                UI.enterSetup();
            }
        });
        this._switcher.appendChild(add);
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
