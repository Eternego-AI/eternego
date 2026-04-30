import Element from './element.js';

class StatusDot extends Element {
    static _styled = false;
    static _css = `
        status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: var(--radius-full);
            background: var(--text-dim);
            transition: background var(--time-medium), box-shadow var(--time-medium);
        }
        status-dot[state=vital] {
            background: var(--vital);
            box-shadow: 0 0 8px var(--vital);
        }
        status-dot[state=danger] {
            background: var(--danger);
            box-shadow: 0 0 8px var(--danger);
        }
        status-dot[state=sleeping] {
            background: rgba(180, 160, 220, 0.7);
            box-shadow: 0 0 6px rgba(180, 160, 220, 0.5);
        }
        status-dot[state=warm] {
            background: var(--warm);
            box-shadow: 0 0 8px var(--warm);
        }
        status-dot[state=cool] {
            background: var(--cool);
            box-shadow: 0 0 8px var(--cool);
        }
    `;

    render() {
        const { state = 'idle' } = this._props;
        this.setAttribute('state', state);
    }
}

customElements.define('status-dot', StatusDot);
export default StatusDot;
