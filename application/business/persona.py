"""Persona — creation, migration, identity, learning, and lifecycle."""

from application.core import bus, identity, diary, instructions, skills, local_model
from application.core.data import Channel, Model, Persona
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError, DiaryError,
)
from application.business import gateway
from application.business.outcome import Outcome


async def create(
    name: str,
    model: Model,
    channel: Channel,
    frontier: Model | None = None,
) -> Outcome[dict]:
    """It gives birth to your persona with minimum but powerful initial abilities."""
    await bus.propose(
        "Creating persona", {"name": name, "model": model.name, "channel": channel.name}
    )

    try:
        outcome = await gateway.verify_channel(channel)
        if not outcome.success:
            await bus.broadcast(
                "Persona creation failed", {"reason": "channel", "name": name}
            )
            return Outcome(success=False, message=outcome.message)

        persona = await identity.initialize(name, model, frontier, channels=[channel])

        await identity.prepare_person_identity_bucket(persona)
        await identity.prepare_person_traits_bucket(persona)
        await identity.prepare_persona_identity_bucket(persona)
        await identity.prepare_persona_context_bucket(persona)
        await identity.prepare_training_material_bucket(persona)

        await identity.instructions(persona, instructions.basic_instructions(frontier))
        await identity.skills(persona, skills.basic_skills())

        await identity.save_persona(persona)

        phrase = await local_model.generate_encryption_phrase(persona)

        await identity.save_phrases(persona, phrase)

        await diary.open_for(persona)

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast(
                "Persona creation failed", {"reason": "diary", "persona_id": persona.id}
            )
            return Outcome(success=False, message=outcome.message)

        await bus.broadcast(
            "Persona created", {"persona_id": persona.id, "name": persona.name}
        )

        return Outcome(
            success=True,
            message="Persona created successfully",
            data={
                "persona_id": persona.id,
                "name": persona.name,
                "recovery_phrase": phrase,
            },
        )

    except UnsupportedOS as e:
        await bus.broadcast("Persona creation failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona creation failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except SecretStorageError as e:
        await bus.broadcast("Persona creation failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except DiaryError as e:
        await bus.broadcast("Persona creation failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def write_diary(persona: Persona) -> Outcome[dict]:
    """It preserves your persona's life so it survives across time, hardware, and changes."""
    await bus.propose("Saving diary", {"persona_id": persona.id})

    try:
        phrase = await identity.get_phrases(persona)
        await diary.record(identity.memory_path(persona), phrase)

        await bus.broadcast("Diary saved", {"persona_id": persona.id})

        return Outcome(success=True, message="Diary saved successfully")

    except UnsupportedOS as e:
        await bus.broadcast("Diary failed", {"reason": "unsupported_os", "persona_id": persona.id, "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Diary failed", {"reason": "secret_storage", "persona_id": persona.id, "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except DiaryError as e:
        await bus.broadcast("Diary failed", {"reason": "diary", "persona_id": persona.id, "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")
