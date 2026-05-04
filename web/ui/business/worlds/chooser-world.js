import World from './world.js';

class ChooserWorld extends World {
    static _styled = false;
    static _css = `
        chooser-world {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100%;
            padding: var(--space-3xl) var(--space-xl);
            background:
                radial-gradient(ellipse at 75% 50%, rgba(140,160,255,0.03) 0%, transparent 50%),
                radial-gradient(ellipse at 30% 50%, rgba(140,160,255,0.015) 0%, transparent 60%),
                var(--bg);
            box-sizing: border-box;
            gap: var(--space-3xl);
        }
        chooser-world .intro {
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
            max-width: 560px;
            text-align: center;
        }
        chooser-world .intro .title {
            font-size: var(--text-lg);
            color: var(--text-primary);
            font-weight: 500;
        }
        chooser-world .intro .description {
            font-size: var(--text-base);
            color: var(--text-secondary);
            line-height: 1.7;
        }
        chooser-world .intro .description strong {
            color: var(--text-primary);
            font-weight: 500;
        }
        chooser-world .options {
            display: flex;
            gap: var(--space-3xl);
        }
        chooser-world .option {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--space-md);
            padding: var(--space-2xl);
            min-width: 240px;
            background: transparent;
            border: 1px solid transparent;
            border-radius: var(--radius-lg);
            cursor: pointer;
            transition: all var(--time-medium) var(--easing);
        }
        chooser-world .option:hover {
            background: var(--surface);
            border-color: var(--accent-border);
            box-shadow: 0 0 40px rgba(140,160,255,0.06);
        }
        chooser-world .orb {
            width: 80px;
            height: 80px;
            border-radius: var(--radius-full);
            border: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--text-lg);
            color: var(--text-dim);
            transition: all var(--time-medium);
            animation: chooser-pulse 4s ease-in-out infinite;
        }
        chooser-world .option:hover .orb {
            color: var(--accent-text);
            border-color: var(--accent-border);
            animation: none;
        }
        @keyframes chooser-pulse {
            0%, 100% { border-color: var(--border-subtle); }
            50%     { border-color: var(--border-default); }
        }
        chooser-world .option .label {
            font-size: var(--text-base);
            color: var(--text-secondary);
            letter-spacing: 1px;
        }
        chooser-world .option:hover .label { color: var(--text-primary); }
        chooser-world .option .sub {
            font-size: var(--text-xs);
            color: var(--text-dim);
            text-align: center;
            max-width: 200px;
            line-height: 1.5;
        }
    `;

    build() {
        const { api } = this._props;
        this.innerHTML = `
            <div class="intro">
                <div class="title">Bring a persona here</div>
                <div class="description">She lives on your hardware. She'll have a <strong>name</strong> she answers to and a <strong>mind</strong> that thinks for her. Optionally: <strong>vision</strong> to see images, a <strong>teacher</strong> for moments she doesn't yet know, and <strong>channels</strong> to reach beyond this app. Her memory is hers — and yours.</div>
            </div>
            <div class="options">
                <button class="option create" type="button">
                    <div class="orb">+</div>
                    <div class="label">Create</div>
                    <div class="sub">begin a new persona</div>
                </button>
                <button class="option restore" type="button">
                    <div class="orb">↥</div>
                    <div class="label">Restore</div>
                    <div class="sub">bring her back from a saved diary</div>
                </button>
            </div>
        `;
        this.querySelector('.create').addEventListener('click', () => api.goToCreate());
        this.querySelector('.restore').addEventListener('click', () => api.goToMigrate());
    }
}

customElements.define('chooser-world', ChooserWorld);
export default ChooserWorld;
