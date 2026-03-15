import Element from './element.js';

class InfoCard extends Element {
    // init({ pairs: [{ key, value }] })
    render() {
        const { pairs } = this._props;
        this.innerHTML = '';
        for (const { key, value } of pairs) {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;justify-content:space-between;padding:4px 0;';
            row.innerHTML = `<span style="color:rgba(255,255,255,0.5)">${this._esc(key)}</span><span>${this._esc(value)}</span>`;
            this.appendChild(row);
        }
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

customElements.define('info-card', InfoCard);
export default InfoCard;
