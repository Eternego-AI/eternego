import Layout from './layout.js';

class HorizontalTimeline extends Layout {
    static _styled = false;
    static _css = `
        horizontal-timeline {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            padding: var(--space-sm) var(--space-xl);
            border-bottom: 1px solid var(--border-subtle);
            overflow-x: auto;
            white-space: nowrap;
            scrollbar-width: none;
        }
        horizontal-timeline::-webkit-scrollbar { display: none; }
        horizontal-timeline .marker {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: var(--space-xs) var(--space-sm);
            background: transparent;
            border: 1px solid transparent;
            border-radius: var(--radius-sm);
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: var(--text-xs);
            letter-spacing: 1px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all var(--time-quick);
        }
        horizontal-timeline .marker:hover { color: var(--text-secondary); }
        horizontal-timeline .marker.active {
            color: var(--warm-text);
            border-color: var(--warm-border);
            background: var(--warm-bg);
        }
        horizontal-timeline .marker.live { color: var(--vital-text); }
        horizontal-timeline .marker.live.active {
            border-color: var(--vital-border);
            background: var(--vital-bg);
        }
        horizontal-timeline .marker .dot {
            width: 6px;
            height: 6px;
            border-radius: var(--radius-full);
            background: var(--text-dim);
        }
        horizontal-timeline .marker.active .dot { background: var(--warm); }
        horizontal-timeline .marker.live .dot {
            background: var(--vital);
            box-shadow: 0 0 6px var(--vital);
        }
    `;

    arrange() {
        const { items = [], currentId, onSelect } = this._props;
        this.innerHTML = '';

        for (const item of items) {
            const m = document.createElement('button');
            m.type = 'button';
            m.className = 'marker';
            if (item.id === currentId) m.classList.add('active');
            if (item.kind === 'live') m.classList.add('live');
            m.innerHTML = `<span class="dot"></span><span class="label"></span>`;
            m.querySelector('.label').textContent = item.label;
            m.addEventListener('click', () => onSelect && onSelect(item.id));
            this.appendChild(m);
        }

        requestAnimationFrame(() => {
            const active = this.querySelector('.marker.active');
            if (active) active.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        });
    }
}

customElements.define('horizontal-timeline', HorizontalTimeline);
export default HorizontalTimeline;
