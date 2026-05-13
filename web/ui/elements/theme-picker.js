/* <theme-picker value="light|dark|system"> — three buttons.
   Emits 'pick' with detail.value when user picks. */

class ThemePicker extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._value = this.getAttribute('value') || 'system';
        this.innerHTML = `
            <button data-v="light">LIGHT</button>
            <button data-v="dark">DARK</button>
            <button data-v="system">SYSTEM</button>
        `;
        for (const b of this.querySelectorAll('button')) {
            b.addEventListener('click', () => {
                this.setValue(b.dataset.v);
                this.dispatchEvent(new CustomEvent('pick', { detail: { value: b.dataset.v } }));
            });
        }
        this._paint();
    }
    setValue(v) {
        this._value = v;
        this.setAttribute('value', v);
        this._paint();
    }
    _paint() {
        for (const b of this.querySelectorAll('button')) {
            if (b.dataset.v === this._value) b.setAttribute('active', '');
            else b.removeAttribute('active');
        }
    }
}
customElements.define('theme-picker', ThemePicker);
