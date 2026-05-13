/* <settings-view> — theme + status picker + editable model sections + actions.
   Emits:
     poweroff, restart, delete                                 — confirmed actions
     update-status with detail.status                          — flip lifecycle
     update-model with detail.{slot, config}                   — save thinking/vision/frontier
     clear-model  with detail.{slot}                           — remove vision/frontier */

import { escapeHtml } from '../platform/escape.js';

const STATUS_CHOICES = [
    { value: 'active',    label: 'ACTIVE',    hint: 'awake and acting' },
    { value: 'hibernate', label: 'HIBERNATE', hint: 'resting until you wake her' },
    { value: 'sick',      label: 'SICK',      hint: 'paused — provider trouble' },
];

const SLOT_LABELS = {
    thinking: { title: 'Mind',     help: 'Where her thoughts come from. She uses this model for every beat.' },
    vision:   { title: 'Vision',   help: 'For seeing images. Skip if her thinking model already sees.' },
    frontier: { title: 'Teacher',  help: 'A stronger model she reaches for when learning. Used rarely.' },
};

class SettingsView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._persona = null;
        this.innerHTML = '<div class="w-settings"></div>';
        this._root = this.querySelector('.w-settings');
    }

    setProps({ persona }) {
        this._persona = persona;
        this.render();
    }

    render() {
        const p = this._persona;
        if (!p) { this._root.innerHTML = '<p class="w-dim">No persona.</p>'; return; }
        this._root.innerHTML = `
            <h2>Settings</h2>

            <section class="w-set-section">
                <h3>Appearance</h3>
                <div class="w-set-row">
                    <label>Theme</label>
                    <theme-picker></theme-picker>
                </div>
            </section>

            <section class="w-set-section">
                <h3>Status</h3>
                <div class="w-set-status">
                    ${STATUS_CHOICES.map(s => `
                        <button class="w-set-status-btn ${s.value === p.status ? 'is-active' : ''}" data-status="${s.value}" type="button">
                            <span class="w-set-status-label">${s.label}</span>
                            <span class="w-set-status-hint">${s.hint}</span>
                        </button>
                    `).join('')}
                </div>
            </section>

            ${this._modelSectionHtml('thinking', p.thinking, true)}
            ${this._modelSectionHtml('vision',   p.vision,   false)}
            ${this._modelSectionHtml('frontier', p.frontier, false)}

            <section class="w-set-section">
                <h3>Channels</h3>
                <p class="w-set-help">Channels reach her from outside this app. Once configured, send a message to the bot from your account — it replies with a six-character code you enter below to verify.</p>
                ${(p.channels || []).length === 0
                    ? '<p class="w-dim w-set-channels-empty">No channels yet. Add at creation time, or re-migrate.</p>'
                    : `<ul class="w-set-channels">
                        ${p.channels.map(c => `
                            <li class="w-set-channel">
                                <div class="w-set-channel-head">
                                    <span class="w-set-channel-type">${escapeHtml(c.type)}</span>
                                    <span class="w-set-channel-name">${escapeHtml(c.name || '(unnamed)')}</span>
                                    <span class="w-set-channel-state ${c.verified ? 'is-verified' : 'is-pending'}">${c.verified ? 'verified' : 'awaiting code'}</span>
                                </div>
                                ${c.verified ? '' : `
                                    <div class="w-set-channel-pair">
                                        <input class="w-set-channel-code" type="text" placeholder="six-character code" maxlength="6" autocomplete="off">
                                        <button class="w-set-channel-verify" type="button">VERIFY</button>
                                        <span class="w-set-channel-feedback" hidden></span>
                                    </div>
                                `}
                            </li>
                        `).join('')}
                    </ul>`
                }
            </section>

            <section class="w-set-section">
                <h3>Actions</h3>
                <div class="w-set-buttons">
                    <button class="w-set-btn" data-act="restart">RESTART HER</button>
                    <button class="w-set-btn" data-act="poweroff">TURN HER OFF</button>
                    <button class="w-set-btn is-danger" data-act="delete">DELETE PERMANENTLY</button>
                </div>
            </section>
        `;

        /* Theme */
        const tp = this._root.querySelector('theme-picker');
        tp.setAttribute('value', window.eternego?.getTheme?.() || 'system');
        tp.addEventListener('pick', (e) => window.eternego?.setTheme?.(e.detail.value));

        /* Status buttons */
        for (const b of this._root.querySelectorAll('.w-set-status-btn')) {
            b.onclick = () => {
                const status = b.dataset.status;
                if (status !== this._persona.status) {
                    this.dispatchEvent(new CustomEvent('update-status', { detail: { status } }));
                }
            };
        }

        /* Model section: hydrate provider-select values + wire SAVE / REMOVE + URL auto-fill */
        for (const section of this._root.querySelectorAll('[data-slot]')) {
            const slot = section.dataset.slot;
            const config = this._persona[slot] || null;

            const ps = section.querySelector('provider-select');
            const urlInput = section.querySelector(`field-input[name="${slot}_url"]`);

            if (config) ps.setValue(config.provider, config.url);
            ps.addEventListener('preset', (e) => {
                if (urlInput && e.detail?.url) urlInput.value = e.detail.url;
            });

            const saveBtn = section.querySelector('[data-act="save"]');
            saveBtn.onclick = () => this._saveSlot(slot);

            const removeBtn = section.querySelector('[data-act="remove"]');
            if (removeBtn) removeBtn.onclick = () =>
                this.dispatchEvent(new CustomEvent('clear-model', { detail: { slot } }));
        }

        /* Confirmed actions */
        for (const b of this._root.querySelectorAll('.w-set-buttons .w-set-btn')) {
            b.onclick = () => this.dispatchEvent(new CustomEvent(b.dataset.act));
        }

        /* Channel pairing */
        for (const item of this._root.querySelectorAll('.w-set-channel')) {
            const btn = item.querySelector('.w-set-channel-verify');
            if (!btn) continue;
            const codeInput = item.querySelector('.w-set-channel-code');
            const feedback = item.querySelector('.w-set-channel-feedback');
            btn.onclick = () => {
                const code = codeInput.value.trim();
                if (!code) {
                    feedback.textContent = 'enter the code from the bot';
                    feedback.hidden = false;
                    return;
                }
                feedback.hidden = true;
                btn.disabled = true;
                btn.textContent = 'VERIFYING…';
                this.dispatchEvent(new CustomEvent('pair-channel', { detail: { code } }));
            };
        }
    }

    showPairResult(ok, message) {
        const btn = this._root.querySelector('.w-set-channel-verify');
        if (!btn) return;
        btn.disabled = false;
        btn.textContent = ok ? 'VERIFIED ✓' : 'TRY AGAIN';
        if (!ok) {
            const item = btn.closest('.w-set-channel');
            const feedback = item?.querySelector('.w-set-channel-feedback');
            if (feedback) {
                feedback.textContent = message || 'invalid or expired';
                feedback.hidden = false;
            }
        }
        if (ok) {
            setTimeout(() => btn.textContent = 'VERIFY', 1500);
        }
    }

    _modelSectionHtml(slot, config, required) {
        const meta = SLOT_LABELS[slot];
        const v = config || {};
        return `
            <section class="w-set-section" data-slot="${slot}">
                <div class="w-set-section-head">
                    <h3>${meta.title}</h3>
                    ${!required && config ? `<button class="w-set-remove" type="button" data-act="remove">REMOVE</button>` : ''}
                </div>
                <p class="w-set-help">${meta.help}</p>
                <provider-select name="${slot}_provider" label="Provider" ${required ? 'required' : 'include-none'}></provider-select>
                <field-input name="${slot}_model" label="Model" value="${escapeHtml(v.name || '')}" placeholder="${slot === 'thinking' ? 'claude-haiku-4-5-20251001' : 'model name'}" ${required ? 'required' : ''}></field-input>
                <field-input name="${slot}_api_key" label="API key" type="password" value="${escapeHtml(v.api_key || '')}" help="Stays on your machine."></field-input>
                <field-input name="${slot}_url" label="URL" value="${escapeHtml(v.url || '')}" placeholder="(leave blank for default)"></field-input>
                <div class="w-set-section-actions">
                    <button class="w-set-btn is-primary" type="button" data-act="save">SAVE</button>
                </div>
            </section>
        `;
    }

    _saveSlot(slot) {
        const section = this._root.querySelector(`[data-slot="${slot}"]`);
        if (!section) return;
        const ps = section.querySelector('provider-select');
        const model   = section.querySelector(`field-input[name="${slot}_model"]`)?.value?.trim() || '';
        const api_key = section.querySelector(`field-input[name="${slot}_api_key"]`)?.value?.trim() || '';
        const url     = section.querySelector(`field-input[name="${slot}_url"]`)?.value?.trim() || '';
        const provider = ps.value;
        const required = slot === 'thinking';

        /* Validate */
        ps.setError('');
        section.querySelectorAll('field-input').forEach(el => el.setError(''));
        if (!provider) {
            ps.setError('required');
            return;
        }
        if (!model) {
            section.querySelector(`field-input[name="${slot}_model"]`).setError('required');
            return;
        }

        const config = { provider, model, url, api_key };
        this.dispatchEvent(new CustomEvent('update-model', { detail: { slot, config } }));
    }

    showSaveResult(slot, ok, message) {
        const section = this._root.querySelector(`[data-slot="${slot}"]`);
        if (!section) return;
        const btn = section.querySelector('[data-act="save"]');
        if (!btn) return;
        const original = 'SAVE';
        btn.textContent = ok ? 'SAVED ✓' : 'FAILED';
        btn.classList.toggle('is-error', !ok);
        setTimeout(() => {
            btn.textContent = original;
            btn.classList.remove('is-error');
        }, 1500);
        if (!ok && message) {
            section.querySelector('provider-select')?.setError(message);
        }
    }
}
customElements.define('settings-view', SettingsView);
