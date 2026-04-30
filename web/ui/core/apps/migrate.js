import App from './app.js';
import '../../platform/layouts/step-form.js';

class Migrate extends App {
    async start() {
        this.step = 0;
        this.values = {};
        this.error = null;
        this.submitting = false;

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
                subtitle: 'Bring her back from a saved diary file.',
                fields: [
                    { name: 'diary', type: 'file', label: 'Diary file', accept: '.diary', required: true },
                    { name: 'phrase', type: 'text', label: 'Recovery phrase', placeholder: 'the words you saved when she was created', required: true },
                ],
            },
            {
                title: 'Mind',
                subtitle: 'The model that thinks for her.',
                fields: [
                    { name: 'thinking_provider', type: 'options', label: 'Provider', options: [
                        { value: 'local', label: 'Local (Ollama)' },
                        { value: 'anthropic', label: 'Anthropic' },
                        { value: 'openai', label: 'OpenAI compatible' },
                    ]},
                    { name: 'thinking_model', type: 'text', label: 'Model', placeholder: 'qwen2.5:7b', required: true },
                    { name: 'thinking_url', type: 'text', label: 'URL', placeholder: p.local?.url || 'http://localhost:11434' },
                    { name: 'thinking_api_key', type: 'text', label: 'API key', placeholder: 'optional' },
                ],
            },
            {
                title: 'Eyes',
                subtitle: 'Optional — skip if she does not need to see images yet.',
                fields: [
                    { name: 'vision_provider', type: 'options', label: 'Provider', options: [
                        { value: '', label: 'None' },
                        { value: 'local', label: 'Local' },
                        { value: 'anthropic', label: 'Anthropic' },
                        { value: 'openai', label: 'OpenAI compatible' },
                    ]},
                    { name: 'vision_model', type: 'text', label: 'Model' },
                    { name: 'vision_url', type: 'text', label: 'URL', placeholder: p.local?.url || '' },
                    { name: 'vision_api_key', type: 'text', label: 'API key' },
                ],
            },
            {
                title: 'Teacher',
                subtitle: 'Optional — a frontier model that teaches her on moments she does not yet know.',
                fields: [
                    { name: 'frontier_provider', type: 'options', label: 'Provider', options: [
                        { value: '', label: 'None' },
                        { value: 'anthropic', label: 'Anthropic' },
                        { value: 'openai', label: 'OpenAI compatible' },
                    ]},
                    { name: 'frontier_model', type: 'text', label: 'Model' },
                    { name: 'frontier_url', type: 'text', label: 'URL' },
                    { name: 'frontier_api_key', type: 'text', label: 'API key' },
                ],
            },
            {
                title: 'Channels',
                subtitle: 'Optional — connect her to messaging channels.',
                fields: [
                    { name: 'telegram_token', type: 'text', label: 'Telegram bot token' },
                    { name: 'discord_token', type: 'text', label: 'Discord bot token' },
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
