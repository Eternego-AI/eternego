import World from './world.js';
import '../../core/widgets/persona-orb.js';
import '../../core/widgets/persona-chat.js';

class OuterWorld extends World {
    static _styled = false;
    static _css = `
        outer-world {
            display: flex;
            height: 100%;
            min-height: 0;
            position: relative;
        }
        outer-world::before {
            content: '';
            position: absolute;
            inset: 0;
            pointer-events: none;
            transition: background var(--time-slow) var(--easing);
            z-index: 0;
        }
        outer-world[phase=morning]::before { background: var(--phase-morning); }
        outer-world[phase=day]::before     { background: var(--phase-day); }
        outer-world[phase=night]::before   { background: var(--phase-night); }
        outer-world .orb-area {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 0;
            min-height: 0;
            position: relative;
            z-index: 1;
        }
        outer-world .chat-area {
            flex: 1;
            min-width: 0;
            min-height: 0;
            display: flex;
            position: relative;
            z-index: 1;
        }
        outer-world persona-chat { flex: 1; min-width: 0; }
    `;

    build() {
        const { id, api, signals } = this._props;
        this.personaId = id;
        this.api = api;
        this.signals = signals;
        this.persona = null;
        this.messages = [];
        this.pending = null;
        this.chatHandler = null;

        this.innerHTML = `
            <div class="orb-area"></div>
            <div class="chat-area"></div>
        `;
        this.setAttribute('phase', 'day');

        this.renderOrb();
        this.renderChat();
    }

    async activate() {
        this.api.getPersona(this.personaId).then((p) => {
            this.persona = p;
            this.renderOrb();
            this.renderChat();
        });
        this.api.getConversation(this.personaId).then((msgs) => {
            this.messages = msgs.map((m) => this.mapMessage(m)).filter(Boolean);
            this.renderChat();
        });
        this.chatHandler = (msg) => {
            if (!msg.content) return;
            this.messages = [...this.messages, {
                role: 'them',
                text: msg.content,
                time: this.formatTime(new Date().toISOString()),
            }];
            this.renderChat();
        };
        this.api.onChat(this.chatHandler);
    }

    deactivate() {
        if (this.chatHandler) this.api.offChat(this.chatHandler);
        this.chatHandler = null;
    }

    renderOrb() {
        const area = this.querySelector('.orb-area');
        area.innerHTML = '';
        const orb = document.createElement('persona-orb');
        const state = !this.persona ? 'idle'
            : this.persona.status === 'sick' ? 'sick'
            : this.persona.status === 'hibernate' ? 'sleeping'
            : this.persona.running === false ? 'stopped'
            : 'idle';
        const phase = this.persona?.phase || 'day';
        orb.init({ size: 280, state, phase });
        area.appendChild(orb);
        this.setAttribute('phase', phase);
    }

    renderChat() {
        const area = this.querySelector('.chat-area');
        area.innerHTML = '';
        const chat = document.createElement('persona-chat');
        chat.init({
            messages: this.messages,
            placeholder: this.persona ? `Speak to ${this.persona.name}.` : 'Speak.',
            pending: this.pending,
            onSend: ({ text, file }) => this.send(text, file),
            onPickFile: (file) => { this.pending = file; this.renderChat(); },
            onClearFile: () => { this.pending = null; this.renderChat(); },
        });
        area.appendChild(chat);
    }

    async send(text, file) {
        const time = this.formatTime(new Date().toISOString());
        if (file) {
            this.messages = [...this.messages, { role: 'me', text: text || '', image: URL.createObjectURL(file), time }];
            this.pending = null;
            this.renderChat();
            const result = await this.api.seePersona(this.personaId, file, text);
            if (!result.success) {
                this.messages = [...this.messages, { role: 'system', text: `Send failed: ${result.error}` }];
                this.renderChat();
            }
        } else if (text && text.trim()) {
            this.messages = [...this.messages, { role: 'me', text, time }];
            this.renderChat();
            const result = await this.api.hearPersona(this.personaId, text);
            if (!result.success) {
                this.messages = [...this.messages, { role: 'system', text: `Send failed: ${result.error}` }];
                this.renderChat();
            }
        }
    }

    mapMessage(msg) {
        const text = msg.text || msg.content || '';
        if (!text) return null;
        if ((msg.role === 'person' || msg.role === 'user') && text.startsWith('TOOL_RESULT')) return null;
        const role = (msg.role === 'persona' || msg.role === 'assistant') ? 'them' : 'me';
        return {
            role,
            text,
            time: this.formatTime(msg.time),
            image: msg.image || (msg.media ? this.api.mediaUrl(this.personaId, msg.media) : null),
        };
    }

    formatTime(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        if (isNaN(d)) return '';
        return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    }
}

customElements.define('outer-world', OuterWorld);
export default OuterWorld;
