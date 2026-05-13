/* HTML escape — shared helper for innerHTML composition.
   Used across layers; lives in platform because it's a pure transform with no domain knowledge. */

export function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
