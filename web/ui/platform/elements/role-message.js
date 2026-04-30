import Element from './element.js';

class RoleMessage extends Element {
    static _styled = false;
    static _css = `
        role-message { display: block; }
        role-message[role=them] {
            font-family: var(--font-serif);
            font-style: italic;
            font-weight: 300;
            font-size: var(--text-md);
            line-height: 1.7;
            color: var(--warm-text);
            padding-left: var(--space-xl);
            border-left: 1px solid var(--warm-border);
            margin: var(--space-lg) 0;
        }
        role-message[role=me] {
            font-family: var(--font-mono);
            font-size: var(--text-base);
            line-height: 1.55;
            color: var(--text-body);
            padding: var(--space-md) var(--space-lg);
            background: var(--surface-recessed);
            border-radius: var(--radius-md);
            margin: var(--space-md) 0;
            margin-left: auto;
            max-width: 75%;
        }
        role-message[role=system] {
            font-family: var(--font-mono);
            font-size: var(--text-xs);
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            text-align: center;
            margin: var(--space-md) 0;
        }
        role-message .image {
            display: block;
            max-width: 280px;
            max-height: 280px;
            border-radius: var(--radius-md);
            margin-bottom: var(--space-sm);
            border: 1px solid var(--border-subtle);
        }
        role-message .text { white-space: pre-wrap; }
        role-message .time {
            display: block;
            margin-top: var(--space-xs);
            font-family: var(--font-mono);
            font-style: normal;
            font-size: var(--text-xs);
            color: var(--text-dim);
            letter-spacing: 1px;
        }
    `;

    render() {
        this.innerHTML = `
            <img class="image" hidden>
            <div class="text"></div>
            <span class="time" hidden></span>
        `;
        const imgEl = this.querySelector('.image');
        const textEl = this.querySelector('.text');
        const timeEl = this.querySelector('.time');

        const { role = 'me', text, time, image, alt } = this._props;

        this.setAttribute('role', role);
        if (image) {
            imgEl.src = image;
            imgEl.alt = alt || '';
            imgEl.hidden = false;
        }
        textEl.textContent = text || '';
        if (time) {
            timeEl.textContent = time;
            timeEl.hidden = false;
        }
    }
}

customElements.define('role-message', RoleMessage);
export default RoleMessage;
