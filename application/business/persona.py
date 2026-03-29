"""Persona — creation, migration, identity, learning, and lifecycle."""
from pathlib import Path

from application.core import bus, channels, gateways, frontier, system, agents, \
    local_model, local_inference_engine, paths
from application.core.data import Channel, Message, Model, Persona
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, FrontierError,
    DNAError, SkillError, ChannelError, ContextError, MindError,
)
from application.business import environment
from application.business.outcome import Outcome
from application.platform import logger


async def get_list() -> Outcome[dict]:
    """Return all personas."""
    await bus.propose("Listing personas", {})

    try:
        root = paths.personas_home()
        if not root.exists():
            await bus.broadcast("No personas found", {})
            return Outcome(success=False, message="No personas found. Create one to get started.", data={"personas": []})
        try:
            persona_ids = [d.name for d in root.iterdir() if d.is_dir() and (d / "home" / "config.json").exists()]
        except OSError as e:
            raise IdentityError("Failed to list personas") from e
        personas = []
        for persona_id in persona_ids:
            try:
                outcome = await find(persona_id)
                if outcome.success:
                    personas.append(outcome.data["persona"])
            except (IdentityError, OSError):
                continue

        await bus.broadcast("Personas listed", {"count": len(personas)})
        return Outcome(success=True, message="", data={"personas": personas})
    except IdentityError as e:
        await bus.broadcast("List personas failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not list personas. Please check the persona data.")


async def find(persona_id: str) -> Outcome[dict]:
    """Find a persona by its ID."""
    await bus.propose("Finding persona", {"persona_id": persona_id})
    try:
        identity_path = paths.persona_identity(persona_id)
        if not identity_path.exists():
            await bus.broadcast("Persona not found", {"persona_id": persona_id})
            return Outcome(success=False, message="Persona not found.")

        raw_persona = paths.read_json(identity_path)
        persona = Persona(
            id=raw_persona["id"],
            name=raw_persona["name"],
            model=Model(**raw_persona["model"]),
            version=raw_persona.get("version"),
            base_model=raw_persona.get("base_model", raw_persona["model"]["name"]),
            birthday=raw_persona.get("birthday"),
            frontier=Model(**raw_persona["frontier"]) if raw_persona.get("frontier") else None,
            channels=[Channel(**n) for n in raw_persona["channels"]] if raw_persona.get("channels") else None,
        )

        await bus.broadcast("Persona found", {"persona": persona})
        return Outcome(success=True, message="", data={"persona": persona})
    except IdentityError as e:
        await bus.broadcast("Persona not found", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message="Persona not found.")


async def loaded(persona_id: str) -> Outcome[dict]:
    """Return the live persona from the in-process registry."""
    await bus.propose("Getting loaded persona", {"persona_id": persona_id})
    try:
        p = agents.find(persona_id)
        return Outcome(success=True, message="", data={"persona": p})
    except MindError as e:
        await bus.broadcast("Loaded persona not found", {"persona_id": persona_id})
        return Outcome(success=False, message=str(e))


