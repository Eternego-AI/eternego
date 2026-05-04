export default class App {
    async init(props) {
        this._props = props || {};
        this._el = null;
        await this.start();
        return this;
    }

    start() {}
    activate() {}
    deactivate() {}

    get el() { return this._el; }
}
