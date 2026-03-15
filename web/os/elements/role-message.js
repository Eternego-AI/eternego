import Element from './element.js';

class RoleMessage extends Element {
    // init({ role, text })
    render() {
        const { role, text } = this._props;
        this.className = `chat-msg chat-msg-${role}`;
        this.textContent = text;
    }
}

customElements.define('role-message', RoleMessage);
export default RoleMessage;
