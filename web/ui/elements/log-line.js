import Element from './element.js';

class LogLine extends Element {
    static _css = `
        log-line {
            display: block;
            font-size: var(--text-sm);
            line-height: 1.5;
            color: var(--boot-text);
            font-family: var(--font);
            white-space: pre-wrap;
            word-break: break-all;
        }
    `;
    render() {
        this.constructor._injectStyles();
        this.textContent = (this._props.text || '') + '\n';
    }
}

customElements.define('log-line', LogLine);
export default LogLine;
