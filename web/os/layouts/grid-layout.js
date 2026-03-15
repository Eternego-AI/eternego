import Layout from './layout.js';

class GridLayout extends Layout {
    // init({ onFocus })
    arrange() {
        this._currentFocus = null;

        this.addEventListener('click', (e) => {
            const widget = e.target.closest('[widget]');
            if (!widget) return;
            const name = widget.getAttribute('widget');
            if (this._props.onFocus) this._props.onFocus(name);
        });
    }

    addWidget(el) {
        // Wire the card's minimize button to unfocus
        const card = el.querySelector('card-layout');
        if (card) card._props.onMinimize = () => {
            if (this._props.onFocus) this._props.onFocus(null);
        };
        this.appendChild(el);
    }

    relayout(focusedName) {
        if (this._currentFocus === focusedName) return;

        const widgets = Array.from(this.children);
        const first = widgets.map(w => w.getBoundingClientRect());

        this._currentFocus = focusedName;
        this._applyFocus(focusedName);
        this.offsetHeight;

        const last = widgets.map(w => w.getBoundingClientRect());

        widgets.forEach((w, i) => {
            const f = first[i], l = last[i];
            if (!f.width || !l.width) return;
            const dx = f.left - l.left;
            const dy = f.top - l.top;
            const sx = f.width / l.width;
            const sy = f.height / l.height;
            if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5
                && Math.abs(sx - 1) < 0.01 && Math.abs(sy - 1) < 0.01) return;

            w.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;
            w.style.transformOrigin = 'top left';
            w.style.transition = 'none';
        });

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                widgets.forEach(w => {
                    w.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
                    w.style.transform = '';
                    w.addEventListener('transitionend', () => {
                        w.style.transition = '';
                        w.style.transform = '';
                        w.style.transformOrigin = '';
                    }, { once: true });
                });
            });
        });
    }

    _applyFocus(focusedName) {
        for (const w of this.children) {
            const name = w.getAttribute('widget');
            const isFocused = name === focusedName;
            w.classList.toggle('widget-focused', isFocused);
            w.classList.toggle('widget-unfocused', focusedName && !isFocused);
        }
    }
}

customElements.define('grid-layout', GridLayout);
export default GridLayout;
