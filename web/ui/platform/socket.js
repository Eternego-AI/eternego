export class Socket {
    constructor(path) {
        this._path = path;
        this._ws = null;
        this._listeners = [];
        this._closed = false;
    }

    open() {
        if (this._ws) return;
        this._closed = false;
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${location.host}${this._path}`);
        ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                for (const fn of this._listeners) fn(data);
            } catch {}
        };
        ws.onclose = () => {
            this._ws = null;
            if (!this._closed) setTimeout(() => this.open(), 3000);
        };
        this._ws = ws;
    }

    close() {
        this._closed = true;
        if (this._ws) {
            this._ws.onclose = null;
            this._ws.close();
            this._ws = null;
        }
    }

    on(fn) {
        this._listeners.push(fn);
    }

    off(fn) {
        this._listeners = this._listeners.filter(f => f !== fn);
    }
}
