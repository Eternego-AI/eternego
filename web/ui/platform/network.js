export async function call(method, url, body) {
    const init = { method };
    if (body !== undefined) {
        if (body instanceof FormData) {
            init.body = body;
        } else {
            init.headers = { 'Content-Type': 'application/json' };
            init.body = JSON.stringify(body);
        }
    }
    const res = await fetch(url, init);
    if (!res.ok) {
        let detail = '';
        try { detail = (await res.json()).detail || ''; } catch {}
        throw new Error(detail || res.statusText || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    return res.text();
}

export const get = (url) => call('GET', url);
export const post = (url, body) => call('POST', url, body);

export async function download(url, filename) {
    const res = await fetch(url);
    if (!res.ok) {
        let detail = '';
        try { detail = (await res.json()).detail || ''; } catch {}
        throw new Error(detail || res.statusText || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(objectUrl);
}
