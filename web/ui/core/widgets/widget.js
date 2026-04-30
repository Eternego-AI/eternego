import Painted from '../../platform/painted.js';

export default class Widget extends Painted {
    init(props) {
        this.constructor._injectStyles();
        this._props = props || {};
        this.build();
        return this;
    }

    build() {}
}
