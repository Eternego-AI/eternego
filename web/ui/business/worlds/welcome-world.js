import World from './world.js';

class WelcomeWorld extends World {
    static _styled = false;
    static _css = `
        welcome-world {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            gap: var(--space-3xl);
            background:
                radial-gradient(ellipse at 75% 50%, rgba(140,160,255,0.03) 0%, transparent 50%),
                radial-gradient(ellipse at 30% 50%, rgba(140,160,255,0.015) 0%, transparent 60%),
                var(--bg);
        }
        welcome-world .option {
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
        welcome-world .option:hover {
            background: var(--surface);
            border-color: var(--accent-border);
            box-shadow: 0 0 40px rgba(140,160,255,0.06);
        }
        welcome-world .orb {
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
            animation: welcome-pulse 4s ease-in-out infinite;
        }
        welcome-world .option:hover .orb {
            color: var(--accent-text);
            border-color: var(--accent-border);
            animation: none;
        }
        @keyframes welcome-pulse {
            0%, 100% { border-color: var(--border-subtle); }
            50%     { border-color: var(--border-default); }
        }
        welcome-world .title {
            font-size: var(--text-base);
            color: var(--text-secondary);
            letter-spacing: 1px;
        }
        welcome-world .option:hover .title { color: var(--text-primary); }
        welcome-world .sub {
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
            <button class="option new" type="button">
                <div class="orb">+</div>
                <div class="title">begin</div>
                <div class="sub">bring a new being to life</div>
            </button>
            <button class="option resume" type="button">
                <div class="orb">↥</div>
                <div class="title">resume</div>
                <div class="sub">restore from a diary</div>
            </button>
        `;
        this.querySelector('.new').addEventListener('click', () => api.goToSetup());
        this.querySelector('.resume').addEventListener('click', () => api.goToMigrate());
    }
}

customElements.define('welcome-world', WelcomeWorld);
export default WelcomeWorld;
