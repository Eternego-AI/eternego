import Layout from './layout.js';
import { minus } from '../icons.js';

class CardLayout extends Layout {
    // init({ title, onMinimize })
    arrange() {
        const { title } = this._props;
        const card = document.createElement('div');
        card.className = 'card';

        if (title) {
            const header = document.createElement('div');
            header.className = 'card-header';

            const h3 = document.createElement('h3');
            h3.textContent = title;
            header.appendChild(h3);

            const btn = document.createElement('button');
            btn.className = 'card-minimize';
            btn.innerHTML = minus(14);
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this._props.onMinimize) this._props.onMinimize();
            });
            header.appendChild(btn);

            card.appendChild(header);
            this._minimizeBtn = btn;
        }

        const body = document.createElement('div');
        body.className = 'card-body';
        card.appendChild(body);
        this.appendChild(card);

        this._card = card;
        this._body = body;
    }

    get body() { return this._body; }
    get card() { return this._card; }

    setFocused(focused) {
        this._card.classList.toggle('focused-widget', focused);
    }
}

customElements.define('card-layout', CardLayout);
export default CardLayout;
