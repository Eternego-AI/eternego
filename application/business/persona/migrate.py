"""Persona — migrating a persona from a diary backup."""

from pathlib import Path

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, paths, system
from application.core.data import Model, Persona
from application.core.exceptions import (
    DiaryError,
    EngineConnectionError,
    IdentityError,
    PersonError,
    SecretStorageError,
    UnsupportedOS,
)
from application.platform.asyncio_worker import Worker

from .delete import delete
from .find import find
from .wake import wake
from .write_diary import write_diary


async def migrate(
    diary_path: str,
    phrase: str,
    thinking: Model,
) -> Outcome[dict]:
    """It enables you to migrate your persona so nothing is ever lost."""
    await bus.propose("Migrating persona", {"diary_path": diary_path, "thinking": thinking})

    persona = None

    try:
        temp_path = Path(diary_path)
        persona_id = temp_path.stem
        archive = paths.decrypt(temp_path, await system.persona_key(phrase, persona_id))
        staging = paths.unzip(persona_id, archive)

        paths.copy_recursively(staging, paths.home(persona_id))
        paths.delete_recursively(staging)

        outcome = await find(persona_id)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "identity"})
            return Outcome(success=False, message=outcome.message)

        persona = outcome.data["persona"]

        persona.thinking = thinking

        if thinking.provider is None:
            persona.base_model = thinking.name
            persona.thinking = Model(name=f"eternego-{persona.id}")
            await local_inference_engine.register(persona.thinking.name, thinking.name)

        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        await system.save_phrases(persona, phrase)

        outcome = await write_diary(persona)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast(
                "Persona migration failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        outcome = await wake(persona.id, Worker())
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": outcome.message, "persona": persona})
            return outcome

        await bus.broadcast("Persona migrated", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona migrated successfully",
            data={
                "persona_id": persona.id,
                "name": persona.name,
            },
        )

    except DiaryError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not restore from diary. Please check the file path and recovery phrase.")

    except IdentityError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not restore persona. The diary data may be corrupted.")

    except PersonError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during migration.")

    except EngineConnectionError as e:
        if persona is not None:
            await delete(persona)

        await bus.broadcast("Persona migration failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except UnsupportedOS as e:
        if persona is not None:
            await delete(persona)
        await bus.broadcast("Persona migration failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        if persona is not None:
            await delete(persona)
        await bus.broadcast("Persona migration failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")
