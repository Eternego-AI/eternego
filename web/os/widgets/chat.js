import Widget from './widget.js';

class ChatWidget extends Widget {
    static columns = 2;
    static rows = 2;

    // init({ onSend, onChat, offChat })
    build() {
        this.setAttribute('widget', 'chat');
        this.setAttribute('columns', ChatWidget.columns);
        this.setAttribute('rows', ChatWidget.rows);

        const card = document.createElement('card-layout');
        card.init({ title: 'Chat' });

        const chat = document.createElement('div');
        chat.className = 'chat';

        const tail = document.createElement('tail-layout');
        tail.init({});
        tail.className = 'chat-messages';

        const thinking = document.createElement('div');
        thinking.className = 'chat-thinking';
        thinking.innerHTML = '<span></span><span></span><span></span>';

        const inputRow = document.createElement('div');
        inputRow.className = 'chat-input-row';

        const input = document.createElement('input');
        input.className = 'chat-input';
        input.type = 'text';
        input.placeholder = 'Say something...';
        input.disabled = true;

        const sendBtn = document.createElement('button');
        sendBtn.className = 'chat-send';
        sendBtn.textContent = '↵';
        sendBtn.disabled = true;

        inputRow.appendChild(input);
        inputRow.appendChild(sendBtn);
        chat.appendChild(tail);
        chat.appendChild(thinking);
        chat.appendChild(inputRow);
        card.body.appendChild(chat);
        this.appendChild(card);

        this._card = card;
        this._tail = tail;
        this._thinking = thinking;
        this._input = input;
        this._sendBtn = sendBtn;
        this._personaId = null;
        this._isThinking = false;

        const send = () => {
            const text = input.value.trim();
            if (!text || this._isThinking || !this._personaId) return;
            input.value = '';
            this._addMessage('user', text);
            this._props.onSend(this._personaId, text);
            input.disabled = true;
            sendBtn.disabled = true;
            this._showThinking();
        };

        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
        sendBtn.addEventListener('click', send);

        this._chatHandler = (msg) => {
            if (msg.persona_id === this._personaId) {
                this._hideThinking();
                this._addMessage('assistant', msg.content);
                this._input.disabled = false;
                this._sendBtn.disabled = false;
                this._input.focus();
            }
        };
    }

    setPersona(personaId) {
        if (personaId === this._personaId) return;
        this._personaId = personaId;
        this._tail.innerHTML = '';
        this._isThinking = false;
        this._hideThinking();
        this._loadHistory();
    }

    activate() {
        this._input.disabled = false;
        this._sendBtn.disabled = false;
        this._props.onChat(this._chatHandler);
        setTimeout(() => this._input.focus(), 50);
    }

    deactivate() {
        this._props.offChat(this._chatHandler);
    }

    setFocused(focused) {
        this._card.setFocused(focused);
        this.classList.toggle('focused', focused);
    }

    async _loadHistory() {
        if (!this._personaId) return;
        try {
            const res = await fetch(`/api/persona/${this._personaId}/mind`);
            if (!res.ok) return;
            const data = await res.json();
            this._tail.innerHTML = '';
            for (const s of data.signals || []) {
                if (s.role === 'user' || s.role === 'assistant') {
                    this._addMessage(s.role, s.content);
                }
            }
        } catch {}
    }

    _addMessage(role, content) {
        const el = document.createElement('role-message');
        el.init({ role, text: content });
        this._tail.append(el);
    }

    _showThinking() {
        this._isThinking = true;
        this._thinking.style.display = 'flex';
    }

    _hideThinking() {
        this._isThinking = false;
        this._thinking.style.display = 'none';
    }
}

customElements.define('chat-widget', ChatWidget);
export default ChatWidget;
