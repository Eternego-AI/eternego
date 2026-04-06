import Element from './element.js';

class StepPanel extends Element {
    static _css = `
        step-panel { flex: 1; display: flex; flex-direction: column; gap: var(--space-lg); overflow-y: auto; }
    `;
    render() {
        this.constructor._injectStyles();
        this.setAttribute('step', this._props.id);
        if (this._props.visible === false) this.style.display = 'none';
    }
}

customElements.define('step-panel', StepPanel);
export default StepPanel;
