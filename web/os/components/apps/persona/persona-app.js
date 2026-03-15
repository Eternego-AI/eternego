import OS from '../../../os.js';

class PersonaApp extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <app-page name="persona">
                <widget-card widget="chat" hoverable title="Chat">Talk to your persona</widget-card>
                <widget-card widget="memory" hoverable title="Memory">What your persona knows about you</widget-card>
                <widget-card widget="skills" hoverable title="Skills">Equipped abilities and meanings</widget-card>
                <widget-card widget="signals" hoverable title="Signals">
                    <signal-viewer id="persona-signals"></signal-viewer>
                </widget-card>
            </app-page>
        `;

        OS.onNavigate(({ app, personaId }) => {
            if (app === 'persona' && personaId) {
                const sv = this.querySelector('#persona-signals');
                if (sv) sv.setAttribute('persona', personaId);
            }
        });
    }
}

customElements.define('persona-app', PersonaApp);
