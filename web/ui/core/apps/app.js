export default class App {
    init(props) {
        this._props = props || {};
        this._el = null;
        this.start();
        return this;
    }

    start() {}
    activate() {}
    deactivate() {}

    get el() { return this._el; }
}
