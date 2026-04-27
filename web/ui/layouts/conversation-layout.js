import Layout from './layout.js';

class ConversationLayout extends Layout {
    static _css = `
        conversation-layout {
            position: relative;
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0;
            width: 100%;
            max-width: 720px;
            margin: 0 auto;
        }
        conversation-layout .cl-stream {
            flex: 1;
            overflow-y: auto;
            padding: var(--space-xl) var(--space-lg) var(--space-lg);
            display: flex;
            flex-direction: column;
            gap: var(--space-xl);
        }
        conversation-layout .cl-turn {
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
            animation: cl-rise 0.35s var(--ease);
        }
        conversation-layout .cl-turn.role-speaker { align-items: flex-start; }
        conversation-layout .cl-turn.role-user { align-items: flex-end; }
        conversation-layout .cl-bubble {
            max-width: 100%;
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-xl);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
        }
        conversation-layout .cl-turn.role-user .cl-bubble {
            background: var(--accent-bg);
            border-color: var(--accent-border);
            color: var(--accent-text);
        }
        @keyframes cl-rise {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        conversation-layout .cl-input-slot {
            padding: var(--space-lg);
            border-top: 1px solid var(--border-subtle);
            background: linear-gradient(to top, var(--bg) 70%, transparent);
        }
        conversation-layout .cl-input-slot:empty { display: none; }
    `;

    arrange() {
        this.constructor._injectStyles();
        this._stream = document.createElement('div');
        this._stream.className = 'cl-stream';
        this._slot = document.createElement('div');
        this._slot.className = 'cl-input-slot';
        this.appendChild(this._stream);
        this.appendChild(this._slot);
    }

    appendTurn(role, blocks) {
        const turn = document.createElement('div');
        turn.className = `cl-turn role-${role}`;
        const bubble = document.createElement('div');
        bubble.className = 'cl-bubble';
        for (const b of blocks) bubble.appendChild(b);
        turn.appendChild(bubble);
        this._stream.appendChild(turn);
        this._scrollToBottom();
        return turn;
    }

    setInput(el) {
        this._slot.innerHTML = '';
        if (el) this._slot.appendChild(el);
    }

    clearInput() {
        this._slot.innerHTML = '';
    }

    _scrollToBottom() {
        requestAnimationFrame(() => {
            this._stream.scrollTop = this._stream.scrollHeight;
        });
    }
}

customElements.define('conversation-layout', ConversationLayout);
export default ConversationLayout;
