import Element from './element.js';
import { send, hash, globe } from '../icons.js';

const CHANNEL_ICONS = {
    telegram: send,
    discord: hash,
    web: globe,
};

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
        media-attachment .ma-meta {
            display: inline-flex;
            align-items: center;
            gap: var(--space-xs);
            margin-left: var(--space-sm);
            color: var(--text-dim);
            white-space: nowrap;
            vertical-align: baseline;
        }
        media-attachment .ma-channel {
            display: inline-flex;
            align-items: center;
            color: var(--text-muted);
        }
        media-attachment .ma-channel svg { display: block; }
    `;

    // init({ role, source, caption, time, channel })
    render() {
        this.constructor._injectStyles();
        this.className = `ma-${this._props.role}`;

        const img = document.createElement('img');
        img.className = 'ma-image';
        img.src = this._props.source;
        img.alt = this._props.caption || 'image';
        img.addEventListener('click', () => window.open(this._props.source, '_blank'));
        this.appendChild(img);

        const channelType = this._props.channel;
        const hasChannel = !!channelType && CHANNEL_ICONS[channelType];

        if (this._props.caption) {
            const cap = document.createElement('div');
            cap.className = 'ma-caption';
            cap.textContent = this._props.caption;
            const meta = this._buildMeta(hasChannel, channelType, this._props.time);
            if (meta) cap.appendChild(meta);
            this.appendChild(cap);
        } else if (this._props.time || hasChannel) {
            const meta = this._buildMeta(hasChannel, channelType, this._props.time);
            meta.classList.add('ma-time');
            this.appendChild(meta);
        }
    }

    _buildMeta(hasChannel, channelType, time) {
        if (!hasChannel && !time) return null;
        const meta = document.createElement('span');
        meta.className = 'ma-meta';
        if (hasChannel) {
            const ch = document.createElement('span');
            ch.className = 'ma-channel';
            ch.title = channelType;
            ch.innerHTML = CHANNEL_ICONS[channelType](12);
            meta.appendChild(ch);
        }
        if (time) {
            const t = document.createElement('span');
            t.className = 'ma-time';
            t.textContent = time;
            meta.appendChild(t);
        }
        return meta;
    }
}

customElements.define('media-attachment', MediaAttachment);
export default MediaAttachment;
