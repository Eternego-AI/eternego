import Layout from './layout.js';

class CardLayout extends Layout {
    static _css = `
        card-layout { display: flex; flex: 1; min-height: 0; min-width: 0; }
        card-layout .cl-card {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
            background: var(--glass-bg);
            backdrop-filter: blur(24px) saturate(1.4);
            border: 1.5px solid var(--glass-border);
            border-radius: var(--radius-3xl);
            box-shadow: var(--glass-shadow);
            padding: 24px;
            color: var(--text-body);
            font-size: 14px;
            font-family: var(--font);
            position: relative;
        }
        card-layout .cl-card::before {
            content: '';
            position: absolute;
            top: 0; left: 20px; right: 20px; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        }
        card-layout .cl-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
        card-layout .cl-title { font-size: 13px; font-weight: 500; color: var(--text-primary); letter-spacing: 0.5px; }
        card-layout .cl-body { flex: 1; min-height: 0; font-size: 12px; color: var(--text-muted); line-height: 1.5; overflow: hidden; display: flex; flex-direction: column; }
    `;

    // init({ title })
    arrange() {
        this.constructor._injectStyles();
        const card = document.createElement('div');
        card.className = 'cl-card';
        if (this._props.title) {
            const header = document.createElement('div');
            header.className = 'cl-header';
            const h = document.createElement('h3');
            h.className = 'cl-title';
            h.textContent = this._props.title;
            header.appendChild(h);
            card.appendChild(header);
        }
        const body = document.createElement('div');
        body.className = 'cl-body';
        card.appendChild(body);
        this.appendChild(card);
        this._body = body;
    }

    get body() { return this._body; }
}

customElements.define('card-layout', CardLayout);
export default CardLayout;
