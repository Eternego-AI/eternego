"""Ego — the persona's reasoning engine, grounded in its full identity.

The ego is everything the persona is:
  character    — cornerstone (why) + values (what) + morals (how)
  traits       — learned behaviours and limitations
  struggles    — known weaknesses the persona is working through
  wishes       — motivational drives and aspirations

effect(persona, mem)         builds the system prompt from identity + current memory state.
talk(persona, mem, prompt)   converses using the ego system prompt.
reason(persona, mem, prompt) reasons in JSON mode with a step-by-step instruction.
will(persona, mem, thoughts) selects one thought to focus on from many.
"""

import uuid

from application.core.data import Persona
from application.core.brain.cognitive.data import Stimulus, Perception, Thought
from application.core.brain.cognitive.memory import Memory
from application.core.brain.cognitive import character, meanings
from application.core import local_model
from application.platform import logger


def status_quo(mem: Memory) -> str:
    """Serialise current memory state as a readable section for the model."""
    lines = ["## Current Memory"]

    unprocessed = mem.presence.be()
    if unprocessed:
        lines.append(f"\n### Presence ({len(unprocessed)} unprocessed)")
        for s in unprocessed:
            lines.append(f"  [{s.role}] {s.content}")

    unattended = mem.awareness.be()
    if unattended:
        lines.append(f"\n### Awareness ({len(unattended)} unattended)")
        for p in unattended:
            lines.append(f"  [{p.meaning}] {p.stimulus.content}")

    unpicked = [t for t in mem.mind.read() if t.picked_at is None]
    if unpicked:
        conscious = [t for t in unpicked if t.role != "assistant"]
        sub = [t for t in unpicked if t.role == "assistant"]
        if conscious:
            lines.append(f"\n### Conscious ({len(conscious)} pending)")
            for t in conscious:
                lines.append(f"  [{t.meaning}] {t.content}")
        if sub:
            lines.append(f"\n### Sub-conscious ({len(sub)} pending)")
            for t in sub:
                lines.append(f"  [{t.meaning}] {t.content}")

    if len(lines) == 1:
        lines.append("\n(empty)")

    return "\n".join(lines)


def effect(persona: Persona, mem: Memory) -> str:
    """Build the full ego system prompt: character + current memory state."""
    return character.shape(persona).content + "\n\n" + status_quo(mem)


async def talk(persona: Persona, mem: Memory, prompt: str) -> str:
    """Call the persona's model conversationally — no structure, no JSON.

    Uses the ego system prompt as the system message and the given prompt
    as the user message. Returns the raw model response.
    """
    messages = [
        {"role": "system", "content": effect(persona, mem)},
        {"role": "user", "content": prompt},
    ]
    return await local_model.chat(persona.model.name, messages)


async def reason(persona: Persona, mem: Memory, prompt: str) -> dict:
    """Call the persona's model in JSON mode with a step-by-step reasoning instruction.

    Adds a reasoning instruction to the ego system prompt, then calls the model
    with the given prompt as the user message. Returns the parsed JSON response.
    """
    def reasoning_system():
        return (
            effect(persona, mem)
            + "\n\nReason step by step before responding. "
            "Consider all relevant factors and consequences. "
            "Return your response as a JSON object."
        )

    messages = [
        {"role": "system", "content": reasoning_system()},
        {"role": "user", "content": prompt},
    ]
    return await local_model.chat_json(persona.model.name, messages)


async def will(persona: Persona, mem: Memory, thoughts: list[Thought]) -> Thought:
    """Select one thought to focus on from competing conscious thoughts.

    One thought:   natural selection — returned immediately without a model call.
    Many thoughts: calls the model with a will-specific prompt, asking the persona
                   to choose the most important thought given who it is right now.
    """
    if len(thoughts) == 1:
        return thoughts[0]

    def will_system():
        return (
            effect(persona, mem)
            + "\n\nYou are given a list of thoughts competing for your attention. "
            "Considering who you are and what matters most to you right now, "
            "select the one thought you should focus on next. "
            "Return JSON with a single key 'index' — the 0-based index of your choice."
        )

    numbered = "\n".join(f"{i}. [{t.role}] {t.content}" for i, t in enumerate(thoughts))
    messages = [
        {"role": "system", "content": will_system()},
        {"role": "user", "content": numbered},
    ]
    response = await local_model.chat_json(persona.model.name, messages)
    index = response.get("index")
    if not isinstance(index, int):
        logger.warning("will: model returned unexpected output, falling back to first thought", {"persona_id": persona.id})
        return thoughts[0]
    return thoughts[max(0, min(index, len(thoughts) - 1))]


