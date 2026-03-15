class SystemApp extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <app-page name="system">
                <widget-card widget="signals" hoverable title="Signals">
                    <signal-viewer></signal-viewer>
                </widget-card>
            </app-page>
        `;
    }
}

customElements.define('system-app', SystemApp);
