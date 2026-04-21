import Layout from './layout.js';

class ModalLayout extends Layout {
    static _css = `
        modal-layout {
            position: fixed;
            inset: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
            animation: ml-fade 0.2s var(--ease);
        }
        modal-layout .ml-card {
            position: relative;
            max-width: 480px;
            width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            padding: var(--space-xl);
            background: var(--bg);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-xl);
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            gap: var(--space-lg);
            animation: ml-rise 0.25s var(--ease);
        }
        modal-layout .ml-close {
            position: absolute;
            top: var(--space-md);
            right: var(--space-md);
            width: 28px;
            height: 28px;
            padding: 0;
            background: none;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-full);
            color: var(--text-secondary);
            font-family: var(--font);
            cursor: pointer;
            transition: border-color 0.2s, color 0.2s;
        }
        modal-layout .ml-close:hover { border-color: var(--border-hover); color: var(--text-primary); }
        @keyframes ml-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes ml-rise {
            from { opacity: 0; transform: translateY(8px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
    `;

    arrange() {
        this.constructor._injectStyles();
        this._card = document.createElement('div');
        this._card.className = 'ml-card';
        this.appendChild(this._card);

        const close = document.createElement('button');
        close.className = 'ml-close';
        close.type = 'button';
        close.setAttribute('aria-label', 'Close');
        close.textContent = '×';
        close.addEventListener('click', () => this._close());
        this._card.appendChild(close);

        this.addEventListener('click', (e) => {
            if (e.target === this) this._close();
        });

        this._onKey = (e) => {
            if (e.key === 'Escape') this._close();
        };
        document.addEventListener('keydown', this._onKey);
    }

    get content() { return this._card; }

    setContent(el) {
        while (this._card.children.length > 1) this._card.removeChild(this._card.lastChild);
        this._card.appendChild(el);
    }

    _close() {
        document.removeEventListener('keydown', this._onKey);
        this.dispatchEvent(new CustomEvent('close', { bubbles: true }));
        this.remove();
    }
}

customElements.define('modal-layout', ModalLayout);
export default ModalLayout;
