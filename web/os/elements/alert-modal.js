import Element from './element.js';

class AlertModal extends Element {
    // init({ title, message, confirmLabel, onConfirm, onCancel })
    render() {
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';

        const wrap = document.createElement('div');
        wrap.className = 'modal-card';

        const card = document.createElement('card-layout');
        card.init({ title: this._props.title || 'Confirm' });

        const msg = document.createElement('role-message');
        msg.init({ role: 'system', text: this._props.message || '' });
        card.body.appendChild(msg);

        const actions = document.createElement('div');
        actions.className = 'modal-actions';

        const cancel = document.createElement('action-button');
        cancel.init({ label: 'Cancel', onClick: () => this.close() });

        const confirm = document.createElement('action-button');
        confirm.init({
            label: this._props.confirmLabel || 'Confirm',
            primary: true,
            onClick: () => {
                this.close();
                if (this._props.onConfirm) this._props.onConfirm();
            },
        });

        actions.appendChild(cancel);
        actions.appendChild(confirm);
        card.body.appendChild(actions);

        wrap.appendChild(card);
        this.appendChild(backdrop);
        this.appendChild(wrap);

        backdrop.addEventListener('click', () => this.close());
    }

    close() {
        if (this._props.onCancel) this._props.onCancel();
        this.remove();
    }
}

customElements.define('alert-modal', AlertModal);
export default AlertModal;
