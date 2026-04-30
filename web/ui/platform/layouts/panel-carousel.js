import Layout from './layout.js';

class PanelCarousel extends Layout {
    static _styled = false;
    static _css = `
        panel-carousel {
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
            height: 100%;
            min-height: 0;
        }
        panel-carousel .track {
            display: flex;
            flex: 1;
            min-height: 0;
            transition: transform var(--time-medium) var(--easing);
        }
        panel-carousel .panel {
            flex: 0 0 100%;
            min-width: 0;
            min-height: 0;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        panel-carousel .nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--surface-overlay);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-full);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--time-quick);
            z-index: 10;
            font-size: var(--text-lg);
        }
        panel-carousel .nav:hover:not(:disabled) {
            color: var(--text-primary);
            border-color: var(--border-hover);
        }
        panel-carousel .nav:disabled { opacity: 0.2; cursor: not-allowed; }
        panel-carousel .nav.prev { left: var(--space-md); }
        panel-carousel .nav.next { right: var(--space-md); }
    `;

    arrange() {
        const { panels = [], current = 0, onCurrentChange } = this._props;
        this.innerHTML = `
            <button class="nav prev" type="button" aria-label="Previous">‹</button>
            <div class="track"></div>
            <button class="nav next" type="button" aria-label="Next">›</button>
        `;
        const trackEl = this.querySelector('.track');
        const prevEl = this.querySelector('.prev');
        const nextEl = this.querySelector('.next');

        for (const panel of panels) {
            const wrap = document.createElement('div');
            wrap.className = 'panel';
            if (panel instanceof HTMLElement) {
                wrap.appendChild(panel);
            } else if (typeof panel === 'function') {
                const el = panel();
                if (el) wrap.appendChild(el);
            }
            trackEl.appendChild(wrap);
        }

        trackEl.style.transform = `translateX(-${current * 100}%)`;
        prevEl.disabled = current === 0;
        nextEl.disabled = current >= panels.length - 1;

        prevEl.addEventListener('click', () => onCurrentChange && onCurrentChange(Math.max(0, current - 1)));
        nextEl.addEventListener('click', () => onCurrentChange && onCurrentChange(Math.min(panels.length - 1, current + 1)));
    }
}

customElements.define('panel-carousel', PanelCarousel);
export default PanelCarousel;
