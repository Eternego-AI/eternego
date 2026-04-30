import Widget from './widget.js';
import '../../platform/layouts/tail-list.js';
import '../../platform/layouts/text-composer.js';
import '../../platform/elements/role-message.js';

class PersonaChat extends Widget {
    static _styled = false;
    static _css = `
        persona-chat {
            display: flex;
            flex-direction: column;
            height: 100%;
            min-height: 0;
        }
        persona-chat tail-list {
            flex: 1;
            min-height: 0;
        }
    `;

    build() {
        const { messages = [], placeholder = 'Speak.', pending, onSend, onPickFile, onClearFile, onTextChange } = this._props;
        this.innerHTML = '';

        const tail = document.createElement('tail-list');
        tail.init({
            items: messages,
            empty: 'Quiet here. Say something.',
            renderItem: (msg) => {
                const m = document.createElement('role-message');
                m.init({
                    role: msg.role,
                    text: msg.text,
                    time: msg.time,
                    image: msg.image,
                });
                return m;
            },
        });
        this.appendChild(tail);

        const composer = document.createElement('text-composer');
        composer.init({
            text: '',
            pending,
            placeholder,
            onTextChange,
            onSend,
            onPickFile,
            onClearFile,
        });
        this.appendChild(composer);
    }
}

customElements.define('persona-chat', PersonaChat);
export default PersonaChat;
