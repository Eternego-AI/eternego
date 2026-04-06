export default class Widget extends HTMLElement {
    static _styled = false;
    static _injectStyles() {
        if (this._styled) return;
        this._styled = true;
        if (!this._css) return;
        const s = document.createElement('style');
        s.textContent = this._css;
        document.head.appendChild(s);
    }
    init(props) { this._props = props; this.build(); return this; }
    build() {}
    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
