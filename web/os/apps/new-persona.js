import App from './app.js';
import OS from '../index.js';
import { plus } from '../icons.js';

export default class NewPersonaApp extends App {
    static appId = 'new-persona';
    static appName = 'New';
    static icon = plus;

    // init({ signals: Feed })
    start() {
        const div = document.createElement('div');
        div.id = 'new-persona-app';

        const create = document.createElement('create-widget');
        create.init({
            models: () => OS.models,
            onCreated: (personaId) => {
                OS.fetchPersonas().then(() => OS.open('persona', { personaId }));
            },
        });

        const migrate = document.createElement('migrate-widget');
        migrate.init({
            models: () => OS.models,
            onMigrated: (personaId) => {
                OS.fetchPersonas().then(() => OS.open('persona', { personaId }));
            },
        });

        this._create = create;
        this._migrate = migrate;
        this._el = div;
        this._widgets = [create, migrate];
    }

    activate() {
        this._create.reset();
        this._migrate.reset();
        this._create.focusInput();
    }

    setFocused(widgetName) {
        for (const w of this._widgets) {
            const name = w.getAttribute('widget');
            if (w.setFocused) w.setFocused(name === widgetName);
        }
        if (widgetName === 'create') this._create.focusInput();
    }

    widgets() { return this._widgets; }
    get el() { return this._el; }
}
