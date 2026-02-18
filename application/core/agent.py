"""Agent — persona identity initialization and management."""

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path

from application.platform import logger, filesystem, crypto, datetimes
from application.core import memories, paths, prompts, local_model, instructions, struggles
from application.core.data import Channel, Model, Persona, Thinking, Thought
from application.core.exceptions import IdentityError


def given(persona: Persona, document: dict) -> Thinking:
    """Give the agent external input and return the thinking process."""
    memories.agent(persona).remember(document)

    system_parts = []

    inst = instructions.read(persona)
    if inst:
        system_parts.append(inst)

    identity_path = persona.storage_dir / "persona-identity.md"
    if identity_path.exists():
        who_i_am = filesystem.read(identity_path).strip()
        if who_i_am:
            system_parts.append(who_i_am)

    context_path = persona.storage_dir / "persona-context.md"
    what_i_know = filesystem.read(context_path).strip() if context_path.exists() else ""
    if what_i_know:
        system_parts.append(what_i_know)

    skills_dir = persona.storage_dir / "skills"
    if skills_dir.exists():
        skill_parts = []
        for skill_file in sorted(skills_dir.glob("*.md")):
            content = filesystem.read(skill_file).strip()
            if content:
                skill_parts.append(f"## {skill_file.stem}\n\n{content}")
        if skill_parts:
            system_parts.append("# Skill Documents\n\n" + "\n\n---\n\n".join(skill_parts))

    person_identity_path = persona.storage_dir / "person-identity.md"
    person_known = person_identity_path.exists() and filesystem.read(person_identity_path).strip()
    if not person_known:
        system_parts.append(
            "You do not know your person yet — not their name or anything about them. "
            "Learn who they are naturally through this conversation."
        )

    if not what_i_know:
        system_parts.append(
            "Your own context and purpose have not yet been shaped. "
            "Ask your person what role they want you to play in their life."
        )

    system_message = "\n\n".join(system_parts)

    async def _reason() -> AsyncIterator[Thought]:
        while True:
            messages = [{"role": "system", "content": system_message}]

            messages.extend(memories.agent(persona).as_messages())

            acted = False
            said = ""
            reasoning = False
            escalating = False
            escalation = ""
            async for raw in local_model.stream(persona.model.name, messages):
                content = raw.get("message", {}).get("content", "")
                tool_calls = raw.get("message", {}).get("tool_calls")
                done = raw.get("done", False)

                if tool_calls:
                    yield Thought(intent="doing", content=content, tool_calls=tool_calls)
                    acted = True
                elif not done:
                    if "<think>" in content:
                        reasoning = True
                        content = content.replace("<think>", "")
                    if "</think>" in content:
                        reasoning = False
                        content = content.replace("</think>", "")
                        continue

                    if "<escalate>" in content:
                        escalating = True
                        content = content.replace("<escalate>", "")
                    if "</escalate>" in content:
                        escalating = False
                        escalation += content.replace("</escalate>", "")
                        yield Thought(intent="consulting", content=escalation)
                        continue

                    if escalating:
                        escalation += content
                    elif reasoning:
                        yield Thought(intent="reasoning", content=content)
                    else:
                        said += content
                        yield Thought(intent="saying", content=content)

            if said:
                memories.agent(persona).remember({"type": "say", "content": said})

            if not acted:
                break

    return Thinking(_reason)


async def initialize(
    name: str,
    model: Model,
    frontier: Model | None = None,
    channels: list[Channel] | None = None,
) -> Persona:
    """Create a new persona with a fresh identity."""
    logger.info("Initializing persona identity", {"name": name, "model": model.name})
    persona_id = str(uuid.uuid4())
    return Persona(
        id=persona_id,
        name=name,
        model=model,
        frontier=frontier,
        channels=channels,
    )


async def embody(persona: Persona, model: Model, name: str) -> None:
    """Set the base model and assign the persona-owned model name."""
    logger.info("Embodying persona with model", {"persona_id": persona.id, "model": model.name, "name": name})
    persona.base_model = model.name
    persona.model = Model(name=name)


async def build(persona: Persona) -> None:
    """Prepare the agent's identity, context, and training directories."""
    logger.info("Building agent", {"persona_id": persona.id})
    try:
        birthday = datetimes.now().date()
        persona_identity = f"Name: {persona.name}\nBirthday: {birthday}\n"
        filesystem.write(persona.storage_dir / "persona-identity.md", persona_identity)
        filesystem.write(persona.storage_dir / "persona-context.md", "")
        filesystem.ensure_dir(persona.storage_dir / "training")
    except OSError as e:
        raise IdentityError("Failed to build agent") from e


async def identity(persona: Persona) -> dict[str, list[str]]:
    """Read the agent's identity and context."""
    logger.info("Reading agent identity", {"persona_id": persona.id})
    try:
        identity_content = filesystem.read(persona.storage_dir / "persona-identity.md")
        context_content = filesystem.read(persona.storage_dir / "persona-context.md")

        return {
            "identity": [line for line in identity_content.splitlines() if line.strip()],
            "context": [line for line in context_content.splitlines() if line.strip()],
        }
    except OSError as e:
        raise IdentityError("Failed to read agent identity") from e


