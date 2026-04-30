import World from './world.js';
import Migrate from '../../core/apps/migrate.js';

class MigrateWorld extends World {
    static _styled = false;
    static _css = `
        migrate-world {
            display: flex;
            flex-direction: column;
            height: 100%;
            max-width: 720px;
            margin: 0 auto;
            padding: var(--space-3xl) var(--space-xl);
            background: var(--bg-deep);
            min-height: 0;
        }
    `;

    build() {
        const { api } = this._props;
        this.api = api;
        this.app = null;
    }

    activate() {
        if (this.app) return;
        this.app = new Migrate();
        this.app.init({
            api: this.api,
            onDone: (id) => this.api.goToOuter(id),
            onCancel: () => this.api.goToHome(),
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
