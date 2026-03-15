import Element from './element.js';

class AppIcon extends Element {
    static get observedAttributes() { return ['selected']; }

    // init({ icon, label, type, selected, onClick })
    render() {
        const { icon, label, type, selected, onClick } = this._props;
        if (type) this.classList.add(type);
        if (selected) this.classList.add('selected');
        this.innerHTML = `
            <div class="orb">${icon}</div>
            <div class="name">${this._esc(label)}</div>
        `;
        if (onClick) this.addEventListener('click', onClick);
    }

    attributeChangedCallback(name, oldVal, newVal) {
        if (name === 'selected') {
            if (newVal !== null) this.classList.add('selected');
            else this.classList.remove('selected');
        }
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

customElements.define('app-icon', AppIcon);
export default AppIcon;
