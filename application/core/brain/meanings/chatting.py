"""Meaning — chatting with the person."""

from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants to have a conversation with {persona.name}"


def prompt(persona: Persona) -> str:
    return (
        "Be with the person through words. The conversation follows below — user turns are theirs, "
        "assistant turns are yours. You can reply to what was just said, initiate something new "
        "(a question, an observation, a check-in) when the moment calls for it, or stay silent "
        "when nothing worth saying is ready. If you have not yet learned who the person is, "
        "initiating is the right move — ask about them warmly, one thing at a time.\n\n"
        "## Tool: `say`\n\n"
        "- `text` (string): the message to send. An empty string means you stay silent this turn.\n\n"
        "## Output\n\n"
        "```json\n"
        '{"reason": "<one short sentence>",\n'
        ' "tool": "say",\n'
        ' "text": "<your message, or an empty string for silence>"}\n'
        "```"
    )
