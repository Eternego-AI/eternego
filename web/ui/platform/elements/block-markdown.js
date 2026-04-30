import Element from './element.js';
import { toHTML } from '../markdown.js';

class BlockMarkdown extends Element {
    static _styled = false;
    static _css = `
        block-markdown { display: block; line-height: 1.7; color: var(--text-body); }
        block-markdown h1, block-markdown h2, block-markdown h3 {
            font-family: var(--font-mono);
            font-weight: 500;
            color: var(--text-primary);
            margin: var(--space-xl) 0 var(--space-md);
            letter-spacing: 0.5px;
        }
        block-markdown h1 { font-size: var(--text-lg); }
        block-markdown h2 {
            font-size: var(--text-sm);
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--cool-text);
        }
        block-markdown h3 {
            font-size: var(--text-sm);
            color: var(--text-secondary);
        }
        block-markdown p { margin: var(--space-md) 0; }
        block-markdown ul, block-markdown ol {
            padding-left: var(--space-xl);
            margin: var(--space-md) 0;
        }
        block-markdown li { margin: var(--space-xs) 0; }
        block-markdown strong { color: var(--text-primary); font-weight: 500; }
        block-markdown em { color: var(--warm-text); font-style: italic; }
        block-markdown code {
            font-family: var(--font-mono);
            font-size: 0.92em;
            padding: 2px 6px;
            background: var(--surface-recessed);
            border-radius: var(--radius-sm);
            color: var(--cool-text);
        }
        block-markdown pre {
            margin: var(--space-md) 0;
            padding: var(--space-md);
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            overflow-x: auto;
        }
        block-markdown pre code {
            padding: 0;
            background: none;
            color: var(--text-body);
        }
        block-markdown blockquote {
            margin: var(--space-md) 0;
            padding-left: var(--space-lg);
            border-left: 1px solid var(--warm-border);
            color: var(--warm-text);
            font-family: var(--font-serif);
            font-style: italic;
        }
    `;

    render() {
        const { source = '' } = this._props;
        this.innerHTML = toHTML(source);
    }
}

customElements.define('block-markdown', BlockMarkdown);
export default BlockMarkdown;