async def knowledge(persona: Persona) -> dict:
    """Read existing knowledge for observation deduplication. Returns empty strings on failure."""
    logger.info("Reading existing knowledge", {"persona_id": persona.id})
    try:
        struggles_path = paths.struggles(persona.id)
        return {
            "person_identity": filesystem.read(persona.storage_dir / "person-identity.md").strip(),
            "person_traits": filesystem.read(persona.storage_dir / "person-traits.md").strip(),
            "persona_context": filesystem.read(persona.storage_dir / "persona-context.md").strip(),
            "person_struggles": filesystem.read(struggles_path).strip() if struggles_path.exists() else "",
        }
    except OSError:
        return {"person_identity": "", "person_traits": "", "persona_context": "", "person_struggles": ""}


async def delete_identity(persona: Persona, hash_part: str) -> None:
    """Remove an entry from persona identity by its content hash."""
    logger.info("Deleting identity entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = persona.storage_dir / "persona-identity.md"
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise IdentityError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise IdentityError("Failed to delete identity entry") from e


async def delete_context(persona: Persona, hash_part: str) -> None:
    """Remove an entry from persona context by its content hash."""
    logger.info("Deleting context entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        path = persona.storage_dir / "persona-context.md"
        content = filesystem.read(path)
        lines = content.splitlines()
        remaining = [line for line in lines if crypto.generate_unique_id(line) != hash_part]
        if len(remaining) == len(lines):
            raise IdentityError("Entry not found or already modified")
        filesystem.write(path, "\n".join(remaining) + "\n" if remaining else "")
    except OSError as e:
        raise IdentityError("Failed to delete context entry") from e


async def learn(persona: Persona, context: list[str]) -> None:
    """Save context observations to the persona's context file."""
    logger.info("Learning from context", {"persona_id": persona.id})
    try:
        if context:
            filesystem.append(persona.storage_dir / "persona-context.md", "\n".join(context) + "\n")
    except OSError as e:
        raise IdentityError("Failed to save context") from e


def find(persona_id: str) -> Persona:
    """Load the persona for the given persona_id from its identity file."""
    logger.info("Loading persona", {"persona_id": persona_id})
    config_path = paths.agent_identity(persona_id)
    try:
        if not config_path.exists():
            raise IdentityError("Persona not found")
        config = filesystem.read_json(config_path)
        return Persona(
            id=config["id"],
            name=config["name"],
            model=Model(**config["model"]),
            base_model=config.get("base_model", config["model"]["name"]),
            frontier=Model(**config["frontier"]) if config.get("frontier") else None,
            channels=[Channel(**ch) for ch in config["channels"]] if config.get("channels") else None,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise IdentityError("Persona data is malformed") from e
    except OSError as e:
        raise IdentityError("Failed to load persona") from e


async def personas() -> list[Persona]:
    """Load all personas by checking the personas directory and loading each config."""
    logger.info("Loading personas")
    root = paths.agents_home()
    if not root.exists():
        return []
    try:
        persona_ids = [d.name for d in root.iterdir() if d.is_dir() and (d / "config.json").exists()]
    except OSError as e:
        raise IdentityError("Failed to list personas") from e
    result = []
    for persona_id in persona_ids:
        try:
            persona = find(persona_id)
            result.append(persona)
        except (IdentityError, OSError):
            continue
    return result


async def distill(materials: Path) -> Persona:
    """Restore a persona from diary materials into the personas directory."""
    logger.info("Distilling persona from materials", {"path": str(materials)})
    try:
        persona_id = filesystem.leaf(materials)
        filesystem.copy_dir(materials, paths.agents_home() / persona_id)
        return find(persona_id)
    except IdentityError:
        raise
    except OSError as e:
        raise IdentityError("Failed to restore persona files") from e


async def sleep(persona: Persona) -> str:
    """Assemble DNA into a sleep prompt for training data generation."""
    logger.info("Preparing sleep prompt", {"persona_id": persona.id})
    try:
        dna_path = persona.storage_dir / "dna.md"
        dna = filesystem.read(dna_path) if dna_path.exists() else ""

        return prompts.sleep(dna=dna)
    except OSError as e:
        raise IdentityError("Failed to read persona files for sleep") from e


async def save_training_set(persona: Persona, training_set: str) -> None:
    """Save a training set to the persona's training directory."""
    logger.info("Saving training set", {"persona_id": persona.id})
    try:
        now = datetimes.date_stamp(datetimes.now())
        path = persona.storage_dir / "training" / f"batch-{now}.json"
        filesystem.write(path, training_set)
    except OSError as e:
        raise IdentityError("Failed to save training set") from e


async def wake_up(persona: Persona, new_model: str) -> None:
    """Set the new model, clear traits, and save persona."""
    logger.info("Waking up persona", {"persona_id": persona.id, "new_model": new_model})
    try:
        persona.model = Model(name=new_model)

        traits_path = persona.storage_dir / "person-traits.md"
        if traits_path.exists():
            filesystem.write(traits_path, "")

        await save_persona(persona)
    except OSError as e:
        raise IdentityError("Failed to wake up persona") from e


async def save_persona(persona: Persona) -> None:
    """Save persona configuration."""
    logger.info("Saving persona", {"persona_id": persona.id})
    try:
        filesystem.write_json(persona.storage_dir / "config.json", asdict(persona))
    except OSError as e:
        raise IdentityError("Failed to save persona") from e


async def remove(persona: Persona) -> None:
    """Delete the persona's storage directory."""
    logger.info("Removing persona storage", {"persona_id": persona.id})
    filesystem.delete_dir(persona.storage_dir)
