import OS from '../os.js';

class BootLoader extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <div class="boot-screen">
                <div class="boot-center">
                    <img class="boot-logo" src="/assets/eternego-logo.svg" alt="Eternego">
                </div>
                <div class="boot-log"></div>
            </div>
        `;

        this._screen = this.querySelector('.boot-screen');
        this._log = this.querySelector('.boot-log');

        this._signalHandler = (msg) => {
            if (!OS.booted) {
                this._append(`[ ${msg.type || 'signal'} ] ${msg.title}`);
            }
        };
        OS.onSignal(this._signalHandler);

        this._boot();
    }

    _append(text) {
        const span = document.createElement('span');
        span.textContent = text + '\n';
        this._log.appendChild(span);
        this._log.scrollTop = this._log.scrollHeight;
    }

    async _boot() {
        await OS.boot();

        this._screen.classList.add('fade-out');

        setTimeout(() => {
            this._screen.style.display = 'none';
            OS.offSignal(this._signalHandler);
        }, 800);

        this.dispatchEvent(new CustomEvent('booted', { bubbles: true }));
    }
}

customElements.define('boot-loader', BootLoader);
