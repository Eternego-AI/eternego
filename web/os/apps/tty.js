import App from './app.js';
import OS from '../index.js';

export default class TtyApp extends App {
    static appId = 'system';
    static appName = 'System';
    static icon = '⚙';

    // init({ signals: Feed })
    start() {
        const div = document.createElement('div');
        div.id = 'tty-app';

        const stdout = document.createElement('stdout-widget');
        stdout.init({ signals: this._props.signals });

        div.appendChild(stdout);
        this._el = div;
        this._widgets = [stdout];
    }

    widgets() { return this._widgets; }
    get el() { return this._el; }
}
