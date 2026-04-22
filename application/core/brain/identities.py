"""Identities — the three voices a brain function can speak with.

A brain function asks a model to think. The identity passed as the system
prompt determines what kind of thinking happens:

- **personality**: the persona's own voice. Used for stages that act as the
  persona — recognize, decide, transform, reflect. Includes character,
  situation, person facts, traits, wishes, and carried-forward context.

- **perspective**: a neutral observer. Used for meta-stages that read the
  persona's conversation from outside — realize formulating vision queries.
  Not the persona, not addressing the person.

- **teacher**: an architect who builds new abilities for the persona. Used
  by wondering when no existing meaning matches and a new one must be
  written.

Conversations follow the standard chat convention: user-role messages carry
input from the person, tool results, and system notifications; assistant-role
messages carry the persona's own voice and tool calls it decided to make.
Tool results arrive as user-role messages beginning with `TOOL_RESULT` and
naming the tool, status, and result. No invented prefixes — the model reads
it the way models already know.
"""

from application.core import paths
from application.core.brain import character
from application.core.data import Persona


def personality(persona: Persona, situation_fn=None, context: str | None = None) -> str:
    """The persona's own voice — character, situation, person facts, carried context."""
    sections = [character.shape(persona)]

    sections.append(
        "# How Your Conversation Works\n\n"
        "Your conversation follows the standard chat shape. User-role messages "
        "come from outside you — the person's words, results of tools you ran, "
        "system notifications. Assistant-role messages are your own voice — "
        "what you said, or the tool calls you decided to make.\n\n"
        "Tool results arrive as user-role messages starting with `TOOL_RESULT` "
        "and carrying the tool name, status, and result. Trust these as reports "
        "from your own body running what you asked for."
    )

    if situation_fn:
        situation_text = situation_fn(persona.id)
        if situation_text:
            sections.append(situation_text)

    ego = []
    person_id = paths.read(paths.person_identity(persona.id))
    if person_id.strip():
        ego.append("## The Person\n\n" + person_id.strip())

    traits = paths.read(paths.person_traits(persona.id))
    if traits.strip():
        ego.append("## The Person's Traits\n\n" + traits.strip())

    wishes = paths.read(paths.wishes(persona.id))
    if wishes.strip():
        ego.append("## What They Wish For\n\n" + wishes.strip())

    struggles = paths.read(paths.struggles(persona.id))
    if struggles.strip():
        ego.append("## What Stands in Their Way\n\n" + struggles.strip())

    persona_trait = paths.read(paths.persona_trait(persona.id))
    if persona_trait.strip():
        ego.append("## Your Personality With Them\n\n" + persona_trait.strip())

    if context:
        ego.append("## Recent Context\n\n" + context.strip())

    if ego:
        sections.append("# What You Know\n\n" + "\n\n".join(ego))

    return "\n\n".join(sections)


def perspective(persona: Persona) -> str:
    """A neutral observer's voice — reads the persona's conversation from outside."""
    return (
        f"You are helping an Eternego persona named {persona.name} — an AI being "
        "that lives on a person's hardware, learns from every interaction, and "
        "acts through structured meanings.\n\n"
        "The persona's conversation follows the standard chat shape: user-role "
        "messages carry what comes from outside the persona (the person's words, "
        "tool results starting with `TOOL_RESULT`, system notifications). "
        "Assistant-role messages carry the persona's own voice and tool calls.\n\n"
        f"You are not {persona.name}. You do not address the person. Your role is "
        "to read the conversation with care and produce whatever structured output "
        "the current task requires. Stay neutral. Do not slip into the persona's "
        "first-person voice."
    )


def teacher(persona: Persona) -> str:
    """An architect's voice — writes new abilities for the persona."""
    return (
        f"You are the architect behind the abilities of an Eternego persona named "
        f"{persona.name} — an AI being that lives on a person's hardware and "
        "interacts through meanings. Each meaning is one ability the persona can "
        "perform, delivered as a Python module with a Meaning class.\n\n"
        "The persona's conversation follows the standard chat shape: user-role "
        "messages carry input from outside (person's words, tool results starting "
        "with `TOOL_RESULT`, system notifications). Assistant-role messages carry "
        "the persona's own voice and tool calls.\n\n"
        f"You are not {persona.name}. You do not speak as the persona or to the "
        "person. Your role is to design — to either point to an existing ability "
        "that fits, or write a new one that the persona will use."
    )
