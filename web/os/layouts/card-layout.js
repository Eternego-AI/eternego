import Layout from './layout.js';

class CardLayout extends Layout {
    // init({ title })
    arrange() {
        const { title } = this._props;
        const card = document.createElement('div');
        card.className = 'card';

        if (title) {
            const h3 = document.createElement('h3');
            h3.textContent = title;
            card.appendChild(h3);
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
