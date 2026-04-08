import App from './app.js';

export default class SetupApp extends App {
    static appId = 'setup';
    static appName = 'Setup';

    // init({ api, onDone(personaId), onCancel() })
    start() {
        this._el = document.createElement('div');
        this._el.id = 'setup-app';
        this._el.style.cssText = 'position:fixed;inset:0;justify-content:center;align-items:center;background:radial-gradient(ellipse at 50% 50%,rgba(140,160,255,0.03) 0%,transparent 60%),var(--bg);';

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'width:100%;max-width:460px;';

        this._setup = document.createElement('setup-widget');
        this._setup.init({
            onCreate: (data) => this._create(data),
            onMigrate: (data) => this._migrate(data),
            onPrepare: (model) => this._props.api.prepareEnvironment(model),
            onPair: (code) => this._props.api.pairChannel(code),
            onDone: (personaId) => {
                if (this._props.onDone) this._props.onDone(personaId);
            },
            onCancel: () => {
                if (this._props.onCancel) this._props.onCancel();
            },
        });

        wrapper.appendChild(this._setup);
        this._el.appendChild(wrapper);
    }

    reset() {
        this._setup._renderChoice();
        this._setup._step.go('choice');
    }

    async _create(data) {
        const body = {
            name: data.name,
            thinking_model: data.thinkingModel,
            channel_type: data.botToken ? 'telegram' : 'web',
            channel_credentials: data.botToken ? { token: data.botToken } : {},
        };
        if (data.thinkingProvider) {
            body.thinking_provider = data.thinkingProvider;
            body.thinking_credentials = { api_key: data.thinkingKey };
        }
        if (data.frontierModel) {
            body.frontier_model = data.frontierModel;
            body.frontier_provider = 'anthropic';
            body.frontier_credentials = { api_key: data.frontierKey };
        }
        return await this._props.api.createPersona(body);
    }

    async _migrate(data) {
        const form = new FormData();
        form.append('diary', data.file);
        form.append('phrase', data.phrase);
        form.append('model', data.model);
        return await this._props.api.migratePersona(form);
    }
}
