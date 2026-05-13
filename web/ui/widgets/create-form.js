/* <create-form> — single-page persona creation form.
   Required: name, thinking_provider, thinking_model. API key required for cloud providers.
   Optional sections: vision, frontier, channels.
   Emits 'submit' with detail = { fields object matching PersonaCreateRequest }.
   Emits 'back' to return to chooser. */

class CreateForm extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._submitting = false;

        this.innerHTML = `
            <div class="w-create">
                <div class="w-create-head">
                    <button class="w-create-back" type="button">← back</button>
                    <h2>Create a persona</h2>
                </div>

                <section class="w-create-section">
                    <h3>Name</h3>
                    <field-input name="name" label="What does she answer to?" placeholder="Lumen, Calla, Nox…" required></field-input>
                </section>

                <section class="w-create-section">
                    <h3>Mind</h3>
                    <p class="w-create-help">Where her thoughts come from. She uses this model for every beat — recognizing, deciding, reflecting.</p>
                    <provider-select name="thinking_provider" label="Provider" required></provider-select>
                    <field-input name="thinking_model" label="Model" placeholder="claude-haiku-4-5-20251001" required></field-input>
                    <field-input name="thinking_api_key" label="API key" type="password" placeholder="sk-…" help="Stays on your machine. Required for cloud providers."></field-input>
                    <field-input name="thinking_url" label="URL" placeholder="(leave blank for default)" help="Optional — override the provider URL."></field-input>
                </section>

                <details class="w-create-details">
                    <summary>Give her vision <span class="w-dim">— optional</span></summary>
                    <section class="w-create-section">
                        <p class="w-create-help">If her thinking model already sees (Claude, GPT-4o), skip this. For minds without vision, give her a separate model.</p>
                        <provider-select name="vision_provider" label="Provider" include-none></provider-select>
                        <field-input name="vision_model" label="Model" placeholder="llava, claude-haiku-4-5…"></field-input>
                        <field-input name="vision_api_key" label="API key" type="password"></field-input>
                        <field-input name="vision_url" label="URL" placeholder="(leave blank)"></field-input>
                    </section>
                </details>

                <details class="w-create-details">
                    <summary>Give her a teacher <span class="w-dim">— optional</span></summary>
                    <section class="w-create-section">
                        <p class="w-create-help">When she meets a moment she's never seen, the teacher explains the principle. She translates the lesson into her own voice.</p>
                        <provider-select name="frontier_provider" label="Provider" include-none></provider-select>
                        <field-input name="frontier_model" label="Model" placeholder="claude-opus-4-7…"></field-input>
                        <field-input name="frontier_api_key" label="API key" type="password"></field-input>
                        <field-input name="frontier_url" label="URL" placeholder="(leave blank)"></field-input>
                    </section>
                </details>

                <details class="w-create-details">
                    <summary>Channels <span class="w-dim">— optional</span></summary>
                    <section class="w-create-section">
                        <p class="w-create-help">Where she can be reached beyond this app.</p>
                        <field-input name="telegram_token" label="Telegram bot token" type="password" help="Create a bot with @BotFather and paste the token."></field-input>
                        <field-input name="discord_token" label="Discord bot token" type="password" help="Create an app at discord.com/developers."></field-input>
                    </section>
                </details>

                <div class="w-create-actions">
                    <div class="w-create-error" hidden></div>
                    <button class="w-create-submit" type="button">CREATE</button>
                </div>
            </div>
        `;

        this.querySelector('.w-create-back').onclick = () =>
            this.dispatchEvent(new CustomEvent('back'));
        this.querySelector('.w-create-submit').onclick = () => this._submit();

        /* Wire each provider-select to auto-fill the matching URL field on preset pick. */
        for (const ps of this.querySelectorAll('provider-select')) {
            const psName = ps.getAttribute('name'); /* e.g. 'thinking_provider' */
            const base = psName.replace('_provider', '');
            const urlInput = this.querySelector(`field-input[name="${base}_url"]`);
            ps.addEventListener('preset', (e) => {
                if (!urlInput) return;
                const preset = e.detail;
                if (preset && preset.url) urlInput.value = preset.url;
            });
        }
    }

    _collectFields() {
        const out = {};
        /* Regular text inputs and selects — but skip any that live inside a provider-select wrapper. */
        for (const el of this.querySelectorAll('field-input, field-select')) {
            if (el.closest('provider-select')) continue;
            const name = el.getAttribute('name');
            const v = el.value?.trim() || '';
            if (name && v) out[name] = v;
        }
        /* Each provider-select contributes its backend provider value. */
        for (const ps of this.querySelectorAll('provider-select')) {
            const name = ps.getAttribute('name');
            const v = ps.value || '';
            if (name && v) out[name] = v;
        }
        return out;
    }

    _validate(fields) {
        let firstError = null;
        for (const el of this.querySelectorAll('field-input[required], provider-select[required]')) {
            const name = el.getAttribute('name');
            const v = (fields[name] || '').trim();
            el.setError?.('');
            if (!v) {
                el.setError?.('required');
                if (!firstError) firstError = el;
            }
        }
        return firstError;
    }

    async _submit() {
        if (this._submitting) return;
        const fields = this._collectFields();
        const err = this._validate(fields);
        if (err) { err.focus?.(); return; }

        this._submitting = true;
        const btn = this.querySelector('.w-create-submit');
        btn.textContent = 'CREATING…';
        btn.disabled = true;
        this.dispatchEvent(new CustomEvent('submit', { detail: fields }));
    }

    setError(message) {
        const e = this.querySelector('.w-create-error');
        e.textContent = message;
        e.hidden = !message;
        this._submitting = false;
        const b = this.querySelector('.w-create-submit');
        b.textContent = 'CREATE';
        b.disabled = false;
    }
}
customElements.define('create-form', CreateForm);
