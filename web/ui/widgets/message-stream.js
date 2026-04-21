import Widget from './widget.js';

class MessageStream extends Widget {
    static _css = `
        message-stream {
            display: flex;
            flex: 1;
            min-height: 0;
            width: 100%;
        }
    `;

    build() {
        this.constructor._injectStyles();
        this._layout = document.createElement('conversation-layout');
        this._layout.init({});
        this.appendChild(this._layout);

        if (this._props.speaker) {
            this._bind(this._props.speaker);
        }
    }

    _bind(speaker) {
        this._speaker = speaker;
        const api = {
            say: (blocks) => this._say(blocks),
            echo: (blocks) => this._echo(blocks),
            ask: (descriptor) => this._ask(descriptor),
            clear: () => this._layout.clearInput(),
        };
        queueMicrotask(() => speaker.run(api));
    }

    _say(blocks) {
        const els = this._renderBlocks(blocks);
        this._layout.appendTurn('speaker', els);
    }

    _echo(blocks) {
        const els = this._renderBlocks(blocks);
        this._layout.appendTurn('user', els);
    }

    _ask(descriptor) {
        return new Promise((resolve) => {
            const el = this._renderInput(descriptor);
            const onSubmit = (e) => {
                el.removeEventListener('submit', onSubmit);
                this._layout.clearInput();
                resolve(e.detail.value);
            };
            el.addEventListener('submit', onSubmit);
            this._layout.setInput(el);
            if (typeof el.focusFirst === 'function') el.focusFirst();
        });
    }

    _renderBlocks(blocks) {
        const out = [];
        for (const b of blocks || []) {
            const el = this._renderBlock(b);
            if (el) out.push(el);
        }
        return out;
    }

    _renderBlock(b) {
        if (!b || !b.type) return null;
        const tag = `block-${b.type}`;
        if (!customElements.get(tag)) return null;
        const el = document.createElement(tag);
        el.init(b);
        return el;
    }

    _renderInput(descriptor) {
        const tag = `input-${descriptor.type}`;
        if (!customElements.get(tag)) {
            const fallback = document.createElement('div');
            fallback.textContent = `Unknown input: ${descriptor.type}`;
            return fallback;
        }
        const el = document.createElement(tag);
        el.init(descriptor.props || {});
        return el;
    }
}

customElements.define('message-stream', MessageStream);
export default MessageStream;
