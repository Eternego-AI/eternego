import Element from './element.js';

class StepPanel extends Element {
    // init({ id })
    render() {
        this.setAttribute('step', this._props.id);
        this.className = 'wizard-steps';
    }
}

customElements.define('step-panel', StepPanel);
export default StepPanel;
