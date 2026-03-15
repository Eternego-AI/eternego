import Widget from './widget.js';

class InfoWidget extends Widget {
    static columns = 1;
    static rows = 1;

    // init({ title, text })
    build() {
        const { title, text } = this._props;
        this.setAttribute('widget', title.toLowerCase());
        this.setAttribute('columns', InfoWidget.columns);
        this.setAttribute('rows', InfoWidget.rows);

        const card = document.createElement('card-layout');
        card.init({ title });
        card.body.textContent = text || '';
        this.appendChild(card);
        this._card = card;
    }

    setFocused(focused) {
        this._card.setFocused(focused);
        this.classList.toggle('focused', focused);
    }
}

customElements.define('info-widget', InfoWidget);
export default InfoWidget;
