import Element from './element.js';

class TextInput extends Element {
    // init({ label, placeholder, value, type, onSubmit })
    render() {
        const { label, placeholder, value, type, onSubmit } = this._props;
        this.innerHTML = '';

        if (label) {
            const lbl = document.createElement('label');
            lbl.className = 'wizard-label';
            lbl.textContent = label;
            this.appendChild(lbl);
        }

        const input = document.createElement('input');
        input.className = 'wizard-input';
        input.type = type || 'text';
        input.placeholder = placeholder || '';
        input.value = value || '';
        this.appendChild(input);

        this._input = input;

        if (onSubmit) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') onSubmit(input.value.trim());
            });
        }
    }

    get value() { return this._input?.value.trim() || ''; }
    focus() { this._input?.focus(); }
}

customElements.define('text-input', TextInput);
export default TextInput;
