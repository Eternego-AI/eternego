"""History — long-term conversation history for a persona."""

from application.platform import logger, filesystem, crypto, datetimes
from application.core import local_model, observations, transcripts
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError, IdentityError


async def start(persona: Persona) -> None:
    """Create the history directory for a new persona."""
    logger.info("Starting history", {"persona_id": persona.id})
    try:
        filesystem.ensure_dir(persona.storage_dir / "history")
    except OSError as e:
        raise IdentityError("Failed to start history") from e


async def entries(persona: Persona) -> list[str]:
    """Read the agent's conversation history names."""
    logger.info("Reading history entries", {"persona_id": persona.id})
    try:
        names = []
        history_dir = persona.storage_dir / "history"
        if history_dir.exists():
            for file in sorted(history_dir.glob("*")):
                names.append(file.stem)
        return names
    except OSError as e:
        raise IdentityError("Failed to read history entries") from e


async def recall(persona: Persona) -> str:
    """Read all history files and return concatenated conversations."""
    logger.info("Recalling history", {"persona_id": persona.id})
    try:
        parts = []
        history_dir = persona.storage_dir / "history"
        if history_dir.exists():
            for file in sorted(history_dir.glob("*")):
                parts.append(filesystem.read(file))
        return "\n\n---\n\n".join(parts)
    except OSError as e:
        raise IdentityError("Failed to read history") from e


async def delete(persona: Persona, hash_part: str) -> None:
    """Remove a conversation file from history by its name hash."""
    logger.info("Deleting history entry", {"persona_id": persona.id, "hash": hash_part})
    try:
        history_dir = persona.storage_dir / "history"
        for file in history_dir.glob("*"):
            if crypto.generate_unique_id(file.stem) == hash_part:
                filesystem.delete(file)
                return
        raise IdentityError("History entry not found or already removed")
    except OSError as e:
        raise IdentityError("Failed to delete history entry") from e


async def consolidate(persona: Persona, knowledge: dict, transcript: str) -> None:
    """Cluster a conversation transcript by topic, extract observations, and commit to long-term history."""
    logger.info("Consolidating to history", {"persona_id": persona.id})

    if not transcript:
        return

    try:
        try:
            clusters = await local_model.cluster(persona.model.name, transcript)
        except EngineConnectionError:
            clusters = []

        if not clusters:
            all_entries = transcripts.as_list(transcript)
            clusters = [{"topic": "conversation", "indices": [e["index"] for e in all_entries]}]

        stamp = datetimes.date_stamp(datetimes.now())

        for entry in clusters:
            topic = entry.get("topic", "conversation")
            indices = entry.get("indices", [])
            cluster_text = transcripts.extract(transcript, indices)
            if not cluster_text:
                continue

            path = persona.storage_dir / "history" / f"{stamp}-{topic}.md"
            if path.exists():
                filesystem.append(path, f"\n\n{cluster_text}")
            else:
                filesystem.write(path, cluster_text)

            try:
                observed = await local_model.observe(persona.model.name, cluster_text, **knowledge)
                await observations.effect(persona, observed)
            except EngineConnectionError:
                logger.info("Skipping observation for cluster", {"topic": topic})

    except OSError as e:
        raise IdentityError("Failed to write history during consolidation") from e


