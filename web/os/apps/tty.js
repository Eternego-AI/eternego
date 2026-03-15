import App from './app.js';
import { terminal } from '../icons.js';

export default class TtyApp extends App {
    static appId = 'tty';
    static appName = 'TTY';
    static icon = terminal;

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
