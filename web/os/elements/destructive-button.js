import Element from './element.js';

class DestructiveButton extends Element {
    // init({ icon, label, text, onConfirm })
    render() {
        const { icon, label } = this._props;

        const btn = document.createElement('button');
        btn.className = 'control-btn';
        btn.innerHTML = `<span class="control-icon">${icon}</span><span class="control-label">${this._esc(label)}</span>`;
        btn.addEventListener('click', () => this._showAlert());
        this.appendChild(btn);
        this._btn = btn;
    }

    _showAlert() {
        const modal = document.createElement('alert-modal');
        modal.init({
            title: this._props.label,
            message: this._props.text,
            confirmLabel: this._props.label,
            onConfirm: () => {
                if (this._props.onConfirm) this._props.onConfirm();
            },
        });
        document.body.appendChild(modal);
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

customElements.define('destructive-button', DestructiveButton);
export default DestructiveButton;
