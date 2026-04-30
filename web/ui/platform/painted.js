export default class Painted extends HTMLElement {
    static _styled = false;

    static _injectStyles() {
        if (this._styled) return;
        this._styled = true;
        if (!this._css) return;
        const s = document.createElement('style');
        s.textContent = this._css;
        document.head.appendChild(s);
    }
}
