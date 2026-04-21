import Element from './element.js';

export default class Input extends Element {
    submit(value) {
        this.dispatchEvent(new CustomEvent('submit', { detail: { value }, bubbles: true }));
    }
    focusFirst() {}
}
