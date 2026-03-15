export default class Widget extends HTMLElement {
    static columns = 1;
    static rows = 1;
    init(props) { this._props = props; this.build(); }
    build() {}
}
