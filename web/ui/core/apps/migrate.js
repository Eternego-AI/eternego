import App from './app.js';
import '../../platform/layouts/step-form.js';

class Migrate extends App {
    async start() {
        this.step = 0;
        this.values = {};
        this.error = null;
        this.submitting = false;
        this.expanded = { vision: false, teacher: false };

        try { this.providers = await this._props.api.getProviderConfig(); }
        catch { this.providers = {}; }

        this._el = document.createElement('step-form');
        this.render();
    }

    render() {
        const p = this.providers || {};
        const steps = [
            {
                title: 'Diary',
                subtitle: 'Her memories live in a single file, sealed by the phrase you saved when she was first created.',
                fields: [
                    { name: 'diary', type: 'file', label: 'Diary file', accept: '.diary', required: true, help: 'The .diary file from her last home — notes, destiny, the meanings she has learned.' },
                    { name: 'phrase', type: 'text', label: 'Recovery phrase', placeholder: 'the words you saved when she was created', required: true, help: 'Words shown on her first day. Without them, the diary stays sealed.' },
                ],
            },
            {
                title: 'Mind',
                subtitle: 'Where her thoughts come from. She uses this model for everything — recognizing, deciding, reflecting, remembering.',
                fields: [
                    { name: 'thinking_provider', type: 'options', label: 'Provider', help: 'Local runs on your machine through Ollama. Anthropic, OpenAI-compatible, and xAI run in the cloud and need a key.', options: [
                        { value: 'local', label: 'Local (Ollama)' },
                        { value: 'anthropic', label: 'Anthropic' },
                        { value: 'openai', label: 'OpenAI compatible' },
                        { value: 'xai', label: 'xAI (Grok)' },
                    ]},
                    { name: 'thinking_model', type: 'text', label: 'Model', placeholder: 'qwen2.5:7b', required: true, help: 'The exact model name your provider exposes.' },
                    { name: 'thinking_url', type: 'text', label: 'URL', placeholder: p.local?.url || 'http://localhost:11434', help: 'Where the model lives. Defaults to Ollama on localhost.' },
                    { name: 'thinking_api_key', type: 'text', label: 'API key', placeholder: 'optional', help: 'Required for cloud providers. Stays on your machine.' },
                ],
            },
            {
                title: 'Vision',
                subtitle: "If you want her to see images, her mind needs vision. Most frontier and cloud models already do — for those, skip this. For minds without it, give her a separate vision model. Without either, she'll politely say she can't see.",
                ...(this.expanded.vision ? {
                    fields: [
                        { name: 'vision_provider', type: 'options', label: 'Provider', options: [
                            { value: 'local', label: 'Local' },
                            { value: 'anthropic', label: 'Anthropic' },
                            { value: 'openai', label: 'OpenAI compatible' },
                            { value: 'xai', label: 'xAI (Grok)' },
                        ]},
                        { name: 'vision_model', type: 'text', label: 'Model', placeholder: 'llava, claude-haiku-4-5...' },
                        { name: 'vision_url', type: 'text', label: 'URL', placeholder: p.local?.url || '' },
                        { name: 'vision_api_key', type: 'text', label: 'API key', placeholder: 'optional' },
                    ],
                } : {
                    optional: {
                        prompt: 'Give her vision',
                        onAdd: () => { this.expanded.vision = true; this.render(); },
                    },
                }),
            },
            {
                title: 'Teacher',
                subtitle: "When she meets a moment she's never seen, the teacher explains the principle behind it. She translates the lesson into her own voice and remembers. Without one, she'll simply say she doesn't know yet.",
                ...(this.expanded.teacher ? {
                    fields: [
                        { name: 'frontier_provider', type: 'options', label: 'Provider', options: [
                            { value: 'local', label: 'Local (Ollama)' },
                            { value: 'anthropic', label: 'Anthropic' },
                            { value: 'openai', label: 'OpenAI compatible' },
                            { value: 'xai', label: 'xAI (Grok)' },
                        ]},
                        { name: 'frontier_model', type: 'text', label: 'Model', placeholder: 'claude-opus-4-7, qwen2.5:32b...' },
                        { name: 'frontier_url', type: 'text', label: 'URL', placeholder: p.local?.url || '' },
                        { name: 'frontier_api_key', type: 'text', label: 'API key', placeholder: 'optional' },
                    ],
                } : {
                    optional: {
                        prompt: 'Give her a teacher',
                        onAdd: () => { this.expanded.teacher = true; this.render(); },
                    },
                }),
            },
            {
                title: 'Channels',
                subtitle: 'Where she can be reached besides this app. Telegram and Discord today — more to come.',
                fields: [
                    { name: 'telegram_token', type: 'text', label: 'Telegram bot token', help: 'Create a bot via @BotFather on Telegram and paste its token here.' },
                    { name: 'discord_token', type: 'text', label: 'Discord bot token', help: 'Create an application at discord.com/developers, add a bot, and paste its token.' },
                ],
            },
        ];

        this._el.init({
            steps,
            current: this.step,
            values: this.values,
            error: this.error,
            submitting: this.submitting,
            onStepChange: (s) => { this.step = s; this.error = null; this.render(); },
            onCancel: () => this._props.onCancel && this._props.onCancel(),
            onSubmit: () => this.submit(),
        });
    }

    async submit() {
        const v = this.values;
        if (!v.diary || !v.phrase) {
            this.error = 'Diary file and recovery phrase are required.';
            this.step = 0;
            this.render();
            return;
        }
        this.submitting = true;
        this.error = null;
        this.render();

        const form = new FormData();
        form.append('diary', v.diary);
        form.append('phrase', v.phrase);
        if (v.thinking_provider) form.append('provider', v.thinking_provider);
        form.append('model', v.thinking_model);
        if (v.thinking_url) form.append('url', v.thinking_url);
        if (v.thinking_api_key) form.append('api_key', v.thinking_api_key);
        if (v.vision_model) {
            form.append('vision_model', v.vision_model);
            if (v.vision_provider) form.append('vision_provider', v.vision_provider);
            if (v.vision_url) form.append('vision_url', v.vision_url);
            if (v.vision_api_key) form.append('vision_api_key', v.vision_api_key);
        }
        if (v.frontier_model) {
            form.append('frontier_model', v.frontier_model);
            if (v.frontier_provider) form.append('frontier_provider', v.frontier_provider);
            if (v.frontier_url) form.append('frontier_url', v.frontier_url);
            if (v.frontier_api_key) form.append('frontier_api_key', v.frontier_api_key);
        }
        if (v.telegram_token) form.append('telegram_token', v.telegram_token);
        if (v.discord_token) form.append('discord_token', v.discord_token);

        const result = await this._props.api.migratePersona(form);
        if (result.success) {
            this._props.onDone && this._props.onDone(result.persona_id);
        } else {
            this.error = result.error || 'Migration failed.';
            this.submitting = false;
            this.render();
        }
    }
}

export default Migrate;
