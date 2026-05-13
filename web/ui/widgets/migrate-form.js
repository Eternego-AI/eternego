/* <migrate-form> — restore a persona from a .diary backup.
   Fields: diary (file), phrase, plus the same model/channel sections as create.
   Submits multipart so the file rides along.
   Emits 'submit-migrate' with detail = FormData. Emits 'back'. */

class MigrateForm extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._submitting = false;
        this._file = null;

        this.innerHTML = `
            <div class="w-migrate">
                <div class="w-migrate-head">
                    <button class="w-migrate-back" type="button">← back</button>
                    <h2>Migrate from a diary</h2>
                </div>

                <section class="w-create-section">
                    <h3>Diary</h3>
                    <p class="w-create-help">She is somewhere in this file. Drop her .diary here. The phrase you set when you exported her unlocks it again — without it, the diary stays sealed.</p>
                    <label class="w-migrate-drop" tabindex="0">
                        <input type="file" class="w-migrate-file" accept=".diary,application/octet-stream" hidden>
                        <span class="w-migrate-drop-label">Choose a .diary file</span>
                        <span class="w-migrate-drop-name" hidden></span>
                    </label>
                    <field-input name="phrase" label="Recovery phrase" type="password" placeholder="the phrase you set when exporting her" required></field-input>
                </section>

                <section class="w-create-section">
                    <h3>Mind</h3>
                    <p class="w-create-help">Where her thoughts come from now. The diary holds her memory; you choose the model that thinks with it.</p>
                    <provider-select name="thinking_provider" label="Provider" required></provider-select>
                    <field-input name="thinking_model" label="Model" placeholder="claude-haiku-4-5-20251001" required></field-input>
                    <field-input name="thinking_api_key" label="API key" type="password" placeholder="sk-…" help="Stays on your machine. Required for cloud providers."></field-input>
                    <field-input name="thinking_url" label="URL" placeholder="(leave blank for default)" help="Optional — override the provider URL."></field-input>
                </section>

                <details class="w-create-details">
                    <summary>Give her vision <span class="w-dim">— optional</span></summary>
                    <section class="w-create-section">
                        <p class="w-create-help">If her thinking model already sees (Claude, GPT-4o), skip this. Otherwise give her a separate model that can read images.</p>
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
                        <p class="w-create-help">Where she can be reached beyond this app. Channels from her old life don't come over — set them again here.</p>
                        <field-input name="telegram_token" label="Telegram bot token" type="password" help="Create a bot with @BotFather and paste the token."></field-input>
                        <field-input name="discord_token" label="Discord bot token" type="password" help="Create an app at discord.com/developers."></field-input>
                    </section>
                </details>

                <div class="w-create-actions">
                    <div class="w-create-error" hidden></div>
                    <button class="w-create-submit" type="button">MIGRATE</button>
                </div>
            </div>
        `;

        this.querySelector('.w-migrate-back').onclick = () =>
            this.dispatchEvent(new CustomEvent('back'));
        this.querySelector('.w-create-submit').onclick = () => this._submit();

        const fileInput = this.querySelector('.w-migrate-file');
        const drop = this.querySelector('.w-migrate-drop');
        const dropName = this.querySelector('.w-migrate-drop-name');
        const dropLabel = this.querySelector('.w-migrate-drop-label');

        fileInput.onchange = () => {
            const f = fileInput.files?.[0] || null;
            this._file = f;
            if (f) {
                dropName.textContent = f.name;
                dropName.hidden = false;
                dropLabel.hidden = true;
            } else {
                dropName.hidden = true;
                dropLabel.hidden = false;
            }
        };
        drop.ondragover = (e) => { e.preventDefault(); drop.classList.add('is-over'); };
        drop.ondragleave = () => drop.classList.remove('is-over');
        drop.ondrop = (e) => {
            e.preventDefault();
            drop.classList.remove('is-over');
            const f = e.dataTransfer?.files?.[0];
            if (f) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        };

        for (const ps of this.querySelectorAll('provider-select')) {
            const psName = ps.getAttribute('name');
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
        for (const el of this.querySelectorAll('field-input, field-select')) {
            if (el.closest('provider-select')) continue;
            const name = el.getAttribute('name');
            const v = el.value?.trim() || '';
            if (name && v) out[name] = v;
        }
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
        if (!this._file) {
            this.setError('Choose a diary file first.');
            return;
        }
        const fields = this._collectFields();
        const err = this._validate(fields);
        if (err) { err.focus?.(); return; }

        const form = new FormData();
        form.append('diary', this._file, this._file.name);
        for (const [k, v] of Object.entries(fields)) form.append(k, v);

        this._submitting = true;
        const btn = this.querySelector('.w-create-submit');
        btn.textContent = 'MIGRATING…';
        btn.disabled = true;
        this.dispatchEvent(new CustomEvent('submit-migrate', { detail: form }));
    }

    setError(message) {
        const e = this.querySelector('.w-create-error');
        e.textContent = message;
        e.hidden = !message;
        this._submitting = false;
        const b = this.querySelector('.w-create-submit');
        b.textContent = 'MIGRATE';
        b.disabled = false;
    }
}
customElements.define('migrate-form', MigrateForm);
