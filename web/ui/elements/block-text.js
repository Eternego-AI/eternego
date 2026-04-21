import Block from './block.js';

class BlockText extends Block {
    static _css = `
        block-text {
            display: block;
            font-family: var(--font);
            font-size: var(--text-base);
            color: var(--text-body);
            line-height: 1.7;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    `;

    render() {
        this.constructor._injectStyles();
        this.textContent = this._props.text || '';
    }
}

customElements.define('block-text', BlockText);
export default BlockText;