async def mind(persona_id: str) -> Outcome[dict]:
    """Return all signals currently in the persona's mind, sorted by time."""
    await bus.propose("Getting persona mind", {"persona_id": persona_id})
    persona = await loaded(persona_id)
    if not persona.success:
        return persona
    try:
        signals = agents.persona(persona.data["persona"]).read()
        await bus.broadcast("Persona mind loaded", {"persona": persona})
        return Outcome(success=True, message="", data={
            "signals": [
                {"event": s.event, "content": s.content, "created_at": s.created_at.isoformat()}
                for s in signals
            ]
        })
    except MindError as e:
        await bus.broadcast("Reading persona mind failed", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def conversation(persona_id: str) -> Outcome[dict]:
    """Return the conversation history for a persona."""
    await bus.propose("Reading conversation", {"persona_id": persona_id})
    try:
        messages = paths.read_jsonl(paths.conversation(persona_id))
        await bus.broadcast("Conversation read", {"persona_id": persona_id})
        return Outcome(success=True, message="", data={"messages": messages})
    except Exception as e:
        await bus.broadcast("Conversation read failed", {"persona_id": persona_id, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def running() -> Outcome[dict]:
    """Return all currently running personas."""
    return Outcome(success=True, message="", data={"personas": agents.personas()})


async def delete(persona: Persona) -> Outcome[dict]:
    """Delete a persona and all its data."""
    await bus.propose("Deleting persona", {"persona": persona})
    try:
        paths.delete_recursively(paths.home(persona.id))
        if await local_inference_engine.check(persona.model.name):
            await local_inference_engine.delete(persona.model.name)
        await bus.broadcast("Persona deleted", {"persona": persona})
        return Outcome(success=True, message="Persona deleted successfully")
    except IdentityError as e:
        await bus.broadcast("Persona deletion failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not delete persona. Please check the persona data.")
    except EngineConnectionError as e:
        await bus.broadcast("Persona deletion failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine to delete the model. Please make sure it is running.")

async def create(
    name: str,
    model: str,
    channel_type: str,
    channel_credentials: dict,
    frontier_model: str | None = None,
    frontier_provider: str | None = None,
    frontier_credentials: dict | None = None,
) -> Outcome[dict]:
    """It gives birth to your persona with minimum but powerful initial abilities."""
    await bus.propose(
        "Creating persona", {"name": name, "model": model, "channel": channel_type, "frontier_model": frontier_model, "frontier_provider": frontier_provider}
    )

    if not local_inference_engine.is_supported(model):
        return Outcome(success=False, message=f"'{model}' is not a supported base model. Please choose from the supported models.")

    persona = None

    try:
        channel = Channel(type=channel_type, credentials=channel_credentials)

        frontier_model_obj = None
        if frontier_model:
            frontier_model_obj = Model(
                name=frontier_model,
                provider=frontier_provider,
                credentials=frontier_credentials,
            )
        persona = Persona(
            name=name,
            model=Model(name=model),
            version="v1",
            frontier=frontier_model_obj,
            channels=[channel],
        )
        persona.base_model = model
        persona.model = Model(name=f"eternego-{persona.id}")

        await local_inference_engine.register(persona.model.name, model)

        paths.create_directory(paths.home(persona.id))
        paths.create_directory(paths.history(persona.id))
        paths.create_directory(paths.destiny(persona.id))
        paths.create_directory(paths.training_set(persona.id))
        paths.create_directory(paths.workspace(persona.id))
        paths.create_directory(paths.notes(persona.id))
        paths.create_directory(paths.meanings(persona.id))

        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)
        paths.save_as_string(paths.person_identity(persona.id), f"The person's timezone is {system.timezone()}.")

        phrase = system.generate_recovery_phrases()
        await system.save_phrases(persona, phrase)

        paths.add_routine(persona.id, "sleep", "00:00", "daily", system.timezone())

        paths.init_git(paths.diary(persona.id))
        outcome = await write_diary(persona)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast(
                "Persona creation failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        from application.platform.asyncio_worker import Worker
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


async def migrate(diary_path: str, phrase: str, model: str) -> Outcome[dict]:
    """It enables you to migrate your persona so nothing is ever lost."""
    await bus.propose("Migrating persona", {"diary_path": diary_path, "model": model})

    if not local_inference_engine.is_supported(model):
        return Outcome(success=False, message=f"'{model}' is not a supported base model. Please choose from the supported models.")

    persona = None

    try:
        temp_path = Path(diary_path)
        persona_id = temp_path.stem
        archive = paths.decrypt(temp_path, await system.persona_key(phrase, persona_id))
        staging = paths.unzip(persona_id, archive)

        outcome = await environment.prepare(model)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "environment"})
            return Outcome(success=False, message=outcome.message)

        paths.copy_recursively(staging, paths.home(persona_id))
        paths.delete_recursively(staging)

        outcome = await find(persona_id)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "identity"})
            return Outcome(success=False, message=outcome.message)

        persona = outcome.data["persona"]
        persona.base_model = model
        persona.model = Model(name=f"eternego-{persona.id}")

        await local_inference_engine.register(persona.model.name, model)

        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        await system.save_phrases(persona, phrase)

        outcome = await write_diary(persona)
        if not outcome.success:
            await delete(persona)
            await bus.broadcast(
                "Persona migration failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        from application.platform.asyncio_worker import Worker
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


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    try:
        messages = await frontier.read(data, source)
        await agents.persona(persona).learn(messages)

        await bus.broadcast("Persona fed", {"persona": persona, "source": source})
        return Outcome(
            success=True,
            message="Persona fed successfully",
            data={"persona_id": persona.id},
        )

    except FrontierError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")


async def oversee(persona: Persona) -> Outcome[dict]:
    """It lets you look into your persona's mind — what it knows what it learned, and how it sees you."""
    await bus.propose("Overseeing persona", {"persona": persona})

    try:
        facts = paths.lines(paths.person_identity(persona.id))
        traits = paths.lines(paths.person_traits(persona.id))
        wish_list = paths.lines(paths.wishes(persona.id))
        struggle_list = paths.lines(paths.struggles(persona.id))
        persona_context = paths.lines(paths.persona_trait(persona.id))
        histories = paths.md_files(paths.history(persona.id))
        destinies = paths.md_files(paths.destiny(persona.id))

        await bus.broadcast("Persona overseen", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona overview ready",
            data={
                "person": system.make_rows_traceable(facts, "pi"),
                "traits": system.make_rows_traceable(traits, "pt"),
                "struggles": system.make_rows_traceable(struggle_list, "ps"),
                "wishes": system.make_rows_traceable(wish_list, "wi"),
                "context": system.make_rows_traceable(persona_context, "pc"),
                "history": system.make_rows_traceable([history_path.name for history_path in histories], "hist"),
                "destiny": system.make_rows_traceable([destiny_path.name for destiny_path in destinies], "dest"),
            },
        )

    except IdentityError as e:
        await bus.broadcast("Persona oversight failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not read agent data.")

    except PersonError as e:
        await bus.broadcast("Persona oversight failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not read person data.")


async def control(persona: Persona, entry_ids: list[str]) -> Outcome[dict]:
    """It gives you full control over what your persona knows — you always have the final say."""
    await bus.propose("Controlling persona", {"persona": persona, "count": len(entry_ids)})

    try:
        for entry_id in entry_ids:
            prefix, hash_part = entry_id.split("-", 1)

            if prefix == "pi":
                paths.delete_entry(paths.person_identity(persona.id), hash_part)
            elif prefix == "pt":
                paths.delete_entry(paths.person_traits(persona.id), hash_part)
            elif prefix == "pc":
                paths.delete_entry(paths.persona_trait(persona.id), hash_part)
            elif prefix == "hist":
                paths.find_and_delete_file(paths.history(persona.id), hash_part)
            elif prefix == "dest":
                paths.find_and_delete_file(paths.destiny(persona.id), hash_part)
            elif prefix == "wi":
                paths.delete_entry(paths.wishes(persona.id), hash_part)
            elif prefix == "ps":
                paths.delete_entry(paths.struggles(persona.id), hash_part)

        await bus.broadcast("Persona controlled", {"persona": persona, "removed": len(entry_ids)})

        return Outcome(
            success=True,
            message="Entries removed successfully",
            data={"removed": len(entry_ids)},
        )

    except ValueError:
        await bus.broadcast("Persona control failed", {"reason": "invalid_id", "persona": persona})
        return Outcome(success=False, message="Invalid entry ID format.")

    except IdentityError as e:
        await bus.broadcast("Persona control failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not remove agent entry. It may have been modified or already deleted.")

    except PersonError as e:
        await bus.broadcast("Persona control failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not remove person entry. It may have been modified or already deleted.")


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

        return Outcome(success=True, message="Diary saved successfully")

    except UnsupportedOS as e:
        await bus.broadcast("Diary failed", {"reason": "unsupported_os", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Diary failed", {"reason": "secret_storage", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")

    except DiaryError as e:
        await bus.broadcast("Diary failed", {"reason": "diary", "persona": persona, "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def connect(persona: Persona, channel: Channel) -> Outcome:
    """Open a connection for a channel and register it."""
    await bus.propose("Connecting channel", {"persona": persona, "channel": channel})
    try:
        if gateways.of(persona).has_channel(channel):
            await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
            return Outcome(success=True, message="")

        if channel.type == "web":
            gateways.of(persona).add(channel, lambda: None)
        else:
            async def on_message(message: Message) -> Outcome:
                if channel.verified_at is not None:
                    return await hear(persona, message)

                outcome = await pair(persona, message.channel)
                if not outcome.success:
                    await channels.send(message.channel, outcome.message)
                else:
                    code = outcome.data["pairing_code"]
                    await channels.send(
                        message.channel,
                        f"Your pairing code is: {code}\n\nRun: eternego pair {code}\n\nThis code expires in 10 minutes.",
                    )
                return outcome

            connection = channels.keep_open(persona, channel, on_message)
            gateways.of(persona).add(channel, connection)

        await bus.broadcast("Channel connected", {"persona": persona, "channel": channel})
        return Outcome(success=True, message="")
    except ChannelError as e:
        await bus.broadcast("Channel connection failed", {"persona": persona, "channel": channel, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def disconnect(persona: Persona, channel: Channel) -> Outcome:
    """Close a channel connection for a persona."""
    await bus.propose("Disconnecting channel", {"persona": persona, "channel": channel})
    stop = gateways.of(persona).remove(channel)
    if stop:
        stop()
    await bus.broadcast("Channel disconnected", {"persona": persona, "channel": channel})
    return Outcome(success=True, message="")



async def pair(persona: Persona, channel: Channel) -> Outcome[dict]:
    """Generate a pairing code so the person can verify a new channel."""
    await bus.propose("Pairing channel", {"persona": persona, "channel": channel})

    if channel.verified_at is not None:
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "already_verified"})
        return Outcome(success=False, message="This channel is already verified.")

    if not any(ch.type == channel.type for ch in (persona.channels or [])):
        await bus.broadcast("Channel pairing failed", {"persona": persona, "reason": "not_belonging"})
        return Outcome(success=False, message="This channel does not belong to this persona.")

    code = agents.pair(persona, channel)
    await bus.broadcast("Channel pairing started", {"persona": persona, "channel": channel})
    return Outcome(success=True, message="Pairing code generated.", data={"pairing_code": code})


async def hear(persona: Persona, message: Message) -> Outcome[dict]:
    """Receive a message, write to conversation, trigger the mind tick."""
    from application.core.brain.data import Signal, SignalEvent
    from application.core.brain import situation
    from application.core import paths
    from application.platform import datetimes
    await bus.propose("Hearing", {"persona": persona, "channel": message.channel})
    try:
        if agents.persona(persona).current_situation is situation.sleep:
            await bus.broadcast("Heard", {"persona": persona})
            return Outcome(success=True, message="", data={"response": f"{persona.name} is sleeping."})

        paths.append_jsonl(paths.conversation(persona.id), {
            "role": "person",
            "content": message.content,
            "channel": message.channel.type if message.channel else "",
            "time": datetimes.iso_8601(datetimes.now()),
        })

        signal = Signal(
            id=f"{message.channel.type}-{message.channel.name}-{message.id}" if message.channel else message.id,
            event=SignalEvent.heard,
            content=message.content,
            channel_type=message.channel.type if message.channel else "",
            channel_name=message.channel.name if message.channel else "",
            message_id=message.id,
        )
        agents.persona(persona).trigger(signal)
        await bus.broadcast("Heard", {"persona": persona})
        return Outcome(success=True, message="")
    except MindError as e:
        await bus.broadcast("Hearing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")



async def query(persona: Persona, messages) -> Outcome[dict]:
    """Answer a direct query using the local model — no pipeline, no memory."""
    from application.core.brain import situation
    from application.core import local_model

    await bus.propose("Querying", {"persona": persona})
    try:
        if agents.persona(persona).current_situation is situation.sleep:
            await bus.broadcast("Queried", {"persona": persona})
            return Outcome(success=True, message="", data={"response": f"{persona.name} is sleeping."})

        ego = agents.persona(persona)

        response = await local_model.chat(persona.model.name, [
            {"role": "system", "content": ego.identity()},
            messages,
        ])

        await bus.broadcast("Queried", {"persona": persona})
        return Outcome(success=True, message="", data={"response": response})
    except MindError as e:
        await bus.broadcast("Query failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")


async def live(persona: Persona, dt) -> Outcome[dict]:
    """Check for due destiny entries, archive them, and notify the persona."""
    import uuid
    from application.core.brain.data import Signal, SignalEvent, Perception
    from application.platform import filesystem

    await bus.propose("Checking todos", {"persona": persona})
    try:
        due = paths.due_destiny_entries(persona.id, dt)
        if not due:
            await bus.broadcast("No todos due", {"persona": persona})
            return Outcome(success=True, message="Nothing due.")

        notifications = []
        for filepath, content in due:
            paths.add_history_entry(persona.id, filepath.stem, content)
            filesystem.delete(filepath)
            notifications.append(content)

        signal = Signal(
            id=str(uuid.uuid4()),
            event=SignalEvent.nudged,
            content="Due now:\n" + "\n---\n".join(notifications),
        )
        from application.platform import datetimes
        perception = Perception(impression=f"Due at {datetimes.iso_8601(datetimes.now())}", thread=[signal])
        agents.persona(persona).incept(perception)

        await bus.broadcast("Todos checked", {"persona": persona, "due": len(due)})
        return Outcome(success=True, message=f"{len(due)} entries due.")
    except MindError as e:
        await bus.broadcast("Todos check failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def nap(persona: Persona) -> Outcome[dict]:
    """Quick stop — clear gateways, force-stop thinking, unload."""
    await bus.propose("Napping", {"persona": persona})

    agent = agents.persona(persona)
    try:
        gateways.of(persona).clear()
        await agent.stop()
        agent.unload()

        await bus.broadcast("Persona napping", {"persona": persona})
        return Outcome(success=True, message="Nap complete.")

    except Exception as e:
        agent.unload()
        await bus.broadcast("Nap failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Nap failed unexpectedly.")


async def sleep(persona: Persona) -> Outcome[dict]:
    """Put a persona to sleep — learn from experience, grow, write diary, then wake refreshed."""
    await bus.propose("Sleeping", {"persona": persona})

    agent = agents.persona(persona)
    worker = agent.worker
    try:
        from application.core.brain import situation

        agent.current_situation = situation.sleep
        await agent.settle()

        await agent.learn_from_experience()

        grow_outcome = await grow(persona)
        if not grow_outcome.success:
            logger.warning("Growing on sleep failed", {"persona": persona, "error": grow_outcome.message})

        outcome = await write_diary(persona)
        if not outcome.success:
            logger.error("Writing diary on sleep failed", {"persona": persona, "error": outcome.message})

        gateways.of(persona).clear()
        agent.unload()
        await wake(persona.id, worker)

        await bus.broadcast("Persona asleep", {"persona": persona})
        return Outcome(success=True, message="Sleep complete.")

    except (DNAError, EngineConnectionError) as e:
        gateways.of(persona).clear()
        agent.unload()
        await wake(persona.id, worker)
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
    except Exception as e:
        gateways.of(persona).clear()
        agent.unload()
        await wake(persona.id, worker)
        await bus.broadcast("Sleep failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Sleep failed unexpectedly.")


async def grow(persona: Persona) -> Outcome[dict]:
    """Generate training pairs from existing DNA and fine-tune the persona's model."""
    await bus.propose("Growing", {"persona": persona})
    try:
        import json
        from application.platform import OS

        dna = paths.read(paths.dna(persona.id))
        if not dna:
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="No DNA to grow from.", data={"dna": False, "finetune": False})

        if persona.frontier:
            try:
                all_pairs = await frontier.generate_training_set(persona.frontier, dna)
            except Exception:
                all_pairs = await local_model.generate_training_set(persona.model.name, dna)
        else:
            all_pairs = await local_model.generate_training_set(persona.model.name, dna)

        training_set = json.dumps({"training_pairs": all_pairs}, indent=2)
        paths.add_training_set(persona.id, training_set)

        vram = OS.gpu_vram_gb()
        if vram is None:
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="Fine-tuning skipped — no GPU detected.", data={"dna": True, "finetune": False})

        hardware = local_inference_engine.models()
        model_info = next((m for m in hardware if m["name"] == persona.base_model), None)
        if model_info is not None and not model_info["fits"]:
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="Fine-tuning skipped — insufficient VRAM.", data={"dna": True, "finetune": False})

        await local_inference_engine.fine_tune(persona.base_model, training_set, persona.model.name, persona.id)

        if not await local_inference_engine.check(persona.model.name):
            raise DNAError("Fine-tuned model failed verification — previous model is still active")

        paths.clear(paths.person_traits(persona.id))

        await bus.broadcast("Grown", {"persona": persona})
        return Outcome(success=True, message="Grow complete.")

    except (DNAError, EngineConnectionError) as e:
        await bus.broadcast("Grow failed", {"reason": "fine_tune", "persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def wake(persona_id: str, worker) -> Outcome[dict]:
    """Wake a persona — find, open gateways, construct ego, register."""
    await bus.propose("Waking persona", {"persona_id": persona_id})

    outcome = await find(persona_id)
    if not outcome.success:
        await bus.broadcast("Wake failed", {"persona_id": persona_id, "reason": "not_found"})
        return outcome

    agent = outcome.data["persona"]

    if not (agent.channels or []):
        await bus.broadcast("Wake failed", {"persona": agent, "reason": "no_channels"})
        return Outcome(success=False, message="No channels configured for this persona.")

    for channel in (agent.channels or []):
        outcome = await connect(agent, channel)
        if not outcome.success:
            await bus.broadcast("Wake failed", {"persona": agent, "error": outcome.message})
            return outcome

    from application.core.brain.mind import meanings
    from application.core.brain import situation

    all_meanings = meanings.built_in(agent) + meanings.specific_to(agent)
    ego = agents.Ego(agent, all_meanings, worker, situation.wake)
    agents.register(agent, ego)

    await bus.broadcast("Persona awake", {"persona": agent})
    return Outcome(success=True, message="Persona awake", data={"persona_id": agent.id})
