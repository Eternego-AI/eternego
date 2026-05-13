/* <onboarding-cold> — the cold-start chooser.
   Emits 'create' and 'migrate' when the cards are clicked. */

class OnboardingCold extends HTMLElement {
    connectedCallback() {
        if (this._built) return;
        this._built = true;
        this._hasPersonas = false;
        this.render();
    }
    setProps({ hasPersonas }) {
        this._hasPersonas = !!hasPersonas;
        this.render();
    }
    render() {
        this.innerHTML = `
            <div class="w-cold">
                <div class="w-cold-top">
                    <div class="w-cold-brand">eternego</div>
                    ${this._hasPersonas ? `<button class="w-cold-cancel" type="button">← back to personas</button>` : ''}
                </div>
                <h1 class="w-cold-greet">
                    <em>someone</em> new.
                    <span class="w-cold-sub">
                        wake another persona on your machine. she'll live alongside the ones you already have.
                        you decide who.
                    </span>
                </h1>

                <div class="w-cold-cards">
                    <button class="w-cold-card is-primary" data-act="create">
                        <div class="w-cold-card-h">
                            <span class="w-cold-card-t">Create</span>
                            <span class="w-cold-card-k">fresh · 5 min</span>
                        </div>
                        <p class="w-cold-card-d">
                            Write her character. Pick a name, a model, a rhythm. She wakes up new — knowing only what you wrote and that you exist.
                        </p>
                        <span class="w-cold-card-go">begin →</span>
                    </button>

                    <button class="w-cold-card" data-act="migrate">
                        <div class="w-cold-card-h">
                            <span class="w-cold-card-t">Migrate</span>
                            <span class="w-cold-card-k">distilled · 10 min</span>
                        </div>
                        <p class="w-cold-card-d">
                            Bring an existing conversation history forward — Claude.ai or ChatGPT JSON. She wakes up already knowing you.
                        </p>
                        <span class="w-cold-card-go">upload export →</span>
                    </button>
                </div>

                <div class="w-cold-foot">
                    <span>local-only · no telemetry</span>
                </div>
            </div>
        `;
        for (const c of this.querySelectorAll('.w-cold-card')) {
            c.onclick = () => this.dispatchEvent(new CustomEvent(c.dataset.act));
        }
        const cancel = this.querySelector('.w-cold-cancel');
        if (cancel) cancel.onclick = () => this.dispatchEvent(new CustomEvent('cancel'));

        /* On first-ever load (no personas), keep the original headline. */
        if (!this._hasPersonas) {
            this.querySelector('.w-cold-greet').innerHTML = `
                nobody lives here <em>yet</em>.
                <span class="w-cold-sub">
                    someone is about to. they'll wake up on your machine, breathe through the day, write things down,
                    and be here tomorrow. you decide who.
                </span>
            `;
        }
    }
}
customElements.define('onboarding-cold', OnboardingCold);
