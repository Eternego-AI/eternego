/* <chat-view> — header + messages list + composer.
   Emits 'send' (text+file), 'stop', 'poweroff'. */

class ChatView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._messages = [];
        this._personaName = 'her';
        this._pendingEl = null;
        this.innerHTML = `
            <div class="w-header">
                <div class="w-spacer"></div>
                <power-button></power-button>
            </div>
            <div class="w-thread">
                <div class="w-thread-inner">
                    <div class="w-messages is-empty">Quiet here. Say something.</div>
                </div>
            </div>
            <div class="w-composer">
                <div class="w-composer-inner">
                    <chat-input></chat-input>
                </div>
            </div>
        `;
        this._messagesEl = this.querySelector('.w-messages');
        this.querySelector('chat-input').addEventListener('send', (e) => {
            this.dispatchEvent(new CustomEvent('send', { detail: e.detail }));
        });
        this.querySelector('power-button').onclick = () => {
            this.dispatchEvent(new CustomEvent('poweroff'));
        };
    }

    setProps({ personaName, messages, pending }) {
        if (personaName) {
            this._personaName = personaName;
            const input = this.querySelector('chat-input .el-input');
            if (input) input.placeholder = `Say something to ${personaName}…`;
        }
        if (messages !== undefined) {
            /* Copy so a parent's array stays separate from ours. */
            this._messages = messages.slice();
            this.renderMessages();
        }
        if (pending !== undefined) this.setPending(pending);
    }

    appendMessage(msg) {
        this._messages.push(msg);
        this.renderMessages();
    }

    setPending(on, detail, mode) {
        if (on) {
            if (!this._pendingEl) {
                this._pendingEl = document.createElement('pending-row');
                this._pendingEl.addEventListener('stop', () => {
                    this.dispatchEvent(new CustomEvent('stop'));
                });
                this._messagesEl.appendChild(this._pendingEl);
                this._messagesEl.classList.remove('is-empty');
                this._scroll();
            }
            this._pendingEl.setProps({ detail, mode });
        } else if (this._pendingEl) {
            this._pendingEl.remove();
            this._pendingEl = null;
        }
    }

    renderMessages() {
        const list = this._messagesEl;
        const pending = this._pendingEl;
        list.innerHTML = '';
        if (this._messages.length === 0 && !pending) {
            list.classList.add('is-empty');
            list.textContent = 'Quiet here. Say something.';
            return;
        }
        list.classList.remove('is-empty');
        for (const msg of this._messages) {
            const m = document.createElement('role-message');
            m.setProps({ role: msg.role, text: msg.text, time: msg.time, image: msg.image, trace: msg.trace });
            list.appendChild(m);
        }
        if (pending) list.appendChild(pending);
        this._scroll();
    }

    _scroll() {
        /* The scrolling container is .w-thread, not .w-messages — that
           inner list is just content inside the centered column. */
        requestAnimationFrame(() => {
            const thread = this.querySelector('.w-thread');
            if (thread) thread.scrollTop = thread.scrollHeight;
        });
    }
}
customElements.define('chat-view', ChatView);
