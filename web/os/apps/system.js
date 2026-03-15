import App from './app.js';
import OS from '../index.js';
import { settings } from '../icons.js';

export default class SystemApp extends App {
    static appId = 'system';
    static appName = 'System';
    static icon = settings;

    // init({ signals: Feed })
    start() {
        const div = document.createElement('div');
        div.id = 'system-app';

        const signals = document.createElement('signal-log-widget');
        signals.init({
            signals: this._props.signals,
            getSignalsFor: (id) => OS.signalsFor(id),
        });

        div.appendChild(signals);
        this._el = div;
        this._widgets = [signals];
    }

    widgets() { return this._widgets; }
    get el() { return this._el; }
}
