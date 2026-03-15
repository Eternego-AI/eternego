import Widget from './widget.js';
import { square, refreshCw, moon, trash2 } from '../icons.js';

class ControlWidget extends Widget {
    static widgetId = 'control';
    static columns = 1;
    static rows = 1;

    // init({ onAction })
    build() {
        const card = document.createElement('card-layout');
        card.init({ title: 'Control' });

        const actions = [
            { id: 'stop',    icon: square(18),    label: 'Stop',    text: 'This will close all channels and stop the persona. You can restart it later.' },
            { id: 'restart', icon: refreshCw(18),  label: 'Restart', text: 'This will restart the persona, closing and reopening all channels.' },
            { id: 'sleep',   icon: moon(18),       label: 'Sleep',   text: 'The persona will consolidate its conversations into knowledge and grow. This may take a moment.' },
            { id: 'delete',  icon: trash2(18),     label: 'Delete',  text: 'This will permanently delete the persona and all its data. This cannot be undone.' },
        ];

        const row = document.createElement('div');
        row.className = 'control-actions';

        for (const action of actions) {
            const btn = document.createElement('destructive-button');
            btn.init({
                icon: action.icon,
                label: action.label,
                text: action.text,
                onConfirm: () => {
                    if (this._props.onAction) this._props.onAction(action.id);
                },
            });
            if (action.id === 'delete') btn.querySelector('.control-btn').classList.add('control-btn-delete');
            row.appendChild(btn);
        }

        card.body.appendChild(row);
        this.appendChild(card);
        this._card = card;
    }

    setFocused(focused) {
        super.setFocused(focused);
        this._card.setFocused(focused);
    }
}

customElements.define('control-widget', ControlWidget);
export default ControlWidget;
