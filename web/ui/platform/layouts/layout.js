import Painted from '../painted.js';

export default class Layout extends Painted {
    init(props) {
        this.constructor._injectStyles();
        this._props = props || {};
        this.arrange();
        return this;
    }

    arrange() {}
}
