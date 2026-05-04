import { Router } from './platform/router.js';
import { Socket } from './platform/socket.js';
import { get, post, download } from './platform/network.js';
import './business/frame.js';

let personas = [];
let currentPersonaId = null;
let personaSocket = null;
let connectedPersonaId = null;
let systemSocket = null;
const signals = new EventTarget();
const chatListeners = [];

async function listPersonas() {
    try {
        const data = await get('/api/personas');
        personas = data.personas || [];
        return personas;
    } catch { return []; }
}

async function getPersona(id) {
    if (!personas.length) await listPersonas();
    return personas.find((p) => p.id === id) || null;
}

async function getConversation(id) {
    try {
        const data = await get(`/api/persona/${id}/conversation`);
        return data.messages || [];
    } catch { return []; }
}

async function getDiagnose(id) {
    try { return await get(`/api/persona/${id}/diagnose`); }
    catch { return null; }
}

async function getOversee(id) {
    try { return await get(`/api/persona/${id}/oversee`); }
    catch { return null; }
}

async function updatePersona(id, fields) {
    try { return { success: true, ...(await post(`/api/persona/${id}/update`, fields)) }; }
    catch (e) { return { success: false, error: e.message }; }
}

async function deletePersona(id) {
    try {
        await post(`/api/persona/${id}/delete`);
        await listPersonas();
        router.go('/');
        return { success: true };
    } catch (e) { return { success: false, error: e.message }; }
}

async function startPersona(id)   { try { await post(`/api/persona/${id}/start`);   return { success: true }; } catch (e) { return { success: false, error: e.message }; } }
async function stopPersona(id)    { try { await post(`/api/persona/${id}/stop`);    return { success: true }; } catch (e) { return { success: false, error: e.message }; } }
async function restartPersona(id) { try { await post(`/api/persona/${id}/restart`); return { success: true }; } catch (e) { return { success: false, error: e.message }; } }
async function sleepPersona(id)   { try { await post(`/api/persona/${id}/sleep`);   return { success: true }; } catch (e) { return { success: false, error: e.message }; } }

async function controlPersona(id, entryIds) {
    try { await post(`/api/persona/${id}/control`, { entry_ids: entryIds }); return { success: true }; }
    catch (e) { return { success: false, error: e.message }; }
}

async function hearPersona(id, message) {
    try { await post(`/api/persona/${id}/hear`, { message }); return { success: true }; }
    catch (e) { return { success: false, error: e.message }; }
}

async function seePersona(id, file, caption) {
    const form = new FormData();
    form.append('image', file);
    if (caption) form.append('caption', caption);
    try { await post(`/api/persona/${id}/see`, form); return { success: true }; }
    catch (e) { return { success: false, error: e.message }; }
}

async function feedPersona(id, file, source) {
    const form = new FormData();
    form.append('history', file);
    form.append('source', source);
    try {
        const data = await post(`/api/persona/${id}/feed`, form);
        return { success: true, message: data?.message };
    } catch (e) { return { success: false, error: e.message }; }
}

async function exportPersona(id) {
    try { await download(`/api/persona/${id}/export`, `${id}.diary`); return { success: true }; }
    catch (e) { return { success: false, error: e.message }; }
}

async function pairChannel(code, personaId) {
    try { await post(`/api/persona/${personaId}/pair`, { code }); return { success: true }; }
    catch (e) { return { success: false, error: e.message }; }
}

async function getProviderConfig() {
    try { return await get('/api/config/providers'); }
    catch {
        return {
            local: { url: 'http://localhost:11434' },
            anthropic: { url: 'https://api.anthropic.com' },
            openai: { url: 'https://api.openai.com' },
        };
    }
}

async function createPersona(data) {
    try {
        const result = await post('/api/persona/create', data);
        return { success: true, persona_id: result.persona?.id, ...result };
    } catch (e) { return { success: false, error: e.message }; }
}

async function migratePersona(formData) {
    try {
        const result = await post('/api/persona/migrate', formData);
        return { success: true, persona_id: result.persona?.id, ...result };
    } catch (e) { return { success: false, error: e.message }; }
}

function mediaUrl(id, source) {
    const base = (source || '').split('/').pop();
    return `/api/persona/${id}/media/${encodeURIComponent(base)}`;
}

function connectPersona(id) {
    if (connectedPersonaId === id) return;
    if (personaSocket) personaSocket.close();
    connectedPersonaId = id;
    personaSocket = new Socket(`/ws/${id}`);
    personaSocket.on(handleMessage);
    personaSocket.open();
}

function disconnectPersona() {
    connectedPersonaId = null;
    if (personaSocket) {
        personaSocket.close();
        personaSocket = null;
    }
}

function handleMessage(msg) {
    if (msg.type === 'chat_message') {
        for (const fn of chatListeners) fn(msg);
    } else if (msg.title) {
        signals.dispatchEvent(new CustomEvent('signal', { detail: msg }));
    }
}

function onChat(fn) { chatListeners.push(fn); }
function offChat(fn) {
    const i = chatListeners.indexOf(fn);
    if (i >= 0) chatListeners.splice(i, 1);
}

const router = new Router();

router.add('/setup', () => showWorld('chooser', {}));
router.add('/setup/create', () => showWorld('create', {}));
router.add('/setup/migrate', () => showWorld('migrate', {}));
router.add('/persona/{id}/inner', ({ id }) => showWorld('inner', { id }));
router.add('/persona/{id}/status', ({ id }) => showWorld('status', { id }));
router.add('/persona/{id}', ({ id }) => showWorld('outer', { id }));
router.add('/', () => {
    if (personas.length === 0) router.go('/setup');
    else showWorld('outer', { id: personas[0].id });
});
router.fallback(() => router.go('/'));

const frame = document.createElement('app-frame');
document.getElementById('app').appendChild(frame);
frame.init({ api: api(), signals });

function showWorld(worldName, params) {
    if (params.id) currentPersonaId = params.id;
    if (worldName === 'outer' || worldName === 'inner' || worldName === 'status') {
        if (params.id) connectPersona(params.id);
    } else {
        disconnectPersona();
    }
    frame.show(worldName, params);
}

function api() {
    return {
        listPersonas, getPersona, getConversation, getDiagnose, getOversee,
        updatePersona, deletePersona,
        startPersona, stopPersona, restartPersona, sleepPersona,
        controlPersona, hearPersona, seePersona, feedPersona,
        exportPersona, pairChannel, getProviderConfig,
        createPersona, migratePersona, mediaUrl,
        connectPersona, disconnectPersona, onChat, offChat,
        goToOuter:   (id) => router.go(`/persona/${id}`),
        goToInner:   (id) => router.go(`/persona/${id}/inner`),
        goToStatus:  (id) => router.go(`/persona/${id}/status`),
        goToSetup:   () => router.go('/setup'),
        goToCreate:  () => router.go('/setup/create'),
        goToMigrate: () => router.go('/setup/migrate'),
        goToHome:    () => router.go('/'),
    };
}

(async () => {
    systemSocket = new Socket('/ws/system');
    systemSocket.on(handleMessage);
    systemSocket.open();

    await listPersonas();
    router.match();
})();
