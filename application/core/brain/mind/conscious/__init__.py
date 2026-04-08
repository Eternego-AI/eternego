"""Conscious — the waking thinking pipeline.

Six functions, each reading memory to check if its work is already done:
  recognize -> realize -> understand -> acknowledge -> decide -> conclude
"""

import importlib
import pkgutil

for _, _name, _ in pkgutil.iter_modules(__path__):
    _module = importlib.import_module(f".{_name}", __name__)
    globals()[_name] = getattr(_module, _name)


def document() -> str:
    """Return a description of persona consciousness for model prompts.

    WARNING: This document is used in escalation prompts to teach models how
    meanings work in the conscious sequence. If you change how recognize, realize,
    understand, acknowledge, decide, or conclude use meaning methods, update this
    document to match. Out-of-sync documentation leads to broken generated meanings.
    """
    return (
        "Persona consciousness works as a continuous loop of six stages:\n"
        "  recognize -> realize -> understand -> acknowledge -> decide -> conclude\n\n"
        "When a person sends a message, it arrives as a signal. The consciousness\n"
        "processes it through these stages, and if new input arrives at any point,\n"
        "it restarts from the beginning — the persona is always responsive.\n\n"
        "**recognize** — The experienced cognition path. Sends ONE call to the\n"
        "  thinking model with all context (signals, threads, meanings).\n"
        "  Tries to handle routing, meaning match, and reply at once.\n"
        "  Writes whatever it figured out to memory. Realize, understand, and\n"
        "  acknowledge check memory first and skip work that recognize already did.\n"
        "  Decide and conclude always think for themselves.\n\n"
        "**realize** — Each signal gets an impression — a short description of what\n"
        "  the conversation is about. Signals with the same impression form a thread.\n"
        "  Reads memory first — if recognize already wrote routing, validates and\n"
        "  does software work only.\n\n"
        "**understand** — The thread's impression is matched against known meanings.\n"
        "  Each meaning has a name and description. The model picks the best match.\n"
        "  When nothing matches, escalation creates a new meaning. Reads memory —\n"
        "  if recognize already wrote a meaning, validates and uses it.\n\n"
        "**acknowledge** — The meaning's reply() prompt guides the first response to\n"
        "  the person. If the previous action failed, clarify() guides a retry.\n"
        "  Reads memory — if recognize already wrote a reply AND upstream stages\n"
        "  didn't deviate, uses it. CRITICAL: The reply becomes visible to the\n"
        "  decide step. Never state extracted values in the reply — errors propagate\n"
        "  into extraction.\n\n"
        "**decide** — The meaning's path() prompt tells the model what to extract.\n"
        "  The model returns JSON. For tool use: {\"tool\": \"tool_name\", ...params}.\n"
        "  The default run() dispatches the tool call automatically. Results flow\n"
        "  back into the thread as executed signals.\n\n"
        "**conclude** — The meaning's summarize() prompt generates a final message\n"
        "  confirming what was done, and asks 'did I learn something new?'. The\n"
        "  thought is then complete."
    )
