"""Persona — preserving a persona's life in an encrypted diary."""

from application.business.outcome import Outcome
from application.core import bus, paths, system
from application.core.data import Persona
from application.core.exceptions import DiaryError, SecretStorageError, UnsupportedOS


async def write_diary(persona: Persona) -> Outcome[dict]:
    """It preserves your persona's life so it survives across time, hardware, and changes."""
    await bus.propose("Saving diary", {"persona": persona})

    try:
        phrase = await system.get_phrases(persona)
        archive = paths.zip_home(persona.id)
        encrypted_archive = paths.encrypt(archive, await system.persona_key(phrase, persona.id))
        diary_path = paths.diary(persona.id)
        diary_filename = f"{persona.id}.diary"
        paths.save_as_binary(diary_path / diary_filename, encrypted_archive)
        paths.commit_diary(persona.id, diary_path)

        await bus.broadcast("Diary saved", {"persona": persona})

        return Outcome(success=True, message="Diary saved successfully", data={
            "diary_path": str(diary_path / diary_filename),
        })

    except UnsupportedOS as e:
        await bus.broadcast("Diary failed", {"reason": "unsupported_os", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Diary failed", {"reason": "secret_storage", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except DiaryError as e:
        await bus.broadcast("Diary failed", {"reason": "diary", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")
