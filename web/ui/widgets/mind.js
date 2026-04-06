import Widget from './widget.js';

/**
 * Mind — a 3D breathing orb visualization for the persona panel.
 *
 * Idle: slow gentle breathing with tilted orbital rings.
 * Thinking: faster pulse, brighter glow, accent-blue rings, pulsing outer ring.
 * Sleeping: nearly invisible, extremely slow.
 * Speaking: brief warm pulse after the persona responds.
 */
class MindWidget extends Widget {
    static _css = `
        mind-widget {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 0;
            min-width: 0;
            cursor: pointer;
        }
        mind-widget canvas {
            width: 100%;
            height: 100%;
        }
    `;

    // init({ onOpenMind })
    build() {
        this.constructor._injectStyles();
        this._canvas = document.createElement('canvas');
        this.appendChild(this._canvas);
        this._ctx = this._canvas.getContext('2d');
        this._personaName = '';
        this._initial = '';
        this._state = 'idle';
        this._phase = 0;
        this._ringPhase = 0;
        this._running = true;
        this._started = false;

        this._canvas.addEventListener('click', () => {
            if (this._props.onOpenMind) this._props.onOpenMind();
        });

        this._ro = new ResizeObserver(() => {
            if (this._canvas.clientWidth > 0) {
                this._resize();
                if (!this._started) { this._started = true; this._animate(); }
            }
        });
        this._ro.observe(this);
    }

    setPersona(name) {
        this._personaName = name || '';
        this._initial = (name || '')[0]?.toUpperCase() || '';
    }

    setState(state) { this._state = state; }

    setGraph(_data) { /* accepted, not visualized */ }

    activateStage(_stage, _impression, _meaning) { /* accepted, not visualized */ }

    _resize() {
        const r = window.devicePixelRatio || 1;
        this._canvas.width = this._canvas.clientWidth * r;
        this._canvas.height = this._canvas.clientHeight * r;
        this._ctx.setTransform(r, 0, 0, r, 0, 0);
    }

    _animate() {
        if (!this._running) return;
        this._draw();
        requestAnimationFrame(() => this._animate());
    }

