import Layout from './layout.js';
import './simple-form.js';
import '../elements/action-button.js';

class StepForm extends Layout {
    static _styled = false;
    static _css = `
        step-form {
            display: flex;
            flex-direction: column;
            gap: var(--space-xl);
        }
        step-form .heading {
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
        }
        step-form .progress {
            display: flex;
            gap: 4px;
        }
        step-form .progress .dot {
            flex: 1;
            height: 2px;
            background: var(--border-subtle);
            border-radius: 1px;
            transition: background var(--time-medium);
        }
        step-form .progress .dot.done { background: var(--accent); }
        step-form .progress .dot.current { background: var(--accent-text); }
        step-form .title {
            font-size: var(--text-lg);
            color: var(--text-primary);
            font-weight: 500;
        }
        step-form .subtitle {
            font-size: var(--text-sm);
            color: var(--text-muted);
            line-height: 1.55;
        }
        step-form .description {
            font-size: var(--text-base);
            color: var(--text-secondary);
            line-height: 1.7;
            display: flex;
            flex-direction: column;
            gap: var(--space-md);
        }
        step-form .description[hidden] { display: none; }
        step-form .description strong {
            color: var(--text-primary);
            font-weight: 500;
        }
        step-form .body:empty { display: none; }
        step-form .body.optional {
            display: flex;
            justify-content: center;
            padding: var(--space-2xl) 0;
        }
        step-form .actions {
            display: flex;
            justify-content: space-between;
            gap: var(--space-md);
        }
        step-form .actions .left,
        step-form .actions .right {
            display: flex;
            gap: var(--space-md);
        }
    `;

    arrange() {
        const { steps = [], current = 0, values = {}, error, onChange, onStepChange, onSubmit, onCancel, submitting } = this._props;
        const step = steps[current];
        if (!step) return;

        this.innerHTML = `
            <div class="heading">
                <div class="progress"></div>
                <div class="title"></div>
                <div class="subtitle" hidden></div>
                <div class="description" hidden></div>
            </div>
            <div class="body"></div>
            <div class="actions">
                <div class="left"></div>
                <div class="right"></div>
            </div>
        `;

        const progressEl = this.querySelector('.progress');
        const titleEl = this.querySelector('.title');
        const subtitleEl = this.querySelector('.subtitle');
        const descriptionEl = this.querySelector('.description');
        const bodyEl = this.querySelector('.body');
        const leftEl = this.querySelector('.actions .left');
        const rightEl = this.querySelector('.actions .right');

        for (let i = 0; i < steps.length; i++) {
            const dot = document.createElement('span');
            dot.className = 'dot' + (i < current ? ' done' : i === current ? ' current' : '');
            progressEl.appendChild(dot);
        }
        titleEl.textContent = step.title || '';
        if (step.subtitle) {
            subtitleEl.textContent = step.subtitle;
            subtitleEl.hidden = false;
        }
        if (step.description) {
            descriptionEl.innerHTML = step.description;
            descriptionEl.hidden = false;
        }

        if (step.fields && step.fields.length) {
            const form = document.createElement('simple-form');
            form.init({
                fields: step.fields,
                values,
                error,
                onChange,
            });
            bodyEl.appendChild(form);
        } else if (step.optional) {
            bodyEl.classList.add('optional');
            const addBtn = document.createElement('action-button');
            addBtn.init({
                label: step.optional.prompt,
                variant: 'ghost',
                onClick: () => step.optional.onAdd && step.optional.onAdd(),
            });
            bodyEl.appendChild(addBtn);
        }

        if (current > 0) {
            const back = document.createElement('action-button');
            back.init({
                label: 'Back',
                variant: 'ghost',
                onClick: () => onStepChange && onStepChange(current - 1, values),
            });
            leftEl.appendChild(back);
        } else if (onCancel) {
            const cancel = document.createElement('action-button');
            cancel.init({
                label: 'Cancel',
                variant: 'ghost',
                onClick: () => onCancel(),
            });
            leftEl.appendChild(cancel);
        }

        const isLast = current === steps.length - 1;
        const next = document.createElement('action-button');
        next.init({
            label: submitting ? '...' : (isLast ? 'Finish' : 'Next'),
            variant: 'primary',
            disabled: !!submitting,
            onClick: () => {
                if (isLast) {
                    onSubmit && onSubmit(values);
                } else {
                    onStepChange && onStepChange(current + 1, values);
                }
            },
        });
        rightEl.appendChild(next);
    }
}

customElements.define('step-form', StepForm);
export default StepForm;
