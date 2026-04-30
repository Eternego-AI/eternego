import Painted from '../painted.js';

export default class Element extends Painted {
    init(props) {
        this.constructor._injectStyles();
        this._props = props || {};
        this.render();
        return this;
    }

    render() {}
}
