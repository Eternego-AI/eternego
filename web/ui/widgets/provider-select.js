/* <provider-select name="thinking_provider" required [include-none]>
   Named provider dropdown — user sees vendor names (OpenAI, Groq, DeepSeek…).
   Backend value is the actual provider key (anthropic|openai|xai|local).
   Emits 'preset' on change with detail = { provider, url } so the form
   can fill the matching URL field. */

const PRESETS = [
    { key: 'local',        label: 'Local (Ollama)',                  provider: 'local',     url: 'http://localhost:11434' },
    { key: 'anthropic',    label: 'Anthropic',                       provider: 'anthropic', url: 'https://api.anthropic.com' },
    { key: 'openai',       label: 'OpenAI',                          provider: 'openai',    url: 'https://api.openai.com' },
    { key: 'xai',          label: 'xAI (Grok)',                      provider: 'xai',       url: 'https://api.x.ai' },
    { key: 'groq',         label: 'Groq',                            provider: 'openai',    url: 'https://api.groq.com/openai/v1' },
    { key: 'deepseek',     label: 'DeepSeek',                        provider: 'openai',    url: 'https://api.deepseek.com' },
    { key: 'mistral',      label: 'Mistral',                         provider: 'openai',    url: 'https://api.mistral.ai/v1' },
    { key: 'together',     label: 'Together AI',                     provider: 'openai',    url: 'https://api.together.xyz/v1' },
    { key: 'openai_other', label: 'Other (OpenAI compatible)',       provider: 'openai',    url: '' },
];

function keyForValues(provider, url) {
    if (!provider) return '';
    const matchExact = PRESETS.find(p => p.provider === provider && p.url === (url || ''));
    if (matchExact) return matchExact.key;
    if (provider === 'openai') return 'openai_other';
    const fallback = PRESETS.find(p => p.provider === provider);
    return fallback?.key || '';
}

class ProviderSelect extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        const label = this.getAttribute('label') || 'Provider';
        const required = this.hasAttribute('required');
        const includeNone = this.hasAttribute('include-none');

        /* Inner field-select keyed by name "__provider_inner_<n>" so the form's
           field-input/field-select scan doesn't claim it as a public field. */
        const innerName = '__provider_inner_' + (this.getAttribute('name') || 'p');
        const optionsHtml = (includeNone ? '<option value="">— none —</option>' : '') +
            PRESETS.map(p => `<option value="${p.key}">${p.label}</option>`).join('');
        this.innerHTML = `
            <field-select name="${innerName}" label="${label}" ${required ? 'required' : ''}>
                ${optionsHtml}
            </field-select>
        `;
        this._inner = this.querySelector('field-select');
        this._inner.addEventListener('input', (e) => {
            const key = e.detail.value;
            const preset = PRESETS.find(p => p.key === key);
            this.dispatchEvent(new CustomEvent('preset', { detail: preset || null }));
        });
    }

    /* Public value: actual backend provider (anthropic|openai|xai|local|''). */
    get value() {
        const key = this._inner?.value || '';
        if (!key) return '';
        return PRESETS.find(p => p.key === key)?.provider || '';
    }

    /* Preselect by saved provider+url. */
    setValue(provider, url) {
        const key = keyForValues(provider, url);
        if (this._inner && key) this._inner.value = key;
    }

    /* The default URL for the currently-selected preset (empty if none). */
    get defaultUrl() {
        const key = this._inner?.value || '';
        return PRESETS.find(p => p.key === key)?.url || '';
    }

    focus() { this._inner?.focus(); }
    setError(msg) { this._inner?.setError(msg); }
}
customElements.define('provider-select', ProviderSelect);
