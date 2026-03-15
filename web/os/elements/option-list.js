import Element from './element.js';

class OptionList extends Element {
    // init({ options: [{ value, label, meta, fit, selected }], onSelect })
    render() {
        const { options, onSelect } = this._props;
        this.innerHTML = '';
        const container = document.createElement('div');
        container.className = 'wizard-options';

        for (const opt of options) {
            const el = document.createElement('div');
            el.className = 'wizard-option' + (opt.selected ? ' selected' : '');
            el.dataset.value = opt.value;
            el.innerHTML = `
                ${opt.fit !== undefined ? `<span class="wizard-option-fit">${opt.fit}</span>` : ''}
                <span class="wizard-option-name">${this._esc(opt.label)}</span>
                ${opt.meta ? `<span class="wizard-option-meta">${opt.meta}</span>` : ''}
            `;
            el.addEventListener('click', () => {
                container.querySelectorAll('.wizard-option').forEach(o => o.classList.remove('selected'));
                el.classList.add('selected');
                if (onSelect) onSelect(opt.value);
            });
            container.appendChild(el);
        }

        this.appendChild(container);
    }

    _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}

customElements.define('option-list', OptionList);
export default OptionList;
