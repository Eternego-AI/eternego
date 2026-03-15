import Mode from './mode.js';

class TerminalMode extends Mode {
    // init({ ttyApp })
    build() {
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

        // Wire tty app's stdout to boot log
        const ttyApp = this._props.ttyApp;
        const widgets = ttyApp.widgets();
        // We don't insert widgets into terminal mode's DOM —
        // terminal mode has its own boot log display
    }

    activate() {
        this._screen.classList.remove('fade-out');
        this._screen.style.display = '';
    }

    deactivate() {
        this._screen.classList.add('fade-out');
        setTimeout(() => {
            this._screen.style.display = 'none';
        }, 800);
    }

    appendLog(text) {
        const span = document.createElement('span');
        span.textContent = text + '\n';
        this._log.appendChild(span);
        this._log.scrollTop = this._log.scrollHeight;
    }
}

customElements.define('terminal-mode', TerminalMode);
export default TerminalMode;
