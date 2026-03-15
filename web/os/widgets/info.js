import Widget from './widget.js';

class InfoWidget extends Widget {
    static columns = 1;
    static rows = 1;

    // init({ title, text })
    build() {
        const { title, text } = this._props;

        const card = document.createElement('card-layout');
        card.init({ title });
        card.body.textContent = text || '';
        this.appendChild(card);
        this._card = card;
    }

    setFocused(focused) {
        super.setFocused(focused);
        this._card.setFocused(focused);
    }
}

customElements.define('info-widget', InfoWidget);
export default InfoWidget;
