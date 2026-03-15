export default class Widget extends HTMLElement {
    static columns = 1;
    static rows = 1;
    init(props) {
        this._props = props;
        this.setAttribute('widget', this.constructor.widgetId || props.widgetId || '');
        this.style.setProperty('--cols', this.constructor.columns);
        this.style.setProperty('--rows', this.constructor.rows);
        this.build();
    }
    build() {}

    setFocused(focused) {
        this.classList.toggle('focused', focused);
    }
}
