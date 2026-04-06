import Layout from './layout.js';

class TailLayout extends Layout {
    static _css = `
        tail-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow-y: auto; }
    `;
    arrange() {
        this.constructor._injectStyles();
        this._pinned = true;
        this.addEventListener('scroll', () => { this._pinned = (this.scrollHeight - this.scrollTop - this.clientHeight) < 24; });
        this._mo = new MutationObserver(() => { if (this._pinned) this.scrollTop = this.scrollHeight; });
        this._mo.observe(this, { childList: true, subtree: true, characterData: true });
        this._ro = new ResizeObserver(() => { if (this._pinned) this.scrollTop = this.scrollHeight; });
        this._ro.observe(this);
    }
    disconnectedCallback() { this._mo?.disconnect(); this._ro?.disconnect(); }
    append(el) { this.appendChild(el); }
}

customElements.define('tail-layout', TailLayout);
export default TailLayout;
