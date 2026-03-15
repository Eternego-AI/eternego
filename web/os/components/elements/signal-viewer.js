import OS from '../../os.js';

/**
 * <signal-viewer persona="id">
 *
 * Live signal stream via WebSocket. Activates when parent app opens.
 */
class SignalViewer extends HTMLElement {
    static get observedAttributes() { return ['persona']; }

    connectedCallback() {
        this.innerHTML = `<div class="signal-terminal"></div>`;

        this._terminal = this.querySelector('.signal-terminal');
        this._personaId = this.getAttribute('persona') || null;
        this._maxLines = 200;
        this._active = false;

        this._navHandler = ({ app }) => {
            const page = this.closest('app-page');
            const myApp = page ? page.getAttribute('name') : null;
            if (myApp === app) {
                if (!this._active) this._activate();
            } else {
                if (this._active) this._deactivate();
            }
        };
        OS.onNavigate(this._navHandler);
    }

    disconnectedCallback() {
        this._deactivate();
        OS._onNavigate = OS._onNavigate.filter(f => f !== this._navHandler);
    }

    attributeChangedCallback(name, oldVal, newVal) {
        if (name === 'persona' && oldVal !== newVal) {
            this._personaId = newVal;
            if (this._active) {
                this._terminal.innerHTML = '';
                this._backfill();
            }
        }
    }

    _activate() {
        this._active = true;
        this._backfill();

        this._handler = (msg) => {
            if (this._personaId && !this._match(msg)) return;
            this._append(msg);
        };
        OS.onSignal(this._handler);
    }

    _deactivate() {
        this._active = false;
        if (this._handler) {
            OS.offSignal(this._handler);
            this._handler = null;
        }
        if (this._terminal) this._terminal.innerHTML = '';
    }

    _backfill() {
        for (const msg of OS.signals(this._personaId)) {
            this._append(msg);
        }
    }

    _match(msg) {
        const p = msg.details?.persona || msg.details?.persona_id || '';
        const pid = typeof p === 'object' ? (p.id || '') : String(p);
        return pid.includes(this._personaId);
    }

    _append(msg) {
        const type = msg.type || 'signal';
        const span = document.createElement('span');
        span.textContent = `[ ${type} ] ${msg.title || ''}\n`;
        this._terminal.appendChild(span);
        while (this._terminal.childNodes.length > this._maxLines) {
            this._terminal.removeChild(this._terminal.firstChild);
        }
        this._terminal.scrollTop = this._terminal.scrollHeight;
    }
}

customElements.define('signal-viewer', SignalViewer);
