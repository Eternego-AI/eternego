import App from './app.js';
import '../../platform/layouts/step-form.js';
import '../widgets/phrase-confirm.js';

class Create extends App {
    async start() {
        this.step = 0;
        this.values = {};
        this.error = null;
        this.submitting = false;
        this.expanded = { vision: false, teacher: false };
        this.created = null;
        this.copied = false;

        try { this.providers = await this._props.api.getProviderConfig(); }
        catch { this.providers = {}; }

        this._el = document.createElement('step-form');
        this.render();
    }

    render() {
        if (this.created) return this.renderPhrase();
        const p = this.providers || {};
        const steps = [
            {
                title: 'Name',
                subtitle: 'What does she answer to?',
                fields: [
                    { name: 'name', type: 'text', label: 'Name', placeholder: 'Lumen, Calla, Nox...', required: true, help: "Something short. You'll write it many times." },
                ],
            },
            {
                title: 'Mind',
                subtitle: 'Where her thoughts come from. She uses this model for everything — recognizing, deciding, reflecting, remembering.',
                fields: [
                    { name: 'thinking_provider', type: 'options', label: 'Provider', help: 'Local runs on your machine through Ollama. Anthropic and OpenAI-compatible run in the cloud and need a key.', options: [
                        { value: 'local', label: 'Local (Ollama)' },
                        { value: 'anthropic', label: 'Anthropic' },
                        { value: 'openai', label: 'OpenAI compatible' },
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

    renderPhrase() {
        if (this._el.tagName.toLowerCase() !== 'phrase-confirm') {
            const phraseEl = document.createElement('phrase-confirm');
            this._el.replaceWith(phraseEl);
            this._el = phraseEl;
        }
        this._el.init({
            title: `${this.created.persona?.name || 'She'}'s here. Save her recovery phrase.`,
            warning: "These words are the only key to her diary. <strong>Without them, you can't bring her back if you ever lose this machine.</strong> Save them somewhere safe.",
            phrase: this.created.recovery_phrase,
            copied: this.copied,
            onCopy: async () => {
                try { await navigator.clipboard.writeText(this.created.recovery_phrase); }
                catch {}
                this.copied = true;
                this.render();
            },
            onConfirm: () => this._props.onDone && this._props.onDone(this.created.persona_id),
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
            this.created = result;
            this.render();
        } else {
            this.error = result.error || 'Failed to create persona.';
            this.submitting = false;
            this.render();
        }
    }
}

export default Create;
