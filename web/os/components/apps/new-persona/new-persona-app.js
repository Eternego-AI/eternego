class NewPersonaApp extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <app-page name="new-persona">
                <widget-card widget="create" hoverable title="Create">
                    <create-widget></create-widget>
                </widget-card>
                <widget-card widget="migrate" hoverable title="Migrate">
                    Import a persona from a diary export.
                </widget-card>
            </app-page>
        `;
    }
}

customElements.define('new-persona-app', NewPersonaApp);
