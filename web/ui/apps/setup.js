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
        wrapper.style.cssText = 'width:90%;max-width:640px;';

        this._setup = document.createElement('setup-widget');
        this._setup.init({
            api: this._props.api,
            onCreate: (data) => this._create(data),
            onMigrate: (data) => this._migrate(data),
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

    _resolvedVision(data) {
        if (data.visionUseThinking) {
            return {
                model: data.thinkingModel,
                url: data.thinkingUrl,
                provider: data.thinkingProvider,
                key: data.thinkingKey,
            };
        }
        if (!data.visionModel) return null;
        return {
            model: data.visionModel,
            url: data.visionUrl,
            provider: data.visionProvider,
            key: data.visionKey,
        };
    }

    _resolvedFrontier(data, resolvedVision) {
        if (data.frontierReuse === 'thinking') {
            return {
                model: data.thinkingModel,
                url: data.thinkingUrl,
                provider: data.thinkingProvider,
                key: data.thinkingKey,
            };
        }
        if (data.frontierReuse === 'vision' && resolvedVision) {
            return { ...resolvedVision };
        }
        if (!data.frontierModel) return null;
        return {
            model: data.frontierModel,
            url: data.frontierUrl,
            provider: data.frontierProvider,
            key: data.frontierKey,
        };
    }

    async _create(data) {
        const vision = this._resolvedVision(data);
        const frontier = this._resolvedFrontier(data, vision);

        const body = {
            name: data.name,
            thinking_model: data.thinkingModel,
            thinking_url: data.thinkingUrl,
        };
        if (data.thinkingProvider) {
            body.thinking_provider = data.thinkingProvider;
            body.thinking_api_key = data.thinkingKey;
        }
        if (vision) {
            body.vision_model = vision.model;
            if (vision.url) body.vision_url = vision.url;
            if (vision.provider) {
                body.vision_provider = vision.provider;
                body.vision_api_key = vision.key;
            }
        }
        if (frontier) {
            body.frontier_model = frontier.model;
            if (frontier.url) body.frontier_url = frontier.url;
            if (frontier.provider) {
                body.frontier_provider = frontier.provider;
                body.frontier_api_key = frontier.key;
            }
        }
        if (data.telegramToken) body.telegram_token = data.telegramToken;
        if (data.discordToken) body.discord_token = data.discordToken;

        return await this._props.api.createPersona(body);
    }

    async _migrate(data) {
        const vision = this._resolvedVision(data);
        const frontier = this._resolvedFrontier(data, vision);

        const form = new FormData();
        form.append('diary', data.file);
        form.append('phrase', data.phrase);
        form.append('model', data.thinkingModel);
        if (data.thinkingUrl) form.append('url', data.thinkingUrl);
        if (data.thinkingProvider) {
            form.append('provider', data.thinkingProvider);
            form.append('api_key', data.thinkingKey);
        }
        if (vision) {
            form.append('vision_model', vision.model);
            if (vision.url) form.append('vision_url', vision.url);
            if (vision.provider) {
                form.append('vision_provider', vision.provider);
                form.append('vision_api_key', vision.key);
            }
        }
        if (frontier) {
            form.append('frontier_model', frontier.model);
            if (frontier.url) form.append('frontier_url', frontier.url);
            if (frontier.provider) {
                form.append('frontier_provider', frontier.provider);
                form.append('frontier_api_key', frontier.key);
            }
        }
        if (data.telegramToken) form.append('telegram_token', data.telegramToken);
        if (data.discordToken) form.append('discord_token', data.discordToken);

        return await this._props.api.migratePersona(form);
    }
}
