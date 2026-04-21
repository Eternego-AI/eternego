import App from './app.js';

export default class SetupSpeaker extends App {
    static appId = 'setup-speaker';
    static appName = 'Setup';

    start() {
        this._providers = {
            local: { url: 'http://localhost:11434' },
            anthropic: { url: 'https://api.anthropic.com' },
            openai: { url: 'https://api.openai.com' },
        };
    }

    async run(stream) {
        this._stream = stream;
        const api = this._props.api;
        if (api.fetchProviderConfig) {
            try { this._providers = await api.fetchProviderConfig(); } catch {}
        }

        stream.say([
            { type: 'text', text: 'Welcome.' },
            { type: 'markdown', markdown: 'I can **create a new persona** with you or **restore one** from a diary backup.' },
        ]);

        const action = await stream.ask({
            type: 'options',
            props: {
                options: [
                    { id: 'create', label: 'Create a new persona' },
                    { id: 'migrate', label: 'Restore from diary' },
                ],
            },
        });
        stream.echo([{ type: 'text', text: action === 'create' ? 'Create a new persona' : 'Restore from diary' }]);

        if (action === 'create') return this._createFlow();
        return this._migrateFlow();
    }

    async _createFlow() {
        const stream = this._stream;

        stream.say([{ type: 'text', text: 'What should we call your persona?' }]);
        const name = await stream.ask({ type: 'text', props: { placeholder: 'Name', submitLabel: 'Next' } });
        stream.echo([{ type: 'text', text: name }]);

        const thinking = await this._askModel('thinking', {
            intro: [
                { type: 'text', text: `Now, the thinking model — ${name}'s core cognition.` },
                { type: 'markdown', markdown: 'Pick where it lives.' },
            ],
            localHint: 'Runs on your machine via Ollama. Nothing leaves your hardware.',
            remoteHint: 'A frontier-quality model reached through an API. Fastest to start with.',
            required: true,
        });

        const vision = await this._askModel('vision', {
            intro: [
                { type: 'text', text: `Vision model — optional.` },
                { type: 'markdown', markdown: 'Used when your persona receives images. Skip to fall back to the thinking model.' },
            ],
            localHint: 'A local vision model like llava.',
            remoteHint: 'A remote model with vision support.',
            required: false,
        });

        stream.say([
            { type: 'text', text: 'How should people reach your persona?' },
        ]);
        const channelType = await stream.ask({
            type: 'options',
            props: {
                options: [
                    { id: 'telegram', label: 'Telegram', hint: 'via a bot you control' },
                    { id: 'web', label: 'Web only', hint: 'no external channel' },
                ],
            },
        });
        stream.echo([{ type: 'text', text: channelType === 'telegram' ? 'Telegram' : 'Web only' }]);

        let botToken = '';
        if (channelType === 'telegram') {
            stream.say([
                { type: 'markdown', markdown: 'Open **@BotFather** on Telegram, send `/newbot`, and paste the token here.' },
            ]);
            botToken = await stream.ask({ type: 'text', props: { placeholder: '123456:ABC-DEF...', submitLabel: 'Next' } });
            stream.echo([{ type: 'text', text: '•••• token received' }]);
        }

        const frontier = await this._askModel('frontier', {
            intro: [
                { type: 'text', text: 'Frontier model — optional.' },
                { type: 'markdown', markdown: 'A stronger model your persona reaches for when it hits the limits of its own mind. Skip to leave unset.' },
            ],
            localHint: 'A larger local model.',
            remoteHint: 'Typically Claude Opus or similar.',
            required: false,
        });

        stream.say([{ type: 'text', text: 'Bringing it all together…' }]);

        const body = this._buildCreateBody({ name, thinking, vision, channelType, botToken, frontier });
        const result = await this._props.api.createPersona(body);

        if (!result.success) {
            stream.say([
                { type: 'markdown', markdown: `I couldn't create the persona: **${result.message || 'unknown error'}**` },
            ]);
            return;
        }

        const personaId = result.persona_id;

        stream.say([
            { type: 'text', text: `${name} is alive.` },
            { type: 'markdown', markdown: `Here is the **recovery phrase**. Write it down and keep it safe — you need it to restore this persona later.` },
            { type: 'markdown', markdown: '```\n' + (result.recovery_phrase || '') + '\n```' },
        ]);
        await stream.ask({
            type: 'options',
            props: { options: [{ id: 'saved', label: 'I saved my phrase' }] },
        });
        stream.echo([{ type: 'text', text: 'I saved my phrase' }]);

        if (channelType === 'telegram') {
            stream.say([
                { type: 'text', text: 'Last step — pair the Telegram bot.' },
                { type: 'markdown', markdown: 'Send any message to your bot on Telegram. It will reply with a pairing code. Paste it below.' },
            ]);
            const pairing = await stream.ask({
                type: 'text',
                props: { placeholder: 'Pairing code', submitLabel: 'Pair' },
            });
            stream.echo([{ type: 'text', text: pairing }]);
            const pairRes = await this._props.api.pairChannel(pairing, personaId);
            if (!pairRes.success) {
                stream.say([{ type: 'markdown', markdown: `Pairing didn't go through: **${pairRes.message || 'unknown error'}**. You can pair from the persona's settings later.` }]);
            } else {
                stream.say([{ type: 'text', text: 'Paired.' }]);
            }
        }

        stream.say([{ type: 'text', text: `All set. Entering ${name}'s world.` }]);
        if (this._props.onCreated) this._props.onCreated(personaId);
    }

