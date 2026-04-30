export function toHTML(source) {
    const lines = String(source || '').split('\n');
    const out = [];
    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        if (/^```/.test(line)) {
            const buf = [];
            i++;
            while (i < lines.length && !/^```/.test(lines[i])) {
                buf.push(lines[i]);
                i++;
            }
            i++;
            out.push(`<pre><code>${escape(buf.join('\n'))}</code></pre>`);
            continue;
        }
        const h = line.match(/^(#{1,3})\s+(.*)$/);
        if (h) {
            const lvl = h[1].length;
            out.push(`<h${lvl}>${inline(h[2])}</h${lvl}>`);
            i++;
            continue;
        }
        if (/^>\s+/.test(line)) {
            const buf = [];
            while (i < lines.length && /^>\s+/.test(lines[i])) {
                buf.push(lines[i].replace(/^>\s+/, ''));
                i++;
            }
            out.push(`<blockquote>${inline(buf.join(' '))}</blockquote>`);
            continue;
        }
        if (/^[-*]\s+/.test(line)) {
            const buf = [];
            while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
                buf.push(`<li>${inline(lines[i].replace(/^[-*]\s+/, ''))}</li>`);
                i++;
            }
            out.push(`<ul>${buf.join('')}</ul>`);
            continue;
        }
        if (/^\d+\.\s+/.test(line)) {
            const buf = [];
            while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
                buf.push(`<li>${inline(lines[i].replace(/^\d+\.\s+/, ''))}</li>`);
                i++;
            }
            out.push(`<ol>${buf.join('')}</ol>`);
            continue;
        }
        if (line.trim() === '') {
            i++;
            continue;
        }
        const buf = [line];
        i++;
        while (i < lines.length && lines[i].trim() !== '' && !/^(#|>|[-*]\s|\d+\.\s|```)/.test(lines[i])) {
            buf.push(lines[i]);
            i++;
        }
        out.push(`<p>${inline(buf.join(' '))}</p>`);
    }
    return out.join('\n');
}

function escape(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function inline(s) {
    let out = escape(s);
    out = out.replace(/`([^`]+)`/g, (_, c) => `<code>${c}</code>`);
    out = out.replace(/\*\*([^*]+)\*\*/g, (_, c) => `<strong>${c}</strong>`);
    out = out.replace(/\*([^*]+)\*/g, (_, c) => `<em>${c}</em>`);
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, t, u) => `<a href="${u}" target="_blank" rel="noopener">${t}</a>`);
    return out;
}
