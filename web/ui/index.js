/* index.js — orchestrator. API surface, router, socket, theme, signal handling.
   Owns session state. Hands data down to pages by setProps. */

import { Router } from './platform/router.js';
import { Socket } from './platform/socket.js';
import { get, post } from './platform/network.js';

const state = {
    personas: [],
    currentPersonaId: null,
    currentTab: 'chat',
    socket: null,
    socketPersonaId: null,
    page: null,
    pendingTrace: [],   /* signals accumulated since the last persona message */
    signalHistory: [],  /* last 50 signals for status-view; never drained */
};

/* ── Theme ───────────────────────────────────────────────────────── */

function getTheme() {
    return localStorage.getItem('eternego.theme') || 'system';
}
function setTheme(v) {
    if (!['light', 'dark', 'system'].includes(v)) v = 'system';
    localStorage.setItem('eternego.theme', v);
    document.documentElement.setAttribute('data-theme', v);
}
window.eternego = window.eternego || {};
window.eternego.getTheme = getTheme;
window.eternego.setTheme = setTheme;
setTheme(getTheme());

/* ── API ─────────────────────────────────────────────────────────── */

async function listPersonas() {
    try { state.personas = (await get('/api/personas')).personas || []; }
    catch { state.personas = []; }
    return state.personas;
}

async function getConversation(id) {
    try { return (await get(`/api/persona/${id}/conversation`)).messages || []; }
    catch { return []; }
}

async function getDiagnose(id) {
    try { return await get(`/api/persona/${id}/diagnose`); }
    catch { return null; }
}

async function getKnowledge(id) {
    try { return await get(`/api/persona/${id}/knowledge`); }
    catch { return { memory: {}, instruction: [] }; }
}

async function getCalendar(id, monthStr) {
    /* monthStr: 'YYYY-MM'. Compute the window as [first of month, first of next). */
    const ymd = monthStr || todayMonth();
    const [y, m] = ymd.split('-').map(Number);
    const start = `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-01`;
    const ny = m === 12 ? y + 1 : y;
    const nm = m === 12 ? 1 : m + 1;
    const end = `${String(ny).padStart(4, '0')}-${String(nm).padStart(2, '0')}-01`;
    try { return { month: ymd, ...(await get(`/api/persona/${id}/calendar?start=${start}&end=${end}`)) }; }
    catch { return { month: ymd, start, end, history: {}, destiny: {} }; }
}

function todayMonth() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

