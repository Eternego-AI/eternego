import Element from './element.js';

class InfoCard extends Element {
    static _css = `
        info-card { display: flex; flex-direction: column; gap: var(--space-xs); }
        info-card .ic-row { display: flex; justify-content: space-between; padding: var(--space-xs) 0; font-size: var(--text-sm); }
        info-card .ic-label { color: var(--text-muted); }
        info-card .ic-value { color: var(--text-body); }
    `;
    render() {
        this.constructor._injectStyles();
        this.innerHTML = '';
        for (const { label, value } of this._props.entries || []) {
            const row = document.createElement('div');
            row.className = 'ic-row';
            row.innerHTML = `<span class="ic-label">${this._esc(label)}</span><span class="ic-value">${this._esc(value)}</span>`;
            this.appendChild(row);
        }
    }
}

customElements.define('info-card', InfoCard);
export default InfoCard;
