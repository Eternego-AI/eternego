/* <breath-dot state="resting|thinking|sleeping|sick|stopped">
   A small living indicator. State-driven via attribute, animation in CSS. */

class BreathDot extends HTMLElement {
    static get observedAttributes() { return ['state']; }
    attributeChangedCallback() {} /* CSS reacts via [state] selector */
}
customElements.define('breath-dot', BreathDot);
