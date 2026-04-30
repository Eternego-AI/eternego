export class Router {
    constructor() {
        this._routes = [];
        this._fallback = null;
        window.addEventListener('popstate', () => this.match());
    }

    add(pattern, handler) {
        const parts = pattern.split('/').filter(Boolean);
        const keys = [];
        const regex = new RegExp('^/' + parts.map(p => {
            if (p.startsWith('{') && p.endsWith('}')) {
                keys.push(p.slice(1, -1));
                return '([^/]+)';
            }
            return p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }).join('/') + '/?$');
        this._routes.push({ regex, keys, handler });
    }

    fallback(handler) {
        this._fallback = handler;
    }

    go(pathname) {
        history.pushState(null, '', pathname);
        this.match();
    }

    match() {
        const path = location.pathname || '/';
        for (const route of this._routes) {
            const m = path.match(route.regex);
            if (m) {
                const params = {};
                route.keys.forEach((key, i) => params[key] = m[i + 1]);
                route.handler(params);
                return;
            }
        }
        if (this._fallback) this._fallback();
    }
}
