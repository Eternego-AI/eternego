import Widget from './widget.js';

class SignalLogWidget extends Widget {
    static widgetId = 'signals';
    static columns = 1;
    static rows = 3;

    // init({ signals: Feed, getSignalsFor })
    build() {

        const card = document.createElement('card-layout');
        card.init({ title: 'Signals' });

        const tail = document.createElement('tail-layout');
        tail.init({});
        tail.className = 'signal-terminal';
        card.body.appendChild(tail);
        this.appendChild(card);

        this._card = card;
        this._tail = tail;
        this._personaId = null;
        this._maxLines = 200;

        this._props.signals.addEventListener('update', (e) => {
            for (const msg of e.detail) {
                if (this._personaId && !this._match(msg)) continue;
                this._append(msg);
            }
        });
    }

    setPersona(personaId) {
        this._personaId = personaId;
        this._tail.innerHTML = '';
        const past = this._props.getSignalsFor(personaId);
        for (const msg of past) this._append(msg);
    }

    setFocused(focused) {
        super.setFocused(focused);
        this._card.setFocused(focused);
    }

    _match(msg) {
        const p = msg.details?.persona || msg.details?.persona_id || '';
        const pid = typeof p === 'object' ? (p.id || '') : String(p);
        return pid.includes(this._personaId);
    }

    _append(msg) {
        const el = document.createElement('log-line');
        el.init({ time: msg.time, text: msg.title || '' });
        this._tail.append(el);
        while (this._tail.childElementCount > this._maxLines) {
            this._tail.removeChild(this._tail.firstChild);
        }
    }
}

customElements.define('signal-log-widget', SignalLogWidget);
export default SignalLogWidget;
