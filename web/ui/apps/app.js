export default class App {
    static appId = '';
    static appName = '';
    init(props) { this._props = props; this.start(); return this; }
    start() {}
    activate() {}
    deactivate() {}
    get el() { return this._el; }
}
