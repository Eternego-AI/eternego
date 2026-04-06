import Layout from './layout.js';

class StepLayout extends Layout {
    static _css = `
        step-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; }
        step-layout .sl-dots { display: flex; justify-content: center; gap: 6px; padding-top: 12px; }
        step-layout .sl-dot {
            width: 6px; height: 6px; border-radius: var(--radius-full);
            background: var(--text-ghost); transition: background 0.3s, transform 0.3s;
        }
        step-layout .sl-dot.active { background: var(--accent); transform: scale(1.4); }
    `;

    arrange() {
        this.constructor._injectStyles();
        this._dotSteps = this._props.steps || [];
        this._panels = [];
        this._activeId = null;
        this._dots = document.createElement('div');
        this._dots.className = 'sl-dots';
        this.appendChild(this._dots);
    }

    addPanel(panel) {
        panel.style.display = 'none';
        this.insertBefore(panel, this._dots);
        this._panels.push(panel);
    }

    go(stepId) {
        this._activeId = stepId;
        for (const p of this._panels) p.style.display = p.getAttribute('step') === stepId ? '' : 'none';
        if (this._dotSteps.includes(stepId)) {
            this._dots.style.display = '';
            this._dots.innerHTML = this._dotSteps.map(id => `<span class="sl-dot${id === stepId ? ' active' : ''}"></span>`).join('');
        } else {
            this._dots.style.display = 'none';
        }
    }
}

customElements.define('step-layout', StepLayout);
export default StepLayout;
