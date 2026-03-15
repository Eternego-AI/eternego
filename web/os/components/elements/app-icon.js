class AppIcon extends HTMLElement {
    static get observedAttributes() { return ['selected']; }

    connectedCallback() {
        const icon = this.getAttribute('icon') || '';
        const label = this.getAttribute('label') || '';
        const type = this.getAttribute('type');

        if (type) this.classList.add(type);
        if (this.hasAttribute('selected')) this.classList.add('selected');

        this.innerHTML = `
            <div class="orb">${icon}</div>
            <div class="name">${label}</div>
        `;
    }

    attributeChangedCallback(name, oldVal, newVal) {
        if (name === 'selected') {
            if (newVal !== null) this.classList.add('selected');
            else this.classList.remove('selected');
        }
    }
}

customElements.define('app-icon', AppIcon);
