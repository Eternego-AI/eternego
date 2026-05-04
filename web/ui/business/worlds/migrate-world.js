import World from './world.js';
import Migrate from '../../core/apps/migrate.js';

class MigrateWorld extends World {
    static _styled = false;
    static _css = `
        migrate-world {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100%;
            padding: var(--space-3xl) var(--space-xl);
            background: var(--bg-deep);
            box-sizing: border-box;
        }
        migrate-world > * {
            width: 100%;
            max-width: 560px;
        }
    `;

    build() {
        const { api } = this._props;
        this.api = api;
        this.app = null;
    }

    async activate() {
        if (this.app) return;
        this.app = new Migrate();
        await this.app.init({
            api: this.api,
            onDone: (id) => this.api.goToOuter(id),
            onCancel: () => this.api.goToSetup(),
        });
        this.appendChild(this.app.el);
    }

    deactivate() {
        if (this.app && this.app.el) this.app.el.remove();
        this.app = null;
    }
}

customElements.define('migrate-world', MigrateWorld);
export default MigrateWorld;
