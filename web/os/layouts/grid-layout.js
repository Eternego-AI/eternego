import Layout from './layout.js';

class GridLayout extends Layout {
    // init({ onFocus })
    arrange() {
        this._currentFocus = null;
        this.className = 'widget-grid';

        this.addEventListener('click', (e) => {
            const card = e.target.closest('[widget]');
            if (!card) return;
            const name = card.getAttribute('widget');
            if (this._props.onFocus) this._props.onFocus(name);
        });
    }

    addWidget(el) {
        this.appendChild(el);
    }

    relayout(focusedName) {
        if (this._currentFocus === focusedName) return;

        const widgets = Array.from(this.children);
        const first = widgets.map(w => w.getBoundingClientRect());

        this._currentFocus = focusedName;
        this._applyLayout(focusedName);
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

    _applyLayout(focusedName) {
        const widgets = Array.from(this.children);
        if (!focusedName) {
            this._packLayout(widgets);
        } else {
            this._focusLayout(widgets, focusedName);
        }
    }

    _packLayout(widgets) {
        const items = widgets.map(w => ({
            el: w,
            cols: parseInt(w.getAttribute('columns')) || 1,
            rows: parseInt(w.getAttribute('rows')) || 1,
        }));

        const maxW = Math.max(...items.map(it => it.cols));
        const totalArea = items.reduce((s, it) => s + it.cols * it.rows, 0);
        const gridCols = Math.max(maxW, Math.round(Math.sqrt(totalArea)));
        const cap = 20;
        const occupied = Array.from({ length: cap }, () => Array(gridCols).fill(false));

        for (const item of items) {
            let placed = false;
            for (let r = 0; r <= cap - item.rows && !placed; r++) {
                for (let c = 0; c <= gridCols - item.cols && !placed; c++) {
                    let fits = true;
                    for (let dr = 0; dr < item.rows && fits; dr++)
                        for (let dc = 0; dc < item.cols && fits; dc++)
                            if (occupied[r + dr][c + dc]) fits = false;
                    if (fits) {
                        for (let dr = 0; dr < item.rows; dr++)
                            for (let dc = 0; dc < item.cols; dc++)
                                occupied[r + dr][c + dc] = true;
                        item.col = c;
                        item.row = r;
                        placed = true;
                    }
                }
            }
        }

        const usedCols = Math.max(...items.map(it => (it.col || 0) + it.cols));
        const usedRows = Math.max(...items.map(it => (it.row || 0) + it.rows));

        for (const it of items) {
            const c1 = Math.round((it.col || 0) / usedCols * 8) + 1;
            const c2 = Math.round(((it.col || 0) + it.cols) / usedCols * 8) + 1;
            const r1 = Math.round((it.row || 0) / usedRows * 8) + 1;
            const r2 = Math.round(((it.row || 0) + it.rows) / usedRows * 8) + 1;
            it.el.style.gridColumn = `${c1} / ${c2}`;
            it.el.style.gridRow = `${r1} / ${r2}`;
        }
    }

    _focusLayout(widgets, focusedName) {
        const focusedEl = widgets.find(w => w.getAttribute('widget') === focusedName);
        const others = widgets.filter(w => w !== focusedEl);

        if (focusedEl) {
            focusedEl.style.gridColumn = '1 / 8';
            focusedEl.style.gridRow = '1 / 8';
        }

        const rightCount = Math.min(others.length, 7);
        for (let i = 0; i < rightCount; i++) {
            others[i].style.gridColumn = '8';
            others[i].style.gridRow = `${i + 1}`;
        }

        const bottom = others.slice(rightCount, rightCount + 8);
        for (let i = 0; i < bottom.length; i++) {
            bottom[i].style.gridColumn = `${i + 1}`;
            bottom[i].style.gridRow = '8';
        }
    }
}

customElements.define('grid-layout', GridLayout);
export default GridLayout;
