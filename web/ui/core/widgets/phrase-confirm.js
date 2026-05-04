import Widget from './widget.js';
import '../../platform/elements/action-button.js';

class PhraseConfirm extends Widget {
    static _styled = false;
    static _css = `
        phrase-confirm {
            display: flex;
            flex-direction: column;
            gap: var(--space-xl);
        }
        phrase-confirm .title {
            font-size: var(--text-lg);
            color: var(--text-primary);
            font-weight: 500;
        }
        phrase-confirm .warning {
            font-size: var(--text-base);
            color: var(--text-secondary);
            line-height: 1.7;
        }
        phrase-confirm .warning strong {
            color: var(--warm-text);
            font-weight: 500;
        }
        phrase-confirm .phrase {
            padding: var(--space-xl);
            background: var(--surface-recessed);
            border: 1px solid var(--warm-border);
            border-radius: var(--radius-md);
            font-family: var(--font-mono);
            font-size: var(--text-md);
            color: var(--warm-text);
            line-height: 1.8;
            text-align: center;
            letter-spacing: 0.5px;
            word-spacing: 0.3em;
        }
        phrase-confirm .actions {
            display: flex;
            justify-content: space-between;
            gap: var(--space-md);
        }
    `;

    build() {
        const { title, warning, phrase, copied, onCopy, onConfirm } = this._props;

        this.innerHTML = `
            <div class="title"></div>
            <div class="warning"></div>
            <div class="phrase"></div>
            <div class="actions">
                <action-button class="copy"></action-button>
                <action-button class="confirm"></action-button>
            </div>
        `;

        this.querySelector('.title').textContent = title || '';
        this.querySelector('.warning').innerHTML = warning || '';
        this.querySelector('.phrase').textContent = phrase || '';

        this.querySelector('.copy').init({
            label: copied ? 'Copied' : 'Copy',
            variant: 'secondary',
            onClick: () => onCopy && onCopy(),
        });
        this.querySelector('.confirm').init({
            label: 'I saved them',
            variant: 'primary',
            onClick: () => onConfirm && onConfirm(),
        });
    }
}

customElements.define('phrase-confirm', PhraseConfirm);
export default PhraseConfirm;
