import Element from './element.js';

class MediaAttachment extends Element {
    static _styled = false;
    static _css = `
        media-attachment { display: block; }
        media-attachment img {
            display: block;
            max-width: 100%;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-subtle);
        }
        media-attachment .caption {
            margin-top: var(--space-sm);
            font-size: var(--text-sm);
            color: var(--text-muted);
            font-style: italic;
        }
    `;

    render() {
        this.innerHTML = `
            <img>
            <div class="caption" hidden></div>
        `;
        const imgEl = this.querySelector('img');
        const captionEl = this.querySelector('.caption');

        const { src, alt, caption } = this._props;

        imgEl.src = src || '';
        imgEl.alt = alt || '';
        if (caption) {
            captionEl.textContent = caption;
            captionEl.hidden = false;
        }
    }
}

customElements.define('media-attachment', MediaAttachment);
export default MediaAttachment;
