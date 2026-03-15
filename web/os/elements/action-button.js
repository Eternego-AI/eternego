import Element from './element.js';

class ActionButton extends Element {
    // init({ label, primary, disabled, onClick })
    render() {
        const { label, primary, disabled, onClick } = this._props;
        const btn = document.createElement('button');
        btn.className = 'wizard-btn' + (primary ? ' primary' : '');
        btn.textContent = label;
        if (disabled) btn.disabled = true;
        if (onClick) btn.addEventListener('click', onClick);
        this.innerHTML = '';
        this.appendChild(btn);
        this._btn = btn;
    }

    set disabled(v) { if (this._btn) this._btn.disabled = v; }
}

customElements.define('action-button', ActionButton);
export default ActionButton;
