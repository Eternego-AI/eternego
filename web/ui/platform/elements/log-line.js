import Element from './element.js';

class LogLine extends Element {
    static _styled = false;
    static _css = `
        log-line {
            display: grid;
            grid-template-columns: 60px 80px 1fr;
            gap: var(--space-md);
            padding: var(--space-sm) 0;
            align-items: baseline;
            border-bottom: 1px solid var(--border-subtle);
            font-family: var(--font-mono);
            font-size: var(--text-sm);
        }
        log-line:last-child { border-bottom: none; }
        log-line .time {
            color: var(--text-dim);
            font-size: var(--text-xs);
            letter-spacing: 1px;
        }
        log-line .kind {
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-muted);
        }
        log-line[tone=warm] .kind { color: var(--warm-text); }
        log-line[tone=cool] .kind { color: var(--cool-text); }
        log-line[tone=vital] .kind { color: var(--vital-text); }
        log-line[tone=danger] .kind { color: var(--danger-text); }
        log-line .text {
            color: var(--text-body);
            line-height: 1.55;
        }
    `;

    render() {
        this.innerHTML = `
            <span class="time"></span>
            <span class="kind"></span>
            <span class="text"></span>
        `;
        const timeEl = this.querySelector('.time');
        const kindEl = this.querySelector('.kind');
        const textEl = this.querySelector('.text');

        const { time, kind, text, tone } = this._props;

        timeEl.textContent = time || '';
        kindEl.textContent = kind || '';
        textEl.textContent = text || '';
        if (tone) this.setAttribute('tone', tone);
    }
}

customElements.define('log-line', LogLine);
export default LogLine;
