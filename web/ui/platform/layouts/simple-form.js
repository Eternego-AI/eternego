import Layout from './layout.js';
import '../elements/input-text.js';
import '../elements/input-textarea.js';
import '../elements/input-options.js';
import '../elements/input-dropzone.js';
import '../elements/action-button.js';

class SimpleForm extends Layout {
    static _styled = false;
    static _css = `
        simple-form {
            display: flex;
            flex-direction: column;
            gap: var(--space-lg);
        }
        simple-form .actions {
            display: flex;
            gap: var(--space-md);
            justify-content: flex-end;
            margin-top: var(--space-md);
        }
        simple-form .error {
            padding: var(--space-md) var(--space-lg);
            background: var(--danger-bg);
            border: 1px solid var(--danger-border);
            border-radius: var(--radius-md);
            color: var(--danger-text);
            font-size: var(--text-sm);
        }
    `;

    arrange() {
        const { fields = [], values = {}, error, onChange, onSubmit, submitLabel, submitting } = this._props;
        this.innerHTML = '';

        for (const field of fields) {
            const tag = field.type === 'textarea' ? 'input-textarea'
                : field.type === 'options' ? 'input-options'
                : (field.type === 'file' || field.type === 'dropzone') ? 'input-dropzone'
                : 'input-text';
            const el = document.createElement(tag);
            el.init({
                ...field,
                value: values[field.name],
                onChange: (v) => {
                    values[field.name] = v;
                    onChange && onChange(field.name, v, values);
                },
            });
            this.appendChild(el);
        }

        if (error) {
            const errEl = document.createElement('div');
            errEl.className = 'error';
            errEl.textContent = error;
            this.appendChild(errEl);
        }

        if (submitLabel && onSubmit) {
            const actionsEl = document.createElement('div');
            actionsEl.className = 'actions';
            const submitEl = document.createElement('action-button');
            submitEl.init({
                label: submitting ? '...' : submitLabel,
                variant: 'primary',
                disabled: !!submitting,
                onClick: () => onSubmit(values),
            });
            actionsEl.appendChild(submitEl);
            this.appendChild(actionsEl);
        }
    }
}

customElements.define('simple-form', SimpleForm);
export default SimpleForm;
