import Widget from './widget.js';
import { check } from '../icons.js';

class PersonaInfoWidget extends Widget {
    static widgetId = 'persona-info';
    static columns = 1;
    static rows = 1;

    // init({})
    build() {
        const card = document.createElement('card-layout');
        card.init({ title: 'Persona' });
        this.appendChild(card);
        this._card = card;
    }

    update(data) {
        const body = this._card.body;
        body.innerHTML = '';

        const fields = document.createElement('info-card');
        fields.init({
            pairs: [
                { key: 'ID', value: data.id },
                { key: 'Name', value: data.name },
                { key: 'Base Model', value: data.base_model },
                { key: 'Model', value: data.model },
            ],
        });
        body.appendChild(fields);

        for (const ch of (data.channels || [])) {
            const badge = document.createElement('badged-text');
            badge.init({
                text: `${ch.type}  ${ch.name || '-'}`,
                badge: ch.verified ? check(12) : null,
            });
            body.appendChild(badge);
        }
    }

    setFocused(focused) {
        super.setFocused(focused);
        this._card.setFocused(focused);
    }
}

customElements.define('persona-info-widget', PersonaInfoWidget);
export default PersonaInfoWidget;
