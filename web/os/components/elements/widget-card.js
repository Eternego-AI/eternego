class WidgetCard extends HTMLElement {
    connectedCallback() {
        const title = this.getAttribute('title') || '';

        const card = document.createElement('div');
        card.className = 'card';
        if (title) {
            const h3 = document.createElement('h3');
            h3.textContent = title;
            card.appendChild(h3);
        }
        const body = document.createElement('div');
        body.className = 'card-body';
        while (this.firstChild) body.appendChild(this.firstChild);
        card.appendChild(body);
        this.appendChild(card);
    }
}

customElements.define('widget-card', WidgetCard);