    _draw() {
        const ctx = this._ctx;
        const w = this._canvas.clientWidth;
        const h = this._canvas.clientHeight;
        if (w < 1 || h < 1) return;
        const cx = w / 2;
        const cy = h / 2;

        const thinking = this._state === 'thinking';
        const sleeping = this._state === 'sleeping';
        const speaking = this._state === 'speaking';
        const stopped = this._state === 'stopped';

        const speed = stopped ? 0 : thinking ? 0.025 : sleeping ? 0.003 : speaking ? 0.018 : 0.008;
        this._phase += speed;
        this._ringPhase += stopped ? 0 : thinking ? 0.012 : sleeping ? 0.0005 : 0.001;
        const breath = Math.sin(this._phase);

        // -- Canvas background: subtle radial gradient, no hard edges --
        ctx.clearRect(0, 0, w, h);
        const bgCenter = ctx.createRadialGradient(cx, cy * 0.85, 0, cx, cy, Math.max(w, h) * 0.75);
        const bgAlpha = thinking ? 0.04 : sleeping ? 0.005 : 0.02;
        bgCenter.addColorStop(0, `rgba(80, 100, 180, ${bgAlpha})`);
        bgCenter.addColorStop(0.5, `rgba(40, 50, 100, ${bgAlpha * 0.4})`);
        bgCenter.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = bgCenter;
        ctx.fillRect(0, 0, w, h);

        // Responsive orb size (base)
        const baseOrbR = Math.min(w, h) * 0.28;

        // -- Background glow that bleeds LEFT beyond the canvas --
        const bleedAlpha = thinking ? 0.06 + breath * 0.02
                         : speaking ? 0.03 + breath * 0.01
                         : sleeping ? 0.005
                         : 0.025 + breath * 0.008;
        const bleedGrad = ctx.createRadialGradient(cx, cy, baseOrbR, cx * 0.2, cy, Math.max(w, h) * 1.2);
        bleedGrad.addColorStop(0, `rgba(140, 160, 255, ${bleedAlpha})`);
        bleedGrad.addColorStop(0.3, `rgba(140, 160, 255, ${bleedAlpha * 0.5})`);
        bleedGrad.addColorStop(0.7, `rgba(100, 120, 220, ${bleedAlpha * 0.15})`);
        bleedGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = bleedGrad;
        ctx.fillRect(0, 0, w, h);
        const orbRadius = baseOrbR + breath * (thinking ? 4 : speaking ? 3 : 1.5);

        // -- Ambient glow around the orb --
        const glowAlpha = thinking ? 0.16 + breath * 0.06
                        : speaking ? 0.08 + breath * 0.03
                        : sleeping ? 0.008
                        : 0.05 + breath * 0.018;
        const glowColor = speaking ? '160, 170, 255' : '140, 160, 255';
        const glowRadius = thinking ? orbRadius * 4.5 : orbRadius * 3.5;
        const glow = ctx.createRadialGradient(cx, cy, orbRadius * 0.15, cx, cy, glowRadius);
        glow.addColorStop(0, `rgba(${glowColor}, ${glowAlpha})`);
        glow.addColorStop(0.4, `rgba(${glowColor}, ${glowAlpha * 0.4})`);
        glow.addColorStop(1, 'transparent');
        ctx.fillStyle = glow;
        ctx.fillRect(0, 0, w, h);

        // -- Tilted orbital rings with depth --
        const rings = [
            { offset: 0.12, thickness: 0.5, speedMul: 1.8, alphaBase: 0.04, tilt: 0.85 },
            { offset: 0.22, thickness: 1.0, speedMul: 1.2, alphaBase: 0.06, tilt: 0.90 },
            { offset: 0.34, thickness: 1.5, speedMul: 0.7, alphaBase: 0.08, tilt: 0.95 },
            { offset: 0.48, thickness: 2.0, speedMul: 0.4, alphaBase: 0.10, tilt: 1.00 },
        ];

        for (let i = 0; i < rings.length; i++) {
            const ring = rings[i];
            const ringR = orbRadius + orbRadius * ring.offset;
            const ringRy = ringR * ring.tilt;

            let ringAlpha;
            let r, g, b;
            if (thinking) {
                ringAlpha = ring.alphaBase * 2.0 + Math.sin(this._phase + i * 0.9) * 0.03;
                r = 140; g = 160; b = 255;
            } else if (speaking) {
                ringAlpha = ring.alphaBase * 1.2 + Math.sin(this._phase + i * 0.9) * 0.015;
                r = 160; g = 170; b = 255;
            } else if (sleeping) {
                ringAlpha = ring.alphaBase * 0.15;
                r = 180; g = 190; b = 255;
            } else {
                ringAlpha = ring.alphaBase + Math.sin(this._phase + i * 0.9) * 0.015;
                r = 200; g = 210; b = 255;
            }
            if (ringAlpha <= 0) continue;

            const rotation = this._ringPhase * ring.speedMul * (i % 2 === 0 ? 1 : -1);

            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(rotation);
            ctx.beginPath();
            ctx.ellipse(0, 0, ringR, ringRy, 0, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${ringAlpha})`;
            ctx.lineWidth = ring.thickness;
            ctx.stroke();
            ctx.restore();
        }

        // -- Thinking: pulsing accent ring --
        if (thinking) {
            const pulseR = orbRadius + orbRadius * 0.3;
            const pulseAlpha = 0.1 + Math.sin(this._phase * 1.5) * 0.1;
            ctx.beginPath();
            ctx.arc(cx, cy, pulseR, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(140, 160, 255, ${pulseAlpha})`;
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // -- Orb fill: layered radial gradients for 3D glass sphere --
        // Layer 1: Core glow — bright center fading outward
        const coreFillAlpha = thinking ? 0.05
                            : speaking ? 0.04
                            : sleeping ? 0.01
                            : 0.03;
        const coreGrad = ctx.createRadialGradient(
            cx - orbRadius * 0.15, cy - orbRadius * 0.15, 0,
            cx, cy, orbRadius
        );
        coreGrad.addColorStop(0, `rgba(200, 210, 255, ${coreFillAlpha * 2.5})`);
        coreGrad.addColorStop(0.4, `rgba(160, 175, 255, ${coreFillAlpha * 1.2})`);
        coreGrad.addColorStop(0.8, `rgba(100, 120, 200, ${coreFillAlpha * 0.5})`);
        coreGrad.addColorStop(1, `rgba(60, 70, 140, ${coreFillAlpha * 0.2})`);
        ctx.beginPath();
        ctx.arc(cx, cy, orbRadius, 0, Math.PI * 2);
        ctx.fillStyle = coreGrad;
        ctx.fill();

        // Layer 2: Specular highlight — subtle bright spot upper-left
        const specGrad = ctx.createRadialGradient(
            cx - orbRadius * 0.35, cy - orbRadius * 0.35, 0,
            cx - orbRadius * 0.2, cy - orbRadius * 0.2, orbRadius * 0.6
        );
        const specAlpha = thinking ? 0.08 : sleeping ? 0.01 : 0.04;
        specGrad.addColorStop(0, `rgba(255, 255, 255, ${specAlpha})`);
        specGrad.addColorStop(0.5, `rgba(200, 215, 255, ${specAlpha * 0.3})`);
        specGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, orbRadius, 0, Math.PI * 2);
        ctx.fillStyle = specGrad;
        ctx.fill();

        // Layer 3: Shadow — darker bottom-right for depth
        const shadowGrad = ctx.createRadialGradient(
            cx + orbRadius * 0.3, cy + orbRadius * 0.3, 0,
            cx + orbRadius * 0.15, cy + orbRadius * 0.15, orbRadius * 0.9
        );
        const shadowAlpha = thinking ? 0.03 : sleeping ? 0.015 : 0.025;
        shadowGrad.addColorStop(0, `rgba(0, 0, 20, ${shadowAlpha})`);
        shadowGrad.addColorStop(0.6, `rgba(0, 0, 30, ${shadowAlpha * 0.5})`);
        shadowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, orbRadius, 0, Math.PI * 2);
        ctx.fillStyle = shadowGrad;
        ctx.fill();

