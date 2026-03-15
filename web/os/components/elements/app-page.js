import OS from '../../os.js';

class AppPage extends HTMLElement {
    connectedCallback() {
        this._name = this.getAttribute('name');

        // Wrap existing children in grid, add backdrop + minimize
        const children = Array.from(this.children);
        const backdrop = document.createElement('div');
        backdrop.className = 'page-backdrop';

        const btn = document.createElement('button');
        btn.className = 'minimize-btn';
        btn.innerHTML = '&minus;';
        btn.addEventListener('click', () => OS.minimize());

        const grid = document.createElement('div');
        grid.className = 'widget-grid';
        for (const child of children) grid.appendChild(child);

        this.appendChild(backdrop);
        this.appendChild(btn);
        this.appendChild(grid);

        this._grid = grid;

        // Widget clicks → focus
        grid.addEventListener('click', (e) => {
            const card = e.target.closest('[widget]');
            if (!card || OS.focusedWidget) return;
            OS.focus(card.getAttribute('widget'));
        });

        // React to navigation
        OS.onNavigate(({ app, widget }) => {
            if (app === this._name) {
                this.classList.add('active');
            } else {
                this.classList.remove('active', 'widget-focused');
                return;
            }

            if (widget) {
                this.classList.add('widget-focused');
                this._grid.querySelectorAll('[widget]').forEach(el => {
                    el.classList.toggle('focused', el.getAttribute('widget') === widget);
                });
            } else {
                this.classList.remove('widget-focused');
                this._grid.querySelectorAll('[widget]').forEach(el => {
                    el.classList.remove('focused');
                });
            }
        });
    }
}

customElements.define('app-page', AppPage);
