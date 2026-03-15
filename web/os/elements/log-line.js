import Element from './element.js';

class LogLine extends Element {
    // init({ type, text })
    render() {
        const { type, text } = this._props;
        this.textContent = `[ ${type || 'signal'} ] ${text || ''}\n`;
    }
}

customElements.define('log-line', LogLine);
export default LogLine;
