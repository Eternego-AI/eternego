import App from './app.js';
import '../../platform/layouts/step-form.js';

class Setup extends App {
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
                title: 'Name',
                subtitle: 'What does she answer to?',
                fields: [
                    { name: 'name', type: 'text', label: 'Name', placeholder: 'Lumen, Calla, Nox...', required: true },
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
        this.submitting = true;
        this.error = null;
        this.render();

        const v = this.values;
        const result = await this._props.api.createPersona({
            name: v.name,
            thinking_provider: v.thinking_provider,
            thinking_url: v.thinking_url || null,
            thinking_model: v.thinking_model,
            thinking_api_key: v.thinking_api_key || null,
            vision_provider: v.vision_provider || null,
            vision_url: v.vision_url || null,
            vision_model: v.vision_model || null,
            vision_api_key: v.vision_api_key || null,
            frontier_provider: v.frontier_provider || null,
            frontier_url: v.frontier_url || null,
            frontier_model: v.frontier_model || null,
            frontier_api_key: v.frontier_api_key || null,
            telegram_token: v.telegram_token || null,
            discord_token: v.discord_token || null,
        });

        if (result.success) {
            this._props.onDone && this._props.onDone(result.persona_id);
        } else {
            this.error = result.error || 'Failed to create persona.';
            this.submitting = false;
            this.render();
        }
    }
}

export default Setup;
