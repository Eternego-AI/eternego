/* <calendar-view> — month grid view of her past and scheduled events.
   setProps({ persona, calendar }). calendar = { date, history, destiny }
   where history/destiny are dicts of subtype → list of events.

   Each event in a day cell renders as a small colored dot. Click a dot to
   reveal a popover with its body. Today's cell is outlined.
   Emits 'navigate' { date: 'YYYY-MM' } when the month changes. */

import { toHTML } from '../platform/markdown.js';
import { escapeHtml } from '../platform/escape.js';

const SUBTYPE_COLOR = {
    'history.conversation': 'var(--accent)',
    'history.schedule':     '#6f9adc',
    'history.reminder':     '#d0a14a',
    'destiny.schedule':     '#5fa67a',
    'destiny.reminder':     '#c97b5f',
};

const SUBTYPE_LABEL = {
    'history.conversation': 'conversation',
    'history.schedule':     'past schedule',
    'history.reminder':     'reminder fired',
    'destiny.schedule':     'scheduled',
    'destiny.reminder':     'upcoming reminder',
};

class CalendarView extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._data = null;
        this._openEvent = null;
        this._popoverEl = null;
        this.render();
        document.addEventListener('click', this._onDocClick);
        document.addEventListener('keydown', this._onKey);
    }
    disconnectedCallback() {
        document.removeEventListener('click', this._onDocClick);
        document.removeEventListener('keydown', this._onKey);
    }
    setProps({ calendar }) {
        if (calendar !== undefined) {
            this._data = calendar;
            this._openEvent = null;
        }
        this.render();
    }

    _onDocClick = (e) => {
        if (!this._openEvent) return;
        if (this._popoverEl && (this._popoverEl.contains(e.target) || e.target.classList?.contains('w-cal-dot'))) return;
        this._openEvent = null;
        this.render();
    };
    _onKey = (e) => {
        if (e.key === 'Escape' && this._openEvent) {
            this._openEvent = null;
            this.render();
        }
    };

    render() {
        const d = this._data;
        if (!d) {
            this.innerHTML = `<div class="w-calendar"><p class="w-cal-loading">loading…</p></div>`;
            return;
        }
        const monthStr = d.month || todayMonth();
        const [year, month] = monthStr.split('-').map(Number);
        const monthLabel = formatMonth(monthStr);
        const cells = buildGrid(year, month);
        const eventMap = groupEventsByDate(d.history || {}, d.destiny || {});
        const todayKey = todayDate();

        this.innerHTML = `
            <div class="w-calendar">
                <div class="w-cal-head">
                    <h2 class="w-cal-h">Calendar</h2>
                    <p class="w-cal-sub">What she's done and what she's scheduled. Click a dot to see the entry.</p>
                </div>
                <div class="w-cal-nav">
                    <button class="w-cal-nav-btn" data-act="prev" type="button">←</button>
                    <span class="w-cal-month">${escapeHtml(monthLabel)}</span>
                    <button class="w-cal-nav-btn" data-act="next" type="button">→</button>
                    <button class="w-cal-today" data-act="today" type="button">today</button>
                </div>
                <div class="w-cal-grid">
                    <div class="w-cal-wk">Mon</div>
                    <div class="w-cal-wk">Tue</div>
                    <div class="w-cal-wk">Wed</div>
                    <div class="w-cal-wk">Thu</div>
                    <div class="w-cal-wk">Fri</div>
                    <div class="w-cal-wk">Sat</div>
                    <div class="w-cal-wk">Sun</div>
                    ${cells.map(c => this._renderCell(c, eventMap, todayKey)).join('')}
                </div>
                <div class="w-cal-legend">
                    ${Object.entries(SUBTYPE_LABEL).map(([k, label]) => `
                        <span class="w-cal-legend-item">
                            <span class="w-cal-dot-key" style="background:${SUBTYPE_COLOR[k]}"></span>
                            ${escapeHtml(label)}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;

        for (const btn of this.querySelectorAll('.w-cal-nav-btn, .w-cal-today')) {
            btn.onclick = (e) => {
                e.stopPropagation();
                if (btn.dataset.act === 'today') {
                    this.dispatchEvent(new CustomEvent('navigate', { detail: { month: todayMonth() } }));
                } else {
                    const next = stepMonth(monthStr, btn.dataset.act === 'next' ? 1 : -1);
                    this.dispatchEvent(new CustomEvent('navigate', { detail: { month: next } }));
                }
            };
        }
        for (const dot of this.querySelectorAll('.w-cal-dot')) {
            dot.onclick = (e) => {
                e.stopPropagation();
                const id = dot.dataset.id;
                this._openEvent = id;
                this.render();
            };
        }

        if (this._openEvent) {
            const event = this._findEvent(this._openEvent, eventMap);
            if (event) this._renderPopover(event);
        }
    }

    _renderCell(cell, eventMap, todayKey) {
        const dateKey = dateKeyOf(cell.date);
        const events = eventMap[dateKey] || [];
        const day = cell.date.getDate();
        const classes = ['w-cal-cell'];
        if (cell.outside) classes.push('is-outside');
        if (dateKey === todayKey) classes.push('is-today');
        const max = 6;
        const visible = events.slice(0, max);
        const overflow = events.length - visible.length;

        return `
            <div class="${classes.join(' ')}" data-date="${dateKey}">
                <span class="w-cal-day">${day}</span>
                <div class="w-cal-dots">
                    ${visible.map((e, i) => `
                        <span class="w-cal-dot" data-id="${dateKey}__${i}"
                              title="${escapeHtml(SUBTYPE_LABEL[`${e.type}.${e.subtype}`] || '')}"
                              style="background:${SUBTYPE_COLOR[`${e.type}.${e.subtype}`] || 'var(--text-muted)'}"></span>
                    `).join('')}
                    ${overflow > 0 ? `<span class="w-cal-overflow">+${overflow}</span>` : ''}
                </div>
            </div>
        `;
    }

    _findEvent(id, eventMap) {
        const [dateKey, idxStr] = id.split('__');
        return (eventMap[dateKey] || [])[Number(idxStr)];
    }

    _renderPopover(event) {
        if (this._popoverEl) this._popoverEl.remove();
        const pop = document.createElement('div');
        pop.className = 'w-cal-popover';
        const k = `${event.type}.${event.subtype}`;
        const t = new Date(event.time);
        const when = isNaN(t) ? event.time : t.toLocaleString();
        pop.innerHTML = `
            <header class="w-cal-popover-h">
                <span class="w-cal-popover-tag" style="background:${SUBTYPE_COLOR[k] || 'var(--text-muted)'}"></span>
                <span class="w-cal-popover-label">${escapeHtml(SUBTYPE_LABEL[k] || k)}</span>
                <span class="w-cal-popover-when">${escapeHtml(when)}</span>
                ${event.recurrence ? `<span class="w-cal-popover-rec">↻ ${escapeHtml(event.recurrence)}</span>` : ''}
                <button class="w-cal-popover-close" type="button" aria-label="close">×</button>
            </header>
            <div class="w-cal-popover-body">${toHTML(event.body || '')}</div>
        `;
        this.appendChild(pop);
        this._popoverEl = pop;

        pop.querySelector('.w-cal-popover-close').onclick = (e) => {
            e.stopPropagation();
            this._openEvent = null;
            this.render();
        };

        // Anchor the popover near the clicked dot.
        const dot = this.querySelector(`.w-cal-dot[data-id="${cssEscape(this._openEvent)}"]`);
        if (dot) {
            const dotRect = dot.getBoundingClientRect();
            const hostRect = this.getBoundingClientRect();
            pop.style.left = `${Math.max(8, dotRect.left - hostRect.left - 120)}px`;
            pop.style.top  = `${dotRect.bottom - hostRect.top + 6}px`;
        }
    }
}

