/* <power-button> — the only hard control: turn her off. Click handler set by parent. */

class PowerButton extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this.innerHTML = `<span class="el-ring"></span><span>OFF</span>`;
    }
}
customElements.define('power-button', PowerButton);
