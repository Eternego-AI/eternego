/* <pending-row> — live activity indicator.
   Two modes via setProps({ mode }):
     'replying' — she's working on a reply to your last message. Shows STOP.
     'active'   — she's living on her own. No STOP, dimmer style.
   Emits 'stop' (only meaningful in 'replying' mode). */

class PendingRow extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._start = Date.now();
        this._mode = 'active';
        this.innerHTML = `
            <breath-dot state="thinking"></breath-dot>
            <span class="el-detail">…</span>
            <span class="el-elapsed">00s</span>
            <button class="el-stop" type="button">STOP</button>
        `;
        this._detail = this.querySelector('.el-detail');
        this._elapsed = this.querySelector('.el-elapsed');
        this._stop = this.querySelector('.el-stop');
        this._stop.onclick = () => this.dispatchEvent(new CustomEvent('stop'));
        this._applyMode();
        this._tick();
        this._timer = setInterval(() => this._tick(), 1000);
    }
    disconnectedCallback() {
        if (this._timer) clearInterval(this._timer);
    }
    _tick() {
        const s = Math.floor((Date.now() - this._start) / 1000);
        const mm = Math.floor(s / 60);
        const ss = s % 60;
        this._elapsed.textContent = mm > 0
            ? `${mm}m ${String(ss).padStart(2, '0')}s`
            : `${String(ss).padStart(2, '0')}s`;
    }
    _applyMode() {
        this.setAttribute('mode', this._mode);
        this._stop.hidden = this._mode !== 'replying';
    }
    setProps({ detail, mode }) {
        if (detail !== undefined && detail !== '') this._detail.textContent = detail;
        if (mode !== undefined && mode !== this._mode) {
            this._mode = mode;
            this._applyMode();
        }
    }
}
customElements.define('pending-row', PendingRow);
