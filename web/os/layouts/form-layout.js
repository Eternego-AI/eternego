import Layout from './layout.js';

class FormLayout extends Layout {
    // init({ onSubmit }) — children (elements) added via addField()
    arrange() {
        this._fields = [];
    }

    addField(element) {
        this._fields.push(element);
        this.appendChild(element);
    }

    values() {
        const result = {};
        for (const f of this._fields) {
            if (f.value !== undefined && f._props?.name) {
                result[f._props.name] = f.value;
            }
        }
        return result;
    }

    submit() {
        if (this._props.onSubmit) this._props.onSubmit(this.values());
    }
}

customElements.define('form-layout', FormLayout);
export default FormLayout;
