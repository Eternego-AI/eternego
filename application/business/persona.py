"""Persona — creation, migration, identity, learning, and lifecycle."""

from application.core import bus, agent, person, frontier, diary, system, local_model, external_llms
from application.core.data import Channel, Model, Observation, Persona
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, ExternalDataError,
)
from application.business import environment, gateway
from application.business.outcome import Outcome


async def create(
    name: str,
    model: Model,
    channel: Channel,
    frontier_model: Model | None = None,
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

        persona = await agent.initialize(name, model, frontier_model, channels=[channel])

        await person.prepare_buckets(persona)
        await agent.prepare_buckets(persona)
        await agent.give_instructions(persona)
        await agent.equip_basic_skills(persona)

        if frontier_model:
            await frontier.allow_escalation(persona)

        await agent.save_persona(persona)

        phrase = await system.generate_encryption_phrase(persona)

        await system.save_phrases(persona, phrase)

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

    except (IdentityError, PersonError) as e:
        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona files.")

    except DiaryError as e:
        await bus.broadcast("Persona creation failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def migrate(diary_path: str, phrase: str, model: Model) -> Outcome[dict]:
    """It enables you to migrate your persona so nothing is ever lost."""
    await bus.propose("Migrating persona", {"diary_path": diary_path, "model": model.name})

    try:
        materials = await diary.open(diary_path, phrase)

        outcome = await environment.prepare(model.name)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "environment"})
            return Outcome(success=False, message=outcome.message)

        persona = await agent.distill(materials)

        persona.model = model
        await agent.save_persona(persona)

        await system.save_phrases(persona, phrase)

        await diary.open_for(persona)

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast(
                "Persona migration failed", {"reason": "diary", "persona_id": persona.id}
            )
            return Outcome(success=False, message=outcome.message)

        verification = {}
        for ch in (persona.channels or []):
            result = await gateway.verify_channel(ch)
            verification[ch.name] = result.success

        await bus.broadcast("Persona migrated", {
            "persona_id": persona.id,
            "name": persona.name,
            "verification": verification,
        })

        return Outcome(
            success=True,
            message="Persona migrated successfully",
            data={
                "persona_id": persona.id,
                "name": persona.name,
                "verification": verification,
            },
        )

    except DiaryError as e:
        await bus.broadcast("Persona migration failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not restore from diary. Please check the file path and recovery phrase.")

    except IdentityError as e:
        await bus.broadcast("Persona migration failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not restore persona. The diary data may be corrupted.")

    except UnsupportedOS as e:
        await bus.broadcast("Persona migration failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Persona migration failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona_id": persona.id, "source": source})

    try:
        conversations = await external_llms.read(data, source)

        observations = await local_model.digest(persona.model.name, conversations)

        outcome = await grow(persona, observations)
        if not outcome.success:
            await bus.broadcast("Persona feeding failed", {"reason": "grow", "persona_id": persona.id})
            return outcome

        await bus.broadcast("Persona fed", {
            "persona_id": persona.id,
            "source": source,
        })

        return outcome

    except ExternalDataError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")


async def grow(persona: Persona, observations: Observation) -> Outcome[dict]:
    """It lets your persona grow from what it observed."""
    await bus.propose("Growing persona", {"persona_id": persona.id})

    try:
        await person.add_facts(persona, observations.facts)
        await person.add_traits(persona, observations.traits)
        await agent.learn(persona, observations.context)

        await bus.broadcast("Persona grew", {"persona_id": persona.id})

        return Outcome(
            success=True,
            message="Persona grew successfully",
            data={"persona_id": persona.id},
        )

    except (IdentityError, PersonError) as e:
        await bus.broadcast("Persona growth failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not save observations to persona.")


async def write_diary(persona: Persona) -> Outcome[dict]:
    """It preserves your persona's life so it survives across time, hardware, and changes."""
    await bus.propose("Saving diary", {"persona_id": persona.id})

    try:
        phrase = await system.get_phrases(persona)
        await diary.record(persona.storage_dir, phrase)

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