        // -- Orb border (breathing) --
        const borderAlpha = thinking ? 0.25 + breath * 0.1
                          : speaking ? 0.14 + breath * 0.06
                          : sleeping ? 0.03 + breath * 0.01
                          : 0.08 + breath * 0.05;
        ctx.beginPath();
        ctx.arc(cx, cy, orbRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 255, 255, ${borderAlpha})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // -- Life signal: waveform inside the orb --
        this._drawWaveform(ctx, cx, cy, orbRadius, thinking, speaking, sleeping, stopped);

        // -- Sleeping dim overlay --
        if (sleeping) {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.08)';
            ctx.fillRect(0, 0, w, h);
        }
    }

    _drawWaveform(ctx, cx, cy, orbR, thinking, speaking, sleeping, stopped) {
        const waveWidth = orbR * 1.2;
        const points = 120;
        const t = this._phase;

        ctx.beginPath();
        ctx.moveTo(cx - waveWidth / 2, cy);

        for (let i = 0; i <= points; i++) {
            const x = cx - waveWidth / 2 + (i / points) * waveWidth;
            const pos = i / points;
            let y = 0;

            if (stopped) {
                // Flatline — persona is off
                y = 0;
            } else if (sleeping) {
                // Slow breath wave — gentle sine, barely moving
                y = Math.sin(pos * Math.PI * 2 + t * 0.5) * orbR * 0.06;
            } else if (thinking) {
                // EEG — layered frequencies, active, complex
                y = Math.sin(pos * Math.PI * 8 + t * 4) * orbR * 0.08
                  + Math.sin(pos * Math.PI * 14 + t * 6) * orbR * 0.05
                  + Math.sin(pos * Math.PI * 22 + t * 9) * orbR * 0.03;
            } else {
                // ECG heartbeat — flat line with periodic sharp peaks
                const cycle = (pos * 3 + t * 0.8) % 1;
                if (cycle > 0.38 && cycle < 0.42) {
                    y = -orbR * 0.04; // small P wave
                } else if (cycle > 0.44 && cycle < 0.46) {
                    y = -orbR * 0.12; // Q dip
                } else if (cycle > 0.46 && cycle < 0.50) {
                    y = orbR * 0.25; // R peak — the heartbeat
                } else if (cycle > 0.50 && cycle < 0.52) {
                    y = -orbR * 0.08; // S dip
                } else if (cycle > 0.56 && cycle < 0.62) {
                    y = orbR * 0.05; // T wave
                } else {
                    y = 0; // baseline
                }
                // Smooth transitions
                y *= Math.sin(pos * Math.PI); // fade at edges
            }

            // Speaking: add a warm ripple on top
            if (speaking) {
                y += Math.sin(pos * Math.PI * 6 + t * 5) * orbR * 0.06;
            }

            ctx.lineTo(x, cy + y);
        }

        const alpha = stopped ? 0.04
                    : thinking ? 0.35 + Math.sin(t) * 0.1
                    : speaking ? 0.25
                    : sleeping ? 0.06
                    : 0.15 + Math.sin(t) * 0.05;
        const r = stopped ? 100 : thinking ? 140 : speaking ? 160 : sleeping ? 180 : 200;
        const g = thinking ? 160 : speaking ? 170 : sleeping ? 190 : 210;
        const b = 255;

        ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        ctx.lineWidth = thinking ? 1.5 : 1;
        ctx.stroke();

        // Glow under the waveform
        if (!sleeping) {
            const glowAlpha = thinking ? 0.08 : speaking ? 0.04 : 0.02;
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${glowAlpha})`;
            ctx.lineWidth = 6;
            ctx.stroke();
        }
    }

    disconnectedCallback() {
        this._running = false;
        this._ro?.disconnect();
    }
}

customElements.define('mind-widget', MindWidget);
export default MindWidget;