async function hearPersona(id, message) {
    try { await post(`/api/persona/${id}/hear`, { message }); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function seePersona(id, file, caption) {
    const form = new FormData();
    form.append('image', file);
    if (caption) form.append('caption', caption);
    try { await post(`/api/persona/${id}/see`, form); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function stopPersona(id) {
    try { await post(`/api/persona/${id}/stop`); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function restartPersona(id) {
    try { await post(`/api/persona/${id}/restart`); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function deletePersona(id) {
    try { await post(`/api/persona/${id}/delete`); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function sleepPersona(id) {
    try { await post(`/api/persona/${id}/sleep`); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function pairChannel(id, code) {
    try { await post(`/api/persona/${id}/pair`, { code }); return { ok: true }; }
    catch (e) { return { ok: false, error: e.message }; }
}

async function updatePersona(id, body) {
    try {
        const result = await post(`/api/persona/${id}/update`, body);
        return { ok: true, result };
    } catch (e) { return { ok: false, error: e.message }; }
}

async function createPersona(fields) {
    try {
        const result = await post('/api/persona/create', fields);
        return { ok: true, id: result.persona?.id, persona: result.persona };
    } catch (e) { return { ok: false, error: e.message }; }
}

async function migratePersona(formData) {
    try {
        const result = await post('/api/persona/migrate', formData);
        return { ok: true, id: result.persona?.id, persona: result.persona };
    } catch (e) { return { ok: false, error: e.message }; }
}

function mediaUrl(personaId, source) {
    const base = (source || '').split('/').pop();
    return `/api/persona/${personaId}/media/${encodeURIComponent(base)}`;
}

/* ── Socket ──────────────────────────────────────────────────────── */

function connectPersonaSocket(id) {
    if (state.socketPersonaId === id && state.socket) return;
    if (state.socket) state.socket.close();
    state.socketPersonaId = id;
    state.pendingTrace = [];
    state.signalHistory = [];
    state.socket = new Socket(`/ws/${id}`);
    state.socket.on(handleSocketMessage);
    state.socket.open();
}

function disconnectSocket() {
    if (state.socket) { state.socket.close(); state.socket = null; }
    state.socketPersonaId = null;
}

function handleSocketMessage(msg) {
    if (!state.page) return;

    bufferTrace(msg);

    if (msg.type === 'chat_message' && msg.content) {
        state.page.appendMessage({
            role: 'them',
            text: msg.content,
            time: formatTime(new Date()),
            trace: takeTrace(),
        });
        state.page.setPending(false);
        return;
    }

    if (msg.title === 'Heard' || msg.title === 'Said') {
        const d = msg.details || {};
        if (d.persona?.id !== state.currentPersonaId) return;
        if (!d.channel || d.channel.type === 'web') return;
        const content = d.content;
        if (!content) return;
        state.page.appendMessage({
            role: msg.title === 'Heard' ? 'me' : 'them',
            text: content,
            time: formatTime(new Date()),
            trace: msg.title === 'Said' ? takeTrace() : undefined,
        });
        if (msg.title === 'Said') state.page.setPending(false);
        return;
    }

    if (msg.title && state.currentTab === 'chat') {
        const d = msg.details || {};
        if (d.persona?.id && d.persona.id !== state.currentPersonaId) return;
        const detail = formatSignalDetail(msg.type, msg.title, d);
        if (detail) state.page.setPending(true, detail);  /* mode unchanged */
    }
}

function bufferTrace(msg) {
    if (msg.type === 'chat_message') return;
    if (typeof msg.title === 'string' && msg.title.includes('stream chunk')) return;
    if (msg.title === 'Persona found') return;
    const d = msg.details || {};
    if (d.persona?.id && d.persona.id !== state.currentPersonaId) return;

    /* Strip the noisy "tools." prefix from CapabilityRun selectors —
       the type column already says it's a tool run. */
    let title = msg.title || '';
    if (msg.type === 'CapabilityRun' && title.startsWith('tools.')) title = title.slice(6);

    const entry = {
        type: msg.type || '',
        title,
        time: formatTime(new Date()),
        detail: extractTraceDetail(msg),
    };
    state.pendingTrace.push(entry);
    state.signalHistory.push(entry);
    if (state.signalHistory.length > 50) state.signalHistory.shift();
    state.page?.setSignals?.(state.signalHistory.slice());
}

function extractTraceDetail(msg) {
    const d = msg.details || {};
    /* CapabilityRun → summarise the call from args + status. */
    if (msg.type === 'CapabilityRun') {
        const args = d.args || {};
        const status = d.status || '';
        if (args.method && args.url) {
            const u = String(args.url).replace(/^https?:\/\//, '').slice(0, 60);
            return `${args.method} ${u}${status === 'error' ? ' · ERROR' : ''}`;
        }
        if (args.path) return `${args.path}${status === 'error' ? ' · ERROR' : ''}`;
        if (args.command) return String(args.command).slice(0, 80);
        if (args.text) return String(args.text).slice(0, 80);
        if (args.intention) return String(args.intention).slice(0, 80);
        if (status) return status;
    }
    if (typeof d.content === 'string') return d.content.slice(0, 100);
    if (d.body?.model) return d.body.model;
    if (d.error) return String(d.error).slice(0, 100);
    return '';
}

function takeTrace() {
    const t = state.pendingTrace;
    state.pendingTrace = [];
    return t;
}

function formatSignalDetail(type, title, _details) {
    if (type === 'Tick' || type === 'Tock') return title;       /* "realize", "recognize", … */
    if (type === 'Plan' || type === 'Event') return title;       /* "Hearing", "Sending Anthropic Request", … */
    if (type === 'Command') return title;
    return null;                                                 /* skip Message stream chunks */
}

/* ── Helpers ─────────────────────────────────────────────────────── */

function formatTime(d) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function mapServerMessage(personaId, m) {
    const text = m.text || m.content || '';
    const image = m.image || (m.media?.source ? mediaUrl(personaId, m.media.source) : null);
    if (!text && !image) return null;
    if ((m.role === 'person' || m.role === 'user') && text.startsWith('TOOL_RESULT')) return null;
    const role = (m.role === 'persona' || m.role === 'assistant') ? 'them' : 'me';
    return {
        role,
        text,
        time: m.time ? formatTime(new Date(m.time)) : '',
        image,
    };
}

/* ── Page mounting ───────────────────────────────────────────────── */

async function showPersona(id, tab = 'chat') {
    const isSamePersona = state.currentPersonaId === id;
    state.currentPersonaId = id;
    state.currentTab = tab;

    let page = state.page;
    const isPersonaPage = page?.tagName?.toLowerCase() === 'persona-page';
    if (!page || !isPersonaPage || !isSamePersona) {
        const app = document.getElementById('app');
        app.innerHTML = '';
        page = document.createElement('persona-page');
        app.appendChild(page);
        state.page = page;

        page.addEventListener('send',     (e) => onSend(id, e.detail));
        page.addEventListener('stop',     () => onStop(id));
        page.addEventListener('poweroff', () => onPowerOff(id));
        page.addEventListener('restart',  () => onRestart(id));
        page.addEventListener('delete',   () => onDelete(id));
        page.addEventListener('sleep',    () => onSleep(id));
        page.addEventListener('refresh-diagnose', () => refreshDiagnose(id));
        page.addEventListener('update-status', (e) => onUpdateStatus(id, e.detail.status));
        page.addEventListener('update-model',  (e) => onUpdateModel(id, e.detail));
        page.addEventListener('clear-model',   (e) => onClearModel(id, e.detail));
        page.addEventListener('pair-channel',  (e) => onPairChannel(id, e.detail.code));
        page.addEventListener('select',   (e) => router.go(`/persona/${id}/${e.detail.id}`));
        page.addEventListener('switch',   (e) => router.go(`/persona/${e.detail.id}`));
        page.addEventListener('add',      () => router.go('/onboarding'));
        page.addEventListener('calendar-navigate', (e) => refreshCalendar(id, e.detail.month));
    }

    if (!state.personas.length) await listPersonas();
    const persona = state.personas.find((p) => p.id === id) || null;
    page.setProps({ persona, personas: state.personas, tab });

    if (!isSamePersona || !isPersonaPage) {
        page.setProps({ messages: [] });
        connectPersonaSocket(id);
        const msgs = (await getConversation(id)).map((m) => mapServerMessage(id, m)).filter(Boolean);
        page.setProps({ messages: msgs });
        refreshKnowledge(id);  /* load once; menu builds itself from this */
    }

    if (tab === 'status') refreshDiagnose(id);
    if (tab === 'calendar') refreshCalendar(id);
}

async function showOnboarding(step = 'cold') {
    disconnectSocket();
    state.currentPersonaId = null;

    if (!state.personas.length) await listPersonas();

    let page = state.page;
    const isOnboardingPage = page?.tagName?.toLowerCase() === 'onboarding-page';
    if (!page || !isOnboardingPage) {
        const app = document.getElementById('app');
        app.innerHTML = '';
        page = document.createElement('onboarding-page');
        app.appendChild(page);
        state.page = page;

        page.addEventListener('choose', (e) => {
            if (e.detail.what === 'create') router.go('/onboarding/create');
            else if (e.detail.what === 'migrate') router.go('/onboarding/migrate');
        });
        page.addEventListener('back',   () => router.go('/onboarding'));
        page.addEventListener('cancel', () => {
            if (state.personas[0]) router.go(`/persona/${state.personas[0].id}`);
            else router.go('/');
        });
        page.addEventListener('submit', (e) => onCreateSubmit(e.detail));
        page.addEventListener('submit-migrate', (e) => onMigrateSubmit(e.detail));
    }
    page.setProps({ step, hasPersonas: state.personas.length > 0 });
}

async function refreshDiagnose(id) {
    const d = await getDiagnose(id);
    if (state.currentPersonaId === id) state.page?.setProps({ diagnose: d });
}

async function refreshKnowledge(id) {
    const k = await getKnowledge(id);
    if (state.currentPersonaId === id) state.page?.setProps({ knowledge: k });
}

async function refreshCalendar(id, monthStr) {
    const c = await getCalendar(id, monthStr);
    if (state.currentPersonaId === id) state.page?.setProps({ calendar: c });
}

async function onSend(id, { text, file }) {
    const time = formatTime(new Date());
    if (file) {
        state.page.appendMessage({
            role: 'me',
            text: text || '',
            time,
            image: URL.createObjectURL(file),
        });
        state.page.setPending(true, '', 'replying');
        const result = await seePersona(id, file, text);
        if (!result.ok) {
            state.page.setPending(false);
            state.page.appendMessage({ role: 'system', text: `Send failed: ${result.error}` });
        }
    } else if (text && text.trim()) {
        state.page.appendMessage({ role: 'me', text, time });
        state.page.setPending(true, '', 'replying');
        const result = await hearPersona(id, text);
        if (!result.ok) {
            state.page.setPending(false);
            state.page.appendMessage({ role: 'system', text: `Send failed: ${result.error}` });
        }
    }
}

async function onStop(id) {
    await hearPersona(id, 'stop');
}

async function onPowerOff(id) {
    if (!confirm('Turn her off? She goes silent until you wake her.')) return;
    const result = await stopPersona(id);
    if (!result.ok) alert(`Could not stop: ${result.error}`);
}

async function onSleep(id) {
    if (!confirm("Send her to sleep? She'll reflect on today and archive what's worth keeping.")) return;
    const result = await sleepPersona(id);
    if (!result.ok) alert(`Could not sleep: ${result.error}`);
}

async function onRestart(id) {
    if (!confirm('Restart her? Her working memory resets but her files stay.')) return;
    const result = await restartPersona(id);
    if (!result.ok) alert(`Could not restart: ${result.error}`);
}

async function onDelete(id) {
    const persona = state.personas.find(p => p.id === id);
    const name = persona?.name || 'this persona';
    if (!confirm(`Delete ${name} permanently? Her files, memory, and conversation will be gone. This can't be undone.`)) return;
    const result = await deletePersona(id);
    if (!result.ok) { alert(`Could not delete: ${result.error}`); return; }
    state.page = null;
    disconnectSocket();
    await listPersonas();
    router.go('/');
}

async function onUpdateStatus(id, status) {
    const result = await updatePersona(id, { status });
    if (!result.ok) { alert(`Could not change status: ${result.error}`); return; }
    /* Re-fetch persona so the new status reflects everywhere. */
    await listPersonas();
    const persona = state.personas.find(p => p.id === id) || null;
    state.page?.setProps?.({ persona, personas: state.personas });
}

async function onUpdateModel(id, { slot, config }) {
    const result = await updatePersona(id, { [slot]: config });
    state.page?.showSaveResult?.(slot, result.ok, result.error);
    if (result.ok) {
        await listPersonas();
        const persona = state.personas.find(p => p.id === id) || null;
        state.page?.setProps?.({ persona, personas: state.personas });
    }
}

async function onClearModel(id, { slot }) {
    if (slot === 'thinking') { alert('Thinking is required — cannot remove.'); return; }
    if (!confirm(`Remove ${slot}?`)) return;
    const body = slot === 'vision' ? { clear_vision: true } : { clear_frontier: true };
    const result = await updatePersona(id, body);
    if (!result.ok) { alert(`Could not remove: ${result.error}`); return; }
    await listPersonas();
    const persona = state.personas.find(p => p.id === id) || null;
    state.page?.setProps?.({ persona, personas: state.personas });
}

async function onPairChannel(id, code) {
    const result = await pairChannel(id, code);
    state.page?.showPairResult?.(result.ok, result.error);
    if (result.ok) {
        await listPersonas();
        const persona = state.personas.find(p => p.id === id) || null;
        state.page?.setProps?.({ persona, personas: state.personas });
    }
}

async function onCreateSubmit(fields) {
    const result = await createPersona(fields);
    if (!result.ok) {
        state.page?.setError?.(result.error || 'Could not create persona.');
        return;
    }
    await listPersonas();
    router.go(`/persona/${result.id}`);
}

async function onMigrateSubmit(formData) {
    const result = await migratePersona(formData);
    if (!result.ok) {
        state.page?.setError?.(result.error || 'Could not migrate persona.');
        return;
    }
    await listPersonas();
    router.go(`/persona/${result.id}`);
}

/* ── Router ──────────────────────────────────────────────────────── */

const router = new Router();
router.add('/persona/{id}/{tab}/{sub}', ({ id, tab, sub }) => showPersona(id, `${tab}/${sub}`));
router.add('/persona/{id}/{tab}',  ({ id, tab }) => showPersona(id, tab));
router.add('/persona/{id}',        ({ id })      => showPersona(id, 'chat'));
router.add('/onboarding/create',   () => showOnboarding('create'));
router.add('/onboarding/migrate',  () => showOnboarding('migrate'));
router.add('/onboarding',          () => showOnboarding('cold'));
router.add('/', async () => {
    if (!state.personas.length) await listPersonas();
    if (state.personas.length === 0) router.go('/onboarding');
    else router.go(`/persona/${state.personas[0].id}`);
});
router.fallback(() => router.go('/'));

/* ── Boot ────────────────────────────────────────────────────────── */

(async () => {
    await listPersonas();
    router.match();
})();
