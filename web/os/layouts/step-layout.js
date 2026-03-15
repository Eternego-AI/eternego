import Layout from './layout.js';

class StepLayout extends Layout {
    // init({ steps: string[] }) — step IDs that get dot indicators
    arrange() {
        this._dotSteps = this._props.steps || [];
        this._panels = [];
        this._activeId = null;

        this._dots = document.createElement('div');
        this._dots.className = 'wizard-dots';
        this.appendChild(this._dots);
    }

    addPanel(panel) {
        panel.style.display = 'none';
        this.insertBefore(panel, this._dots);
        this._panels.push(panel);
    }

    go(stepId) {
        this._activeId = stepId;
        for (const p of this._panels) {
            const id = p.getAttribute('step');
            p.style.display = id === stepId ? '' : 'none';
        }
        if (this._dotSteps.includes(stepId)) {
            this._renderDots();
        } else {
            this._dots.style.display = 'none';
        }
    }

    _renderDots() {
        if (this._dotSteps.length <= 1) { this._dots.style.display = 'none'; return; }
        this._dots.style.display = '';
        this._dots.innerHTML = this._dotSteps.map(id =>
            `<span class="wizard-dot${id === this._activeId ? ' active' : ''}"></span>`
        ).join('');
    }
}

customElements.define('step-layout', StepLayout);
export default StepLayout;
