export default class App {
    static appId = '';
    static appName = '';
    static icon = '';
    init(props) { this._props = props; this.start(); }
    start() {}
    widgets() { return []; }
}
