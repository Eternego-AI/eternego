import Element from './element.js';

class LogLine extends Element {
    // init({ time, text })
    render() {
        const { time, text } = this._props;
        const ts = time ? new Date(time / 1e6).toLocaleTimeString() : '';
        this.textContent = `${ts}  ${text || ''}\n`;
    }
}

customElements.define('log-line', LogLine);
export default LogLine;
