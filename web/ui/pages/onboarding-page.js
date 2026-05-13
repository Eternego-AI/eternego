/* <onboarding-page> — full-screen onboarding host.
   Renders one of: onboarding-cold (chooser), create-form, migrate-form.
   setProps({ step: 'cold' | 'create' | 'migrate' }).
   Emits: choose (detail.what), submit (detail.fields), back. */

class OnboardingPage extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._step = 'cold';
        this._hasPersonas = false;
        this.innerHTML = `<div class="p-onboard-host"></div>`;
        this._host = this.querySelector('.p-onboard-host');
        this.render();
    }

    setProps({ step, hasPersonas }) {
        if (step) this._step = step;
        if (hasPersonas !== undefined) this._hasPersonas = hasPersonas;
        this.render();
    }

    setError(message) {
        const form = this._host.firstElementChild;
        if (form?.setError) form.setError(message);
    }

    render() {
        this._host.innerHTML = '';
        let widget;
        if (this._step === 'create') {
            widget = document.createElement('create-form');
            widget.addEventListener('back',   () => this.dispatchEvent(new CustomEvent('back')));
            widget.addEventListener('submit', (e) => this.dispatchEvent(new CustomEvent('submit', { detail: e.detail })));
        } else if (this._step === 'migrate') {
            widget = document.createElement('migrate-form');
            widget.addEventListener('back', () => this.dispatchEvent(new CustomEvent('back')));
            widget.addEventListener('submit-migrate', (e) =>
                this.dispatchEvent(new CustomEvent('submit-migrate', { detail: e.detail })));
        } else {
            widget = document.createElement('onboarding-cold');
            widget.addEventListener('create',  () => this.dispatchEvent(new CustomEvent('choose', { detail: { what: 'create' } })));
            widget.addEventListener('migrate', () => this.dispatchEvent(new CustomEvent('choose', { detail: { what: 'migrate' } })));
            widget.addEventListener('cancel',  () => this.dispatchEvent(new CustomEvent('cancel')));
        }
        this._host.appendChild(widget);
        if (widget.setProps) widget.setProps({ hasPersonas: this._hasPersonas });
    }
}
customElements.define('onboarding-page', OnboardingPage);