    async _migrateFlow() {
        const stream = this._stream;

        stream.say([
            { type: 'text', text: 'Drop the diary file.' },
            { type: 'markdown', markdown: 'Your persona backup — the `.diary` file you exported previously.' },
        ]);
        const file = await stream.ask({
            type: 'dropzone',
            props: { label: 'Choose or drop a diary file', submitLabel: 'Use this file' },
        });
        stream.echo([{ type: 'text', text: file.name }]);

        stream.say([{ type: 'text', text: 'Recovery phrase?' }]);
        const phrase = await stream.ask({
            type: 'text',
            props: { placeholder: 'Enter your recovery phrase', multiline: true, submitLabel: 'Next' },
        });
        stream.echo([{ type: 'text', text: '•••• phrase received' }]);

        const thinking = await this._askModel('thinking', {
            intro: [
                { type: 'text', text: 'The thinking model to wake this persona on.' },
                { type: 'markdown', markdown: 'Pick where it lives.' },
            ],
            localHint: 'Runs on your machine via Ollama.',
            remoteHint: 'A frontier-quality model reached through an API.',
            required: true,
        });

        const vision = await this._askModel('vision', {
            intro: [
                { type: 'text', text: 'Vision model — optional.' },
                { type: 'markdown', markdown: 'Skip to fall back to the thinking model.' },
            ],
            localHint: 'A local vision model.',
            remoteHint: 'A remote vision-capable model.',
            required: false,
        });

        const frontier = await this._askModel('frontier', {
            intro: [
                { type: 'text', text: 'Frontier model — optional.' },
                { type: 'markdown', markdown: 'Skip to leave unset.' },
            ],
            localHint: 'A larger local model.',
            remoteHint: 'Typically Claude Opus or similar.',
            required: false,
        });

        stream.say([{ type: 'text', text: 'Restoring…' }]);

        const form = this._buildMigrateForm({ file, phrase, thinking, vision, frontier });
        const result = await this._props.api.migratePersona(form);

        if (!result.success) {
            stream.say([{ type: 'markdown', markdown: `I couldn't restore the persona: **${result.message || 'unknown error'}**` }]);
            return;
        }

        stream.say([{ type: 'text', text: 'Restored. Entering their world.' }]);
        if (this._props.onCreated) this._props.onCreated(result.persona_id);
    }

    async _askModel(slot, { intro, localHint, remoteHint, required }) {
        const stream = this._stream;
        stream.say(intro);

        const providerOptions = [
            { id: 'local', label: 'Local (Ollama)', hint: localHint },
            { id: 'anthropic', label: 'Claude', hint: remoteHint },
            { id: 'openai', label: 'OpenAI-compatible', hint: 'ChatGPT, NVIDIA NIM, Together, Groq…' },
        ];
        const provider = await stream.ask({
            type: 'options',
            props: {
                options: providerOptions,
                canSkip: !required,
                skipLabel: 'Skip',
            },
        });
        if (provider == null) {
            stream.echo([{ type: 'text', text: 'Skip' }]);
            return null;
        }
        const providerLabel = providerOptions.find(o => o.id === provider)?.label || provider;
        stream.echo([{ type: 'text', text: providerLabel }]);

        const defaultUrl = (this._providers[provider] || {}).url || '';

        if (provider === 'local') {
            stream.say([{ type: 'markdown', markdown: 'Ollama endpoint and the model name (e.g. `qwen2.5:7b`).' }]);
            const fields = await stream.ask({
                type: 'composite',
                props: {
                    fields: [
                        { name: 'url', label: 'URL', placeholder: 'http://localhost:11434', value: defaultUrl },
                        { name: 'model', label: 'Model', placeholder: 'qwen2.5:7b' },
                    ],
                    submitLabel: 'Next',
                },
            });
            stream.echo([{ type: 'text', text: fields.model }]);
            return { provider: null, url: fields.url, model: fields.model, key: '' };
        }

        stream.say([{ type: 'markdown', markdown: 'Endpoint, model name, and API key.' }]);
        const fields = await stream.ask({
            type: 'composite',
            props: {
                fields: [
                    { name: 'url', label: 'URL', placeholder: '', value: defaultUrl },
                    { name: 'model', label: 'Model', placeholder: provider === 'anthropic' ? 'claude-sonnet-4-20250514' : 'gpt-4o' },
                    { name: 'key', label: 'API Key', placeholder: 'sk-…', password: true },
                ],
                submitLabel: 'Next',
            },
        });
        stream.echo([{ type: 'text', text: fields.model }]);
        return { provider, url: fields.url, model: fields.model, key: fields.key };
    }

    _buildCreateBody({ name, thinking, vision, channelType, botToken, frontier }) {
        const body = {
            name,
            thinking_model: thinking.model,
            thinking_url: thinking.url,
            channel_type: channelType,
            channel_credentials: channelType === 'telegram' ? { token: botToken } : {},
        };
        if (thinking.provider) {
            body.thinking_provider = thinking.provider;
            body.thinking_api_key = thinking.key;
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
        return body;
    }

    _buildMigrateForm({ file, phrase, thinking, vision, frontier }) {
        const form = new FormData();
        form.append('diary', file);
        form.append('phrase', phrase);
        form.append('model', thinking.model);
        if (thinking.url) form.append('url', thinking.url);
        if (thinking.provider) {
            form.append('provider', thinking.provider);
            form.append('api_key', thinking.key);
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
        return form;
    }
}
