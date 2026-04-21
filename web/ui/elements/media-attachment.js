import Element from './element.js';

class MediaAttachment extends Element {
    static _css = `
        media-attachment {
            display: inline-flex;
            flex-direction: column;
            gap: var(--space-xs);
            max-width: 70%;
            padding: var(--space-xs) 0;
            animation: ma-arrive 0.3s var(--ease);
        }
        @keyframes ma-arrive { from { opacity: 0; transform: translateY(4px); } }
        media-attachment .ma-image {
            max-width: 100%;
            max-height: 320px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-subtle);
            background: var(--surface-recessed);
            cursor: zoom-in;
            display: block;
            object-fit: contain;
        }
        media-attachment .ma-image:hover { border-color: var(--border-hover); }
        media-attachment .ma-caption {
            font-size: var(--text-base);
            line-height: 1.65;
            color: var(--text-body);
        }
        media-attachment.ma-person .ma-caption { color: var(--accent-text); }
        media-attachment.ma-persona .ma-caption { color: var(--text-body); font-weight: 300; }
        media-attachment .ma-time {
            font-size: var(--text-xs);
            color: var(--text-dim);
            white-space: nowrap;
        }
    `;

    // init({ role, source, caption, time })
    render() {
        this.constructor._injectStyles();
        this.className = `ma-${this._props.role}`;

        const img = document.createElement('img');
        img.className = 'ma-image';
        img.src = this._props.source;
        img.alt = this._props.caption || 'image';
        img.addEventListener('click', () => window.open(this._props.source, '_blank'));
        this.appendChild(img);

        if (this._props.caption) {
            const cap = document.createElement('div');
            cap.className = 'ma-caption';
            cap.textContent = this._props.caption;
            if (this._props.time) {
                const t = document.createElement('span');
                t.className = 'ma-time';
                t.textContent = ' ' + this._props.time;
                cap.appendChild(t);
            }
            this.appendChild(cap);
        } else if (this._props.time) {
            const t = document.createElement('div');
            t.className = 'ma-time';
            t.textContent = this._props.time;
            this.appendChild(t);
        }
    }
}

customElements.define('media-attachment', MediaAttachment);
export default MediaAttachment;
