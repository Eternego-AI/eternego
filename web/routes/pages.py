"""Pages — server-rendered HTML routes."""

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from application.business import persona

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    outcome = await persona.agents()
    personas_list = (outcome.data or {}).get("personas", []) if outcome.success else []
    personas_json = json.dumps([
        {"id": p.id, "name": p.name, "model": p.model.name}
        for p in personas_list
    ])
    return _TEMPLATE.replace("__PERSONAS__", personas_json)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eternego</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #07070c;
      --surface:   #0c0c15;
      --surface-2: #111120;
      --border:    #16162a;
      --border-2:  #20203a;

      --text-1:    #dcdcf0;
      --text-2:    #7878a0;
      --text-3:    #363655;

      --violet:    #7c5cbf;
      --active:    #2ed47f;
      --thinking:  #e8973a;
      --idle:      #252540;

      --c-plan:    #4a8aff;
      --c-event:   #2ed47f;
      --c-message: #9b72ef;
      --c-inquiry: #e8973a;
      --c-command: #ef5454;

      --mono: "SF Mono","Fira Code","Cascadia Code","Consolas",monospace;
      --r: 10px;
    }

    html, body {
      height: 100%;
      background: var(--bg);
      color: var(--text-1);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }

    /* ── Layout ──────────────────────────────────────────── */

    .shell {
      display: grid;
      grid-template-rows: 56px 1fr;
      height: 100vh;
      max-width: 1280px;
      margin: 0 auto;
      padding: 0 28px;
    }

    /* ── Header ──────────────────────────────────────────── */

    header {
      display: flex;
      align-items: center;
      gap: 16px;
      border-bottom: 1px solid var(--border);
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 9px;
    }

    .logo-gem {
      width: 26px;
      height: 26px;
      background: linear-gradient(145deg, #9f7fe0, #5a3da0);
      border-radius: 7px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      flex-shrink: 0;
      box-shadow: 0 0 18px rgba(124,92,191,.35);
    }

    .logo-name {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .2em;
      text-transform: uppercase;
      color: var(--text-1);
    }

    .logo-sub {
      font-size: 11px;
      color: var(--text-3);
      font-style: italic;
      letter-spacing: .04em;
      flex: 1;
    }

    .ws-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 10px;
      font-family: var(--mono);
      color: var(--text-3);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 100px;
      padding: 3px 10px 3px 8px;
      transition: color .3s, border-color .3s;
    }

    .ws-dot {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--text-3);
      transition: background .3s;
    }

    .ws-badge.live { color: var(--active); border-color: rgba(46,212,127,.25); }
    .ws-badge.live .ws-dot { background: var(--active); animation: blink 2s ease infinite; }
    .ws-badge.dead { color: var(--c-command); border-color: rgba(239,84,84,.2); }
    .ws-badge.dead .ws-dot { background: var(--c-command); }

    /* ── Main grid ───────────────────────────────────────── */

    main {
      display: grid;
      grid-template-rows: auto 1fr;
      overflow: hidden;
      padding: 24px 0 20px;
      gap: 24px;
    }

    .row-head {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
    }

    .row-label {
      font-size: 9.5px;
      font-weight: 700;
      letter-spacing: .22em;
      text-transform: uppercase;
      color: var(--text-3);
      white-space: nowrap;
    }

    .row-rule {
      flex: 1;
      height: 1px;
      background: var(--border);
    }

    /* ── Persona cards ───────────────────────────────────── */

    .personas-wrap { overflow: hidden; }

    .personas-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: 14px;
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 18px 18px 16px;
      transition: border-color .3s, box-shadow .3s, transform .2s;
      position: relative;
    }

    .card:hover { transform: translateY(-2px); border-color: var(--border-2); }

    .card.active {
      border-color: rgba(46,212,127,.3);
      box-shadow: 0 0 0 1px rgba(46,212,127,.08), 0 8px 28px rgba(46,212,127,.06);
    }

    .card.thinking {
      border-color: rgba(232,151,58,.3);
      box-shadow: 0 0 0 1px rgba(232,151,58,.08), 0 8px 28px rgba(232,151,58,.06);
    }

    .card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }

    .status-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 10px;
      font-family: var(--mono);
      color: var(--text-3);
      transition: color .3s;
    }

    .status-orb {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--idle);
      transition: background .3s;
    }

    .card.active   .status-orb { background: var(--active); }
    .card.active   .status-pill { color: var(--active); }
    .card.thinking .status-orb { background: var(--thinking); animation: pulse-orb 1.2s ease-out infinite; }
    .card.thinking .status-pill { color: var(--thinking); }

    .card-name {
      font-size: 1.2rem;
      font-weight: 600;
      letter-spacing: -.015em;
      color: var(--text-1);
      margin-bottom: 14px;
    }

    .card-sep {
      height: 1px;
      background: var(--border);
      margin-bottom: 12px;
    }

    .card-foot {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .card-model {
      font-size: 10.5px;
      font-family: var(--mono);
      color: var(--text-2);
    }

    .card-id {
      font-size: 9.5px;
      font-family: var(--mono);
      color: var(--text-3);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .no-personas {
      grid-column: 1/-1;
      padding: 36px;
      text-align: center;
      color: var(--text-3);
      font-size: 12px;
      border: 1px dashed var(--border-2);
      border-radius: var(--r);
    }

    /* ── Signal feed ─────────────────────────────────────── */

    .feed-wrap {
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 0;
    }

    .feed {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      overflow-y: auto;
      min-height: 0;
    }

    .feed::-webkit-scrollbar { width: 3px; }
    .feed::-webkit-scrollbar-track { background: transparent; }
    .feed::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 2px; }

    .feed-empty {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100px;
      color: var(--text-3);
      font-size: 11px;
      font-family: var(--mono);
    }

    .sig {
      display: grid;
      grid-template-columns: 64px 76px 1fr auto;
      align-items: center;
      gap: 14px;
      padding: 7px 16px;
      border-bottom: 1px solid var(--border);
      animation: drop-in .12s ease-out both;
    }

    .sig:last-child { border-bottom: none; }
    .sig:hover { background: var(--surface-2); }

    .sig-time {
      font-family: var(--mono);
      font-size: 10px;
      color: var(--text-3);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 2px 9px;
      border-radius: 100px;
      font-size: 9.5px;
      font-weight: 600;
      font-family: var(--mono);
      letter-spacing: .04em;
    }

    .badge-Plan    { background: rgba(74,138,255,.12); color: var(--c-plan);    }
    .badge-Event   { background: rgba(46,212,127,.12); color: var(--c-event);   }
    .badge-Message { background: rgba(155,114,239,.12); color: var(--c-message);}
    .badge-Inquiry { background: rgba(232,151,58,.12);  color: var(--c-inquiry);}
    .badge-Command { background: rgba(239,84,84,.12);   color: var(--c-command);}

    .sig-title {
      font-size: 12px;
      color: var(--text-2);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .sig-who {
      font-size: 10px;
      font-family: var(--mono);
      color: var(--text-3);
      white-space: nowrap;
    }

    /* ── Animations ──────────────────────────────────────── */

    @keyframes blink {
      0%,100% { opacity: 1; }
      50%      { opacity: .3; }
    }

    @keyframes pulse-orb {
      0%   { box-shadow: 0 0 0 0 rgba(232,151,58,.6); }
      70%  { box-shadow: 0 0 0 7px transparent; }
      100% { box-shadow: 0 0 0 0 transparent; }
    }

    @keyframes drop-in {
      from { opacity: 0; transform: translateY(-3px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>
<div class="shell">

  <header>
    <div class="logo">
      <div class="logo-gem">◈</div>
      <span class="logo-name">Eternego</span>
    </div>
    <span class="logo-sub">the eternal i</span>
    <div class="ws-badge" id="ws">
      <span class="ws-dot"></span>
      <span id="ws-label">connecting</span>
    </div>
  </header>

  <main>
    <div class="personas-wrap">
      <div class="row-head">
        <span class="row-label">Personas</span>
        <div class="row-rule"></div>
      </div>
      <div class="personas-grid" id="grid"></div>
    </div>

    <div class="feed-wrap">
      <div class="row-head">
        <span class="row-label">Live Signals</span>
        <div class="row-rule"></div>
      </div>
      <div class="feed" id="feed">
        <div class="feed-empty" id="feed-empty">waiting for signals…</div>
      </div>
    </div>
  </main>

</div>
<script>
  const PERSONAS = __PERSONAS__;
  const MAX_SIGS = 200;

  // ── Persona cards ───────────────────────────────────────

  const timers = {};

  function applyStatus(id, state) {
    clearTimeout(timers[id]);
    if (state !== 'idle') {
      timers[id] = setTimeout(() => applyStatus(id, 'idle'), 30_000);
    }
    const card = document.getElementById('c-' + id);
    if (!card) return;
    card.className = 'card ' + state;
    const labels = { idle: 'idle', active: 'listening', thinking: 'thinking…' };
    card.querySelector('.status-label').textContent = labels[state] || state;
  }

  function renderGrid() {
    const grid = document.getElementById('grid');
    if (!PERSONAS.length) {
      grid.innerHTML = '<div class="no-personas">No personas yet. Create one to get started.</div>';
      return;
    }
    grid.innerHTML = PERSONAS.map(p => `
      <div class="card idle" id="c-${p.id}">
        <div class="card-top">
          <div class="status-pill">
            <span class="status-orb"></span>
            <span class="status-label">idle</span>
          </div>
        </div>
        <div class="card-name">${p.name}</div>
        <div class="card-sep"></div>
        <div class="card-foot">
          <span class="card-model">${p.model}</span>
          <span class="card-id" title="${p.id}">${p.id}</span>
        </div>
      </div>
    `).join('');
  }

  // ── Signal feed ─────────────────────────────────────────

  function addSignal(sig) {
    const feed  = document.getElementById('feed');
    const empty = document.getElementById('feed-empty');
    if (empty) empty.remove();

    const personaId   = sig.details?.persona?.id   || '';
    const personaName = sig.details?.persona?.name || '';

    if (personaId) {
      if (sig.type === 'Plan')  applyStatus(personaId, 'thinking');
      if (sig.type === 'Event') applyStatus(personaId, 'active');
    }

    const t = new Date();
    const ts = [t.getHours(), t.getMinutes(), t.getSeconds()]
      .map(n => String(n).padStart(2, '0')).join(':');

    const row = document.createElement('div');
    row.className = 'sig';
    row.innerHTML =
      `<span class="sig-time">${ts}</span>` +
      `<span class="badge badge-${sig.type}">${sig.type}</span>` +
      `<span class="sig-title">${sig.title}</span>` +
      `<span class="sig-who">${personaName}</span>`;

    feed.prepend(row);

    const rows = feed.querySelectorAll('.sig');
    if (rows.length > MAX_SIGS) rows[rows.length - 1].remove();
  }

  // ── WebSocket ───────────────────────────────────────────

  function connect() {
    const ws  = new WebSocket(`ws://${location.host}/ws`);
    const bag = document.getElementById('ws');
    const lbl = document.getElementById('ws-label');

    ws.onopen    = () => { bag.className = 'ws-badge live'; lbl.textContent = 'live'; };
    ws.onclose   = () => { bag.className = 'ws-badge dead'; lbl.textContent = 'reconnecting…'; setTimeout(connect, 3000); };
    ws.onerror   = () => ws.close();
    ws.onmessage = e  => { try { addSignal(JSON.parse(e.data)); } catch {} };
  }

  renderGrid();
  connect();
</script>
</body>
</html>"""
