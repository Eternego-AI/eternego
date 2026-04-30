import Layout from './layout.js';

class TailList extends Layout {
    static _styled = false;
    static _css = `
        tail-list {
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow-y: auto;
            padding: var(--space-lg) var(--space-xl);
            gap: var(--space-md);
        }
        tail-list .empty {
            margin: auto;
            color: var(--text-dim);
            text-align: center;
            font-size: var(--text-sm);
        }
    `;

    arrange() {
        const { items = [], renderItem, empty } = this._props;
        this.innerHTML = '';

        if (items.length === 0 && empty) {
            const emptyEl = document.createElement('div');
            emptyEl.className = 'empty';
            emptyEl.textContent = empty;
            this.appendChild(emptyEl);
            return;
        }

        for (const item of items) {
            const el = renderItem(item);
            if (el) this.appendChild(el);
        }

        requestAnimationFrame(() => { this.scrollTop = this.scrollHeight; });
    }
}

customElements.define('tail-list', TailList);
export default TailList;