function todayMonth() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}
function todayDate() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function dateKeyOf(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function buildGrid(year, month) {
    const firstOfMonth = new Date(year, month - 1, 1);
    const firstWeekday = (firstOfMonth.getDay() + 6) % 7; // Monday=0
    const daysInMonth = new Date(year, month, 0).getDate();

    const cells = [];
    const prevMonth = month === 1 ? 12 : month - 1;
    const prevYear  = month === 1 ? year - 1 : year;
    const daysInPrev = new Date(prevYear, prevMonth, 0).getDate();
    for (let i = firstWeekday - 1; i >= 0; i--) {
        cells.push({ date: new Date(prevYear, prevMonth - 1, daysInPrev - i), outside: true });
    }
    for (let d = 1; d <= daysInMonth; d++) {
        cells.push({ date: new Date(year, month - 1, d), outside: false });
    }
    const nextMonth = month === 12 ? 1 : month + 1;
    const nextYear  = month === 12 ? year + 1 : year;
    let nextDay = 1;
    while (cells.length < 42) {
        cells.push({ date: new Date(nextYear, nextMonth - 1, nextDay++), outside: true });
    }
    return cells;
}

function groupEventsByDate(history, destiny) {
    const map = {};
    for (const [subtype, events] of Object.entries(history)) {
        for (const e of events) {
            const dateKey = String(e.time).slice(0, 10);
            (map[dateKey] = map[dateKey] || []).push({ type: 'history', subtype, ...e });
        }
    }
    for (const [subtype, events] of Object.entries(destiny)) {
        for (const e of events) {
            const dateKey = String(e.time).slice(0, 10);
            (map[dateKey] = map[dateKey] || []).push({ type: 'destiny', subtype, ...e });
        }
    }
    for (const list of Object.values(map)) {
        list.sort((a, b) => a.time.localeCompare(b.time));
    }
    return map;
}

function formatMonth(ym) {
    const [y, m] = (ym || '').split('-').map(Number);
    if (!y || !m) return ym || '';
    const names = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    return `${names[m - 1]} ${y}`;
}
function stepMonth(ym, delta) {
    const [y, m] = ym.split('-').map(Number);
    let ny = y, nm = m + delta;
    if (nm > 12) { ny++; nm = 1; }
    if (nm < 1) { ny--; nm = 12; }
    return `${String(ny).padStart(4, '0')}-${String(nm).padStart(2, '0')}`;
}
function cssEscape(s) {
    return String(s).replace(/"/g, '\\"');
}

customElements.define('calendar-view', CalendarView);