async def understand(persona: Persona, mem: Memory, stimuli: list[Stimulus]) -> list[Perception]:
    """Interpret a list of stimuli through the persona's ego.

    Calls reason with a prompt asking the model to give each stimulus a meaning
    and optionally continue an existing thread. Returns a list of perceptions
    ready for awareness. Returns [] if the model output is not well-defined.
    """
    if not stimuli:
        return []

    def prompt():
        vocabulary = ", ".join(f'"{m}"' for m in meanings.we_know())
        lines = [
            "Given these stimuli, classify the meaning of each one.",
            f"Meaning must be one of: {vocabulary}.",
            "Return JSON: {\"perceptions\": [{\"meaning\": \"...\", \"thread_id\": null}]}",
            "One entry per stimulus, same order.\n",
        ]
        for i, s in enumerate(stimuli):
            lines.append(f"{i}. [{s.role}] {s.content}")
        return "\n".join(lines)

    response = await reason(persona, mem, prompt())
    items = response.get("perceptions") if isinstance(response, dict) else None
    if not isinstance(items, list) or len(items) != len(stimuli):
        logger.warning("understand: model returned unexpected output", {"persona_id": persona.id})
        return []

    def to_perception(stimulus, item):
        meaning = item.get("meaning")
        if meaning not in meanings.we_know():
            return None
        return Perception(
            stimulus=stimulus,
            meaning=meaning,
            thread_id=item.get("thread_id"),
        )

    result = [to_perception(s, item) for s, item in zip(stimuli, items)]
    if any(p is None for p in result):
        logger.warning("understand: one or more perceptions are malformed", {"persona_id": persona.id})
        return []
    return result


async def attention(persona: Persona, mem: Memory, perceptions: list[Perception]) -> list[Thought]:
    """Assign perceptions to threads and roles through the persona's ego.

    Calls reason with a prompt asking the model to assign each perception to a
    thread (existing or new) and determine its stream role. Returns a list of
    thoughts ready for mind. Returns [] if the model output is not well-defined.
    """
    if not perceptions:
        return []

    def prompt():
        lines = [
            "Given these perceptions, assign each to a thread and a role.",
            "Role: \"user\" for things requiring deliberate attention, \"assistant\" for things to execute.",
            "Thread: use the existing thread_id if this continues that thread, otherwise use \"NEW\".",
            "Return JSON: {\"thoughts\": [{\"thread_id\": \"existing-or-NEW\", \"role\": \"user|assistant\"}]}",
            "One entry per perception, same order.\n",
        ]
        for i, p in enumerate(perceptions):
            thread = p.thread_id or "none"
            lines.append(f"{i}. [thread: {thread}] {p.meaning}")
        return "\n".join(lines)

    response = await reason(persona, mem, prompt())
    items = response.get("thoughts") if isinstance(response, dict) else None
    if not isinstance(items, list) or len(items) != len(perceptions):
        logger.warning("attention: model returned unexpected output", {"persona_id": persona.id})
        return []

    def to_thought(perception, item):
        role = item.get("role")
        if role not in ("user", "assistant"):
            return None
        thread_id = item.get("thread_id")
        if not thread_id or thread_id == "NEW":
            thread_id = str(uuid.uuid4())
        return Thought(
            thread_id=thread_id,
            role=role,
            content=perception.stimulus.content,
            meaning=perception.meaning,
        )

    result = [to_thought(p, item) for p, item in zip(perceptions, items)]
    if any(t is None for t in result):
        logger.warning("attention: one or more thoughts are malformed", {"persona_id": persona.id})
        return []
    return result
