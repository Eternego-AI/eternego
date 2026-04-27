import Block from './block.js';

class BlockMarkdown extends Block {
    static _css = `
        block-markdown {
            display: block;
            font-family: var(--font);
            font-size: var(--text-base);
            color: var(--text-body);
            line-height: 1.7;
            word-wrap: break-word;
        }
        block-markdown p { margin: 0 0 var(--space-md); }
        block-markdown p:last-child { margin-bottom: 0; }
        block-markdown strong { color: var(--text-primary); font-weight: 500; }
        block-markdown em { color: var(--text-primary); font-style: italic; }
        block-markdown code {
            background: var(--surface-hover);
            padding: 1px 6px;
            border-radius: var(--radius-sm);
            font-size: 0.9em;
            color: var(--accent-text);
        }
        block-markdown pre {
            background: var(--surface-recessed);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: var(--space-lg);
            overflow-x: auto;
            margin: var(--space-md) 0;
        }
        block-markdown pre code {
            background: none;
            padding: 0;
            color: var(--text-body);
        }
        block-markdown a {
            color: var(--accent-text);
            text-decoration: none;
            border-bottom: 1px solid var(--accent-border);
        }
        block-markdown a:hover { border-bottom-color: var(--accent); }
        block-markdown ul, block-markdown ol { padding-left: var(--space-xl); margin: 0 0 var(--space-md); }
        block-markdown li { margin-bottom: var(--space-xs); }
        block-markdown h1, block-markdown h2, block-markdown h3 {
            color: var(--text-primary);
            font-weight: 500;
            margin: var(--space-lg) 0 var(--space-md);
        }
        block-markdown h1 { font-size: 1.4em; }
        block-markdown h2 { font-size: 1.2em; }
        block-markdown h3 { font-size: 1.05em; }
        block-markdown blockquote {
            border-left: 2px solid var(--accent-border);
            padding-left: var(--space-lg);
            color: var(--text-secondary);
            margin: var(--space-md) 0;
        }
    `;

    render() {
        this.constructor._injectStyles();
        const md = this._props.markdown || '';
        this.innerHTML = this._parse(md);
    }

    _parse(src) {
        const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const lines = src.split('\n');
        const out = [];
        let inCode = false;
        let codeBuffer = [];
        let inList = false;
        let listKind = null;
        let para = [];

        const flushPara = () => {
            if (para.length) {
                const text = para.join(' ');
                out.push(`<p>${this._inline(esc(text))}</p>`);
                para = [];
            }
        };
        const flushList = () => {
            if (inList) {
                out.push(`</${listKind}>`);
                inList = false;
                listKind = null;
            }
        };

        for (const raw of lines) {
            const line = raw;
            if (line.startsWith('```')) {
                flushPara();
                flushList();
                if (inCode) {
                    out.push(`<pre><code>${esc(codeBuffer.join('\n'))}</code></pre>`);
                    codeBuffer = [];
                    inCode = false;
                } else {
                    inCode = true;
                }
                continue;
            }
            if (inCode) {
                codeBuffer.push(line);
                continue;
            }
            if (!line.trim()) {
                flushPara();
                flushList();
                continue;
            }
            const heading = line.match(/^(#{1,3})\s+(.+)$/);
            if (heading) {
                flushPara();
                flushList();
                const level = heading[1].length;
                out.push(`<h${level}>${this._inline(esc(heading[2]))}</h${level}>`);
                continue;
            }
            const quote = line.match(/^>\s+(.+)$/);
            if (quote) {
                flushPara();
                flushList();
                out.push(`<blockquote>${this._inline(esc(quote[1]))}</blockquote>`);
                continue;
            }
            const ul = line.match(/^[-*]\s+(.+)$/);
            const ol = line.match(/^\d+\.\s+(.+)$/);
            if (ul || ol) {
                flushPara();
                const kind = ul ? 'ul' : 'ol';
                if (!inList) {
                    out.push(`<${kind}>`);
                    inList = true;
                    listKind = kind;
                } else if (listKind !== kind) {
                    out.push(`</${listKind}><${kind}>`);
                    listKind = kind;
                }
                out.push(`<li>${this._inline(esc((ul || ol)[1]))}</li>`);
                continue;
            }
            para.push(line);
        }
        flushPara();
        flushList();
        return out.join('');
    }

    _inline(s) {
        return s
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }
}

customElements.define('block-markdown', BlockMarkdown);
export default BlockMarkdown;
