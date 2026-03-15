import Layout from './layout.js';

class TailLayout extends Layout {
    // init({ }) — no props needed, children added externally
    arrange() {
        this._pinned = true;

        this.addEventListener('scroll', () => {
            const gap = this.scrollHeight - this.scrollTop - this.clientHeight;
            this._pinned = gap < 24;
        });

        this._observer = new MutationObserver(() => {
            if (this._pinned) this.scrollTop = this.scrollHeight;
        });
        this._observer.observe(this, { childList: true, subtree: true, characterData: true });
    }

    disconnectedCallback() {
        this._observer?.disconnect();
    }

    append(element) {
        this.appendChild(element);
    }
}

customElements.define('tail-layout', TailLayout);
export default TailLayout;
