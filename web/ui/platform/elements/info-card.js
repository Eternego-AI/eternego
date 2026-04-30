import Element from './element.js';

class InfoCard extends Element {
    static _styled = false;
    static _css = `
        info-card {
            display: block;
            padding: var(--space-lg);
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
        }
        info-card .title {
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-muted);
            margin-bottom: var(--space-sm);
        }
        info-card .body {
            font-size: var(--text-base);
            color: var(--text-body);
            line-height: 1.55;
        }
        info-card[tone=warm] { border-color: var(--warm-border); background: var(--warm-bg); }
        info-card[tone=warm] .title { color: var(--warm-text); }
        info-card[tone=cool] { border-color: var(--cool-border); background: var(--cool-bg); }
        info-card[tone=cool] .title { color: var(--cool-text); }
        info-card[tone=danger] { border-color: var(--danger-border); background: var(--danger-bg); }
        info-card[tone=danger] .title { color: var(--danger-text); }
    `;

    render() {
        this.innerHTML = `
            <div class="title" hidden></div>
            <div class="body"></div>
        `;
        const titleEl = this.querySelector('.title');
        const bodyEl = this.querySelector('.body');

        const { title, body, tone } = this._props;

        if (title) { titleEl.textContent = title; titleEl.hidden = false; }
        bodyEl.textContent = body || '';
        if (tone) this.setAttribute('tone', tone);
    }
}

customElements.define('info-card', InfoCard);
export default InfoCard;
