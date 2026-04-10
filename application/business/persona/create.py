"""Persona — creating a new persona."""

import uuid

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, paths, system
from application.core.data import Channel, Model, Persona
from application.core.exceptions import (
    ContextError,
    DiaryError,
    EngineConnectionError,
    IdentityError,
    PersonError,
    SecretStorageError,
    SkillError,
    UnsupportedOS,
)
from application.platform.asyncio_worker import Worker

from .delete import delete
from .wake import wake
from .write_diary import write_diary


async def create(
    name: str,
    thinking: Model,
    channel: Channel,
    frontier: Model | None = None,
) -> Outcome[dict]:
    """It gives birth to your persona with minimum but powerful initial abilities."""
    await bus.propose(
        "Creating persona", {"name": name, "thinking": thinking, "channel": channel, "frontier": frontier if frontier else None}
    )

    persona = None

    try:

        base_model = ""
        if thinking.provider is None:
            base_model = thinking.name
            thinking = Model(
                name=f"eternego-{uuid.uuid4()}",
                provider=thinking.provider,
                api_key=thinking.api_key,
                url=thinking.url
            )

        if base_model:
            await local_inference_engine.register(thinking.url, thinking.name, base_model)

        persona = Persona(
            name=name,
            thinking=thinking,
            base_model=base_model,
            version="v1",
            frontier=frontier,
            channels=[channel],
        )

        paths.create_directory(paths.home(persona.id))
        paths.create_directory(paths.history(persona.id))
        paths.create_directory(paths.destiny(persona.id))
        paths.create_directory(paths.training_set(persona.id))
        paths.create_directory(paths.workspace(persona.id))
        paths.create_directory(paths.notes(persona.id))
        paths.create_directory(paths.meanings(persona.id))

        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        phrase = system.generate_recovery_phrases()
        await system.save_phrases(persona, phrase)

        paths.add_routine(persona.id, "sleep", "00:00", "daily")

        paths.init_git(paths.diary(persona.id))
        outcome = await write_diary(persona)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast(
                "Persona creation failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        outcome = await wake(persona.id, Worker())
        if not outcome.success:
            await bus.broadcast("Persona creation failed", {"reason": outcome.message, "persona": persona})
            return outcome

        await bus.broadcast("Persona created", {"persona": persona})

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
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except EngineConnectionError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except SecretStorageError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except IdentityError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona identity files.")

    except PersonError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not set up person files.")

    except ContextError as e:
        await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "context", "error": str(e)})
        return Outcome(success=False, message="Could not set up initial context for the persona.")

    except SkillError as e:
        await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "skills", "error": str(e)})
        return Outcome(success=False, message="Could not assess default skills. The model may have returned an unexpected response — try again.")

    except DiaryError as e:
        await delete(persona)

        await bus.broadcast("Persona creation failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")
