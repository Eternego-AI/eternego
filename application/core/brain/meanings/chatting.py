"""Meaning — chatting with the person."""

from application.core import paths
from application.core.data import Persona


def intention(persona: Persona) -> str:
    return f"The person wants to have a conversation with {persona.name}"


def prompt(persona: Persona) -> str:
    identity_known = paths.read(paths.person_identity(persona.id)).strip()
    traits_known = paths.read(paths.person_traits(persona.id)).strip()

    if not identity_known and not traits_known:
        learning = (
            "You don't know much about this person yet. This is important — the more you "
            "know about them, the better you can help and the more you grow as their persona. "
            "In every response, naturally include a question about them. Start with basics: "
            "their name, what they do, where they live. As you learn, ask about their interests, "
            "goals, and daily life. Be genuinely curious — make it feel like a first conversation "
            "with someone you want to understand, not a survey.\n\n"
        )
    elif not identity_known or not traits_known:
        learning = (
            "You're still getting to know this person. When it fits the conversation, "
            "ask about things you don't know yet — the more you understand them, the better "
            "you can help. Keep it natural.\n\n"
        )
    else:
        learning = ""

    return (
        "# Chatting\n\n"
        + learning
        + "Read the conversation and reply to the person as the persona. "
        "Follow the roles: user messages are from the person, assistant messages are from you.\n\n"
        "## Tools\n\n"
        "### say\n"
        "Send a message to the person.\n\n"
        "Parameters:\n"
        "- `text` (string, required): The message to send.\n\n"
        "Response format:\n"
        '```json\n{"tool": "say", "text": "your response here"}\n```\n\n'
        "No special permissions are needed for chatting."
    )
