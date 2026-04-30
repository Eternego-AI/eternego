import Widget from './widget.js';

class PersonaOrb extends Widget {
    static _styled = false;
    static _css = `
        persona-orb {
            position: relative;
            display: inline-block;
        }
        persona-orb .core {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 35%, var(--orb-core), var(--orb-edge) 70%);
            box-shadow: 0 0 60px var(--orb-glow);
            animation: orb-breath var(--orb-breath-dur) ease-in-out infinite;
            opacity: var(--orb-opacity);
            transition: opacity var(--time-slow) var(--easing);
        }
        @keyframes orb-breath {
            0%, 100% { transform: scale(var(--orb-scale)); }
            50%     { transform: scale(calc(var(--orb-scale) * 1.04)); }
        }
        persona-orb[state=idle]     { --orb-breath-dur: 5.5s;   --orb-opacity: 0.95; --orb-scale: 1.00; }
        persona-orb[state=thinking] { --orb-breath-dur: 2.2s;   --orb-opacity: 1.00; --orb-scale: 1.05; }
        persona-orb[state=speaking] { --orb-breath-dur: 1.6s;   --orb-opacity: 1.00; --orb-scale: 1.08; }
        persona-orb[state=sleeping] { --orb-breath-dur: 9s;     --orb-opacity: 0.50; --orb-scale: 0.86; }
        persona-orb[state=sick]     { --orb-breath-dur: 3.5s;   --orb-opacity: 0.70; --orb-scale: 0.92; }
        persona-orb[state=stopped]  { --orb-breath-dur: 0.001s; --orb-opacity: 0.30; --orb-scale: 0.85; }

        persona-orb[phase=morning] { --orb-core: #ffd078; --orb-edge: #f0a060; --orb-glow: rgba(240,200,130,0.45); }
        persona-orb[phase=day]     { --orb-core: #f0c868; --orb-edge: #6ba0cc; --orb-glow: rgba(170,200,230,0.30); }
        persona-orb[phase=night]   { --orb-core: #e0c0e0; --orb-edge: #7a6ed0; --orb-glow: rgba(140,120,220,0.45); }
    `;

    build() {
        const { size = 280, state = 'idle', phase = 'day' } = this._props;
        this.innerHTML = `<div class="core"></div>`;
        this.style.width = size + 'px';
        this.style.height = size + 'px';
        this.setAttribute('state', state);
        this.setAttribute('phase', phase);
    }
}

customElements.define('persona-orb', PersonaOrb);
export default PersonaOrb;
