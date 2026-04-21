import Widget from './widget.js';

class PairWidget extends Widget {
    static _css = `
        pair-widget { display: flex; flex-direction: column; gap: var(--space-md); }
        pair-widget .pw-title { font-size: var(--text-lg); color: var(--text-primary); font-weight: 500; }
        pair-widget .pw-hint { font-size: var(--text-sm); color: var(--text-secondary); line-height: 1.7; }
        pair-widget .pw-hint strong { color: var(--text-body); font-weight: 500; }
        pair-widget .pw-hint code { background: var(--surface-hover); padding: 1px 5px; border-radius: var(--radius-sm); }
        pair-widget .pw-input {
            padding: 10px 14px; background: var(--surface-recessed); border: 1px solid var(--border-default);
            border-radius: var(--radius-lg); color: var(--text-body); font-family: var(--font); font-size: var(--text-base);
            outline: none; text-transform: uppercase; transition: border-color 0.25s var(--ease);
        }
        pair-widget .pw-input:focus { border-color: var(--accent-border); }
        pair-widget .pw-nav { display: flex; justify-content: flex-end; gap: var(--space-sm); padding-top: var(--space-sm); }
        pair-widget .pw-btn {
            padding: var(--space-sm) var(--space-lg); background: var(--surface-hover); border: 1px solid var(--glass-border);
            border-radius: var(--radius-md); color: var(--text-secondary); font-family: var(--font); font-size: var(--text-base);
            cursor: pointer; transition: border-color 0.2s, color 0.2s, background 0.2s;
        }
        pair-widget .pw-btn:hover { border-color: var(--border-hover); color: #fff; }
        pair-widget .pw-btn.primary { background: var(--accent-bg); border-color: var(--accent-border); color: var(--accent-text); }
        pair-widget .pw-btn.primary:hover { background: var(--accent-hover-bg); border-color: var(--accent-hover-border); color: #fff; }
        pair-widget .pw-btn:disabled { opacity: 0.3; cursor: not-allowed; }
        pair-widget .pw-error {
            padding: 10px 14px; background: var(--destructive-bg); border: 1px solid var(--destructive-border);
            border-radius: var(--radius-md); color: var(--destructive-text); font-size: var(--text-sm);
        }
    `;

    // init({ api, personaId, channelType, onDone, onCancel })
    build() {
        this.constructor._injectStyles();
        const type = this._props.channelType;
        const title = type === 'discord' ? 'Pair with Discord' : 'Pair with Telegram';
        const hint = type === 'discord'
            ? 'Open a direct message with your bot on Discord and send any text. It will reply with a pairing code. Paste it below.'
            : 'Send any message to your bot on Telegram. It will reply with a pairing code. Paste it below.';

        this.innerHTML = `
            <div class="pw-title">${this._esc(title)}</div>
            <p class="pw-hint">${hint}</p>
            <input class="pw-input" type="text" placeholder="Pairing code">
            <div class="pw-nav">
                <button class="pw-btn" data-cancel>Cancel</button>
                <button class="pw-btn primary" data-pair>Pair</button>
            </div>
        `;

        this._input = this.querySelector('.pw-input');
        this._btn = this.querySelector('[data-pair]');

        const doPair = async () => {
            const code = (this._input.value || '').trim();
            if (!code) return;
            this._clearError();
            this._btn.disabled = true;
            try {
                const result = await this._props.api.pairChannel(code, this._props.personaId);
                if (result.success) {
                    if (this._props.onDone) this._props.onDone();
                } else {
                    this._showError(result.message || 'Pairing failed');
                    this._btn.disabled = false;
                }
            } catch (e) {
                this._showError(e.message || 'Pairing failed');
                this._btn.disabled = false;
            }
        };

        this._input.addEventListener('keydown', (e) => { if (e.key === 'Enter') doPair(); });
        this._btn.addEventListener('click', doPair);
        this.querySelector('[data-cancel]').addEventListener('click', () => {
            if (this._props.onCancel) this._props.onCancel();
        });

        setTimeout(() => this._input.focus(), 60);
    }

    _showError(msg) {
        this._clearError();
        const el = document.createElement('p');
        el.className = 'pw-error';
        el.textContent = msg;
        this.insertBefore(el, this._input);
    }

    _clearError() {
        const existing = this.querySelector('.pw-error');
        if (existing) existing.remove();
    }
}

customElements.define('pair-widget', PairWidget);
export default PairWidget;
