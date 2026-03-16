import Element from './element.js';

class BadgedText extends Element {
    // init({ text, badge })
    // badge is an SVG string or falsy
    render() {
        const { text, badge } = this._props;
        this.className = 'badged-text';

        const span = document.createElement('span');
        span.className = 'badged-text-label';
        span.textContent = text || '';
        this.appendChild(span);

        if (badge) {
            const icon = document.createElement('span');
            icon.className = 'badged-text-icon';
            icon.innerHTML = badge;
            this.appendChild(icon);
        }
    }
}

customElements.define('badged-text', BadgedText);
export default BadgedText;
