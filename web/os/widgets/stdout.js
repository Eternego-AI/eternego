import Widget from './widget.js';

class StdoutWidget extends Widget {
    static widgetId = 'stdout';
    static columns = 1;
    static rows = 1;

    // init({ signals: Feed })
    build() {
        const { signals } = this._props;

        const card = document.createElement('card-layout');
        card.init({ title: 'Signals' });

        const tail = document.createElement('tail-layout');
        tail.init({});
        tail.className = 'signal-terminal';
        card.body.appendChild(tail);
        this.appendChild(card);

        this._tail = tail;
        this._maxLines = 200;

        // Backfill existing signals
        for (const msg of signals.items) this._append(msg);

        // Live updates
        signals.addEventListener('update', (e) => {
            for (const msg of e.detail) this._append(msg);
        });
    }

    _append(msg) {
        const el = document.createElement('log-line');
        el.init({ time: msg.time, text: msg.title || '' });
        this._tail.append(el);
        while (this._tail.childElementCount > this._maxLines) {
            this._tail.removeChild(this._tail.firstChild);
        }
    }

    setPersona(personaId) {
        this._personaId = personaId;
    }
}

customElements.define('stdout-widget', StdoutWidget);
export default StdoutWidget;
