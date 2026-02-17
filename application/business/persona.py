"""Persona — creation, migration, identity, learning, and lifecycle."""

from application.core import bus, agent, channels, gateways, memories, person, frontier, diary, system, external_llms, local_model, local_inference_engine, models, prompts, dna, instructions, skills, history, observations
from application.core.bus import Message
from application.core.data import Channel, Model, Persona, Thought
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, ExternalDataError, FrontierError,
    ExecutionError, DNAError, ChannelError,
)
from application.business import environment
from application.business.outcome import Outcome


async def agents() -> Outcome[dict]:
    """Return all personas."""
    await bus.propose("Listing personas", {})

    try:
        personas = await agent.personas()
        await bus.broadcast("Personas listed", {"count": len(personas)})
        return Outcome(success=True, message="", data={"personas": personas})
    except IdentityError as e:
        await bus.broadcast("List personas failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not list personas. Please check the persona data.")


async def find_by_channel(channel: Channel) -> Outcome[dict]:
    """Find the persona that owns the given channel."""
    outcome = await agents()
    if not outcome.success:
        return outcome
    personas = (outcome.data or {}).get("personas", [])
    for persona in personas:
        for ch in persona.channels or []:
            if channels.matches(ch, channel):
                return Outcome(success=True, message="", data={"persona": persona})
    return Outcome(success=False, message="No persona found for channel.", data=None)


async def create(
    name: str,
    model: str,
    channel_name: str,
    channel_credentials: dict,
    frontier_model: str | None = None,
    frontier_provider: str | None = None,
    frontier_credentials: dict | None = None,
) -> Outcome[dict]:
    """It gives birth to your persona with minimum but powerful initial abilities."""
    await bus.propose(
        "Creating persona", {"name": name, "model": model, "channel": channel_name, "frontier_model": frontier_model, "frontier_provider": frontier_provider}
    )

    try:
        channel = Channel(name=channel_name, credentials=channel_credentials)

        if not await channels.assert_receives(channel, "Welcome to Eternego!"):
            await bus.broadcast(
                "Persona creation failed", {"reason": "channel", "name": name, "channel": channel_name}
            )
            return Outcome(success=False, message=f"Could not connect to {channel_name}. Please check your credentials.")

        local_model_obj = Model(name=model)
        frontier_model_obj = None
        if frontier_model:
            frontier_model_obj = Model(
                name=frontier_model,
                provider=frontier_provider,
                credentials=frontier_credentials,
            )

        persona = await agent.initialize(name, local_model_obj, frontier_model_obj, channels=[channel])

        persona_model = models.generate_name(model, persona.id)
        await agent.embody(persona, local_model_obj, persona_model)
        await local_inference_engine.copy(model, persona_model)

        await agent.build(persona)
        await dna.make(persona)
        await history.start(persona)
        await instructions.give(persona)
        await skills.equip(persona)
        await person.bond(persona)

        if frontier_model_obj:
            await frontier.allow_escalation(persona)

        await agent.save_persona(persona)

        phrase = await system.generate_encryption_phrase(persona)

        await system.save_phrases(persona, phrase)

        await diary.open_for(persona)

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast(
                "Persona creation failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        await bus.broadcast(
            "Persona created", {"persona": persona}
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

    except IdentityError as e:
        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona identity files.")

    except PersonError as e:
        await bus.broadcast("Persona creation failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not set up person files.")

    except DiaryError as e:
        await bus.broadcast("Persona creation failed", {"reason": "diary", "error": str(e)})
        return Outcome(success=False, message="Could not save the persona diary.")


async def migrate(diary_path: str, phrase: str, model: str) -> Outcome[dict]:
    """It enables you to migrate your persona so nothing is ever lost."""
    await bus.propose("Migrating persona", {"diary_path": diary_path, "model": model})

    try:
        materials = await diary.open(diary_path, phrase)

        outcome = await environment.prepare(model)
        if not outcome.success:
            await bus.broadcast("Persona migration failed", {"reason": "environment"})
            return Outcome(success=False, message=outcome.message)

        persona = await agent.distill(materials)

        model_obj = Model(name=model)
        persona_model = models.generate_name(model, persona.id)
        await agent.embody(persona, model_obj, persona_model)
        await local_inference_engine.copy(model, persona_model)
        await agent.save_persona(persona)

        dna_structure = dna.read(persona)
        observed = await local_model.study(persona.model.name, dna_structure)
        await observations.effect(persona, observed)

        await system.save_phrases(persona, phrase)

        await diary.open_for(persona)

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast(
                "Persona migration failed", {"reason": "diary", "persona": persona}
            )
            return Outcome(success=False, message=outcome.message)

        verification = {}
        for ch in (persona.channels or []):
            verification[ch.name] = await channels.assert_receives(ch, "Welcome to Eternego!")

        await bus.broadcast("Persona migrated", {
            "persona": persona,
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

    except PersonError as e:
        await bus.broadcast("Persona migration failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during migration.")

    except DNAError as e:
        await bus.broadcast("Persona migration failed", {"reason": "dna", "error": str(e)})
        return Outcome(success=False, message="Could not read persona DNA. The diary may be from an older version.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona migration failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the local inference engine. Please make sure it is running.")

    except UnsupportedOS as e:
        await bus.broadcast("Persona migration failed", {"reason": "unsupported_os", "error": str(e)})
        return Outcome(success=False, message="Your operating system is not supported.")

    except SecretStorageError as e:
        await bus.broadcast("Persona migration failed", {"reason": "secret_storage", "error": str(e)})
        return Outcome(success=False, message="Could not access secure storage. Please check your system keyring is available.")


async def feed(persona: Persona, data: str, source: str) -> Outcome[dict]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    try:
        conversations = await external_llms.read(data, source)

        observation = await local_model.observe(persona.model.name, conversations)
        await observations.effect(persona, observation)

        await bus.broadcast("Persona fed", {
            "persona": persona,
            "source": source,
        })

        return Outcome(
            success=True,
            message="Persona fed successfully",
            data={"persona_id": persona.id},
        )

    except ExternalDataError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except IdentityError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not save observations to persona.")

    except PersonError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations to persona.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")


async def equip(persona: Persona, skill_path: str) -> Outcome[dict]:
    """It lets you equip your persona with new skills so it can do more for you."""
    await bus.propose("Equipping persona", {"persona": persona, "skill_path": skill_path})

    if not skill_path.endswith(".md"):
        await bus.broadcast("Persona equipping failed", {"reason": "invalid_format", "skill_path": skill_path})
        return Outcome(success=False, message="Skill must be a markdown (.md) file.")

    try:
        skill_file = await skills.shelve(persona, skill_path)

        observed = await skills.summarize(persona, skill_file)
        await observations.effect(persona, observed)

        await bus.broadcast("Persona equipped", {
            "persona": persona,
            "skill": skill_file.stem,
        })

        return Outcome(
            success=True,
            message="Skill equipped successfully",
            data={"persona_id": persona.id, "skill": skill_file.stem},
        )

    except IdentityError as e:
        await bus.broadcast("Persona equipping failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not equip the skill.")

    except PersonError as e:
        await bus.broadcast("Persona equipping failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations from skill.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona equipping failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not assess the skill. Please make sure the model is running.")


async def sense(persona: Persona, prompt: str, channel: Channel) -> Outcome[dict]:
    """It lets the persona sense a stimulus from a channel and process it."""
    await bus.propose(
        "Sensing", {"persona": persona, "channel": channel}
    )

    try:
        think = agent.given(persona, {"type": "stimulus", "role": "user", "content": prompt, "channel": channel.name})

        failed = False
        async for thought in think.reason():
            if thought.intent == "saying":
                await say(persona, thought, channel)
            elif thought.intent == "doing":
                if failed:
                    memories.agent(persona).remember({
                        "type": "act",
                        "tool_calls": thought.tool_calls,
                        "result": "Skipped — a previous tool call failed in this interaction.",
                    })
                else:
                    outcome = await act(persona, thought)
                    if not outcome.success:
                        failed = True
            elif thought.intent == "consulting":
                await escalate(persona, thought.content, channel)
            elif thought.intent == "reasoning":
                await bus.share("Reasoning", {"content": thought.content})

        await reflect(persona, channel)

        await bus.broadcast(
            "Sensed", {"persona": persona, "channel": channel}
        )

        return Outcome(
            success=True,
            message="Stimulus processed",
            data={"persona_id": persona.id},
        )

    except EngineConnectionError as e:
        await bus.broadcast(
            "Sensing failed",
            {"reason": "connection", "error": str(e)},
        )
        return Outcome(
            success=False,
            message="Could not connect to the inference engine. Please make sure it is running.",
        )


async def say(persona: Persona, thought: Thought, channel: Channel | None = None) -> Outcome[dict]:
    """It lets the persona express a thought through a channel."""
    await bus.propose(
        "Saying", {"persona": persona}
    )

    if not ([channel] if channel else (persona.channels or [])):
        await bus.broadcast("Saying failed", {"persona": persona})
        return Outcome(
            success=False,
            message="No channel to communicate the thought.",
            data={"persona_id": persona.id},
        )

    try:
        for channel in ([channel] if channel else (persona.channels or [])):
            await channels.send(channel, thought.content)
            memories.agent(persona).remember({
                "type": "communicated",
                "channel": channel.name,
                "content": thought.content,
            })
            await bus.broadcast("Said", {"persona": persona, "channel": channel})

        return Outcome(
            success=True,
            message="Thought expressed",
            data={"persona_id": persona.id},
        )

    except ChannelError as e:
        await bus.broadcast("Saying failed", {"persona": persona, "error": str(e)})
        return Outcome(
            success=False,
            message="Could not deliver the message. Please check the channel connection.",
            data={"persona_id": persona.id},
        )


async def act(persona: Persona, thought: Thought) -> Outcome[dict]:
    """It lets the persona act on the world by executing a tool call."""
    await bus.propose(
        "Acting", {"persona": persona, "tool": thought.tool_calls}
    )

    signals = await bus.ask(
        "Can I run this command?", {"tool_calls": thought.tool_calls}
    )

    authorized = any(
        isinstance(signal, Message)
        and signal.title == "Run command authorized"
        and signal.details.get("tool_calls") == thought.tool_calls
        for signal in signals
    )

    if not authorized:
        memories.agent(persona).remember({
            "type": "act",
            "tool_calls": thought.tool_calls,
            "result": "Rejected — the person declined to run this command.",
        })

        await bus.broadcast(
            "Acting rejected",
            {"persona": persona, "tool": thought.tool_calls},
        )

        return Outcome(
            success=False,
            message="Command rejected by the person.",
            data={"persona_id": persona.id},
        )

    try:
        result = await system.execute(thought.tool_calls)

        memories.agent(persona).remember({"type": "act", "tool_calls": thought.tool_calls, "result": result})

        await bus.broadcast(
            "Acted", {"persona": persona, "tool": thought.tool_calls}
        )

        return Outcome(
            success=True,
            message="Action executed",
            data={"persona_id": persona.id},
        )

    except ExecutionError as e:
        memories.agent(persona).remember({
            "type": "act",
            "tool_calls": thought.tool_calls,
            "result": f"Failed: {e}",
        })

        await bus.broadcast(
            "Acting failed",
            {"persona": persona, "tool": thought.tool_calls, "error": str(e)},
        )

        return Outcome(
            success=False,
            message="Command failed to execute.",
            data={"persona_id": persona.id},
        )

    except UnsupportedOS as e:
        memories.agent(persona).remember({
            "type": "act",
            "tool_calls": thought.tool_calls,
            "result": f"Failed: {e}",
        })

        await bus.broadcast(
            "Acting failed",
            {"persona": persona, "tool": thought.tool_calls, "error": str(e)},
        )

        return Outcome(
            success=False,
            message="Your operating system is not supported.",
            data={"persona_id": persona.id},
        )


async def escalate(persona: Persona, prompt: str, channel: Channel) -> Outcome[dict]:
    """It lets the persona escalate to a frontier model when the task exceeds its ability."""
    await bus.propose(
        "Escalating", {"persona": persona, "channel": channel}
    )

    try:
        observation = [{"role": "user", "content": prompt}]

        failed = False
        async for response in frontier.consulting(persona, prompt).reason():
            if response.intent == "saying":
                observation.append({"role": "assistant", "content": response.content})
                await say(persona, response, channel)
            elif response.intent == "doing":
                observation.append({"role": "assistant", "tool_calls": response.tool_calls})
                if failed:
                    memories.agent(persona).remember({
                        "type": "act",
                        "tool_calls": response.tool_calls,
                        "result": "Skipped — a previous tool call failed in this interaction.",
                    })
                else:
                    outcome = await act(persona, response)
                    if not outcome.success:
                        failed = True
            elif response.intent == "reasoning":
                # Reasoning is not observed. The agent should develop its own reasoning
                # for similar situations, not imitate the frontier's thought process.
                await bus.share("Reasoning", {"content": response.content})

        memories.agent(persona).remember({"type": "observation", "observation": observation})

        await bus.broadcast(
            "Escalated", {"persona": persona}
        )

        return Outcome(
            success=True,
            message="Escalation complete",
            data={"persona_id": persona.id},
        )

    except FrontierError as e:
        await bus.broadcast(
            "Escalation failed",
            {"reason": "frontier", "error": str(e)},
        )
        return Outcome(
            success=False,
            message="Could not reach the frontier model. Please check your credentials and connection.",
        )


async def reflect(persona: Persona, channel: Channel) -> Outcome[dict]:
    """It lets the persona reflect on what it learned from the interaction."""
    await bus.propose(
        "Reflecting", {"persona": persona, "channel": channel}
    )

    try:
        think = agent.given(persona, prompts.reflection())

        async for thought in think.reason():
            if thought.intent == "saying":
                await say(persona, thought, channel)
            elif thought.intent == "reasoning":
                await bus.share("Reasoning", {"content": thought.content})

        await bus.broadcast(
            "Reflected", {"persona": persona}
        )

        return Outcome(
            success=True,
            message="Reflection complete",
            data={"persona_id": persona.id},
        )

    except EngineConnectionError as e:
        await bus.broadcast(
            "Reflection failed",
            {"reason": "connection", "error": str(e)},
        )
        return Outcome(
            success=False,
            message="Could not connect to the inference engine for reflection.",
        )


async def predict(persona: Persona, channel: Channel) -> Outcome[dict]:
    """It lets the persona anticipate and act without external stimulus."""
    await bus.propose(
        "Predicting", {"persona": persona, "channel": channel}
    )

    try:
        think = agent.given(persona, prompts.prediction())

        async for thought in think.reason():
            if thought.intent == "saying":
                await say(persona, thought, channel)
            elif thought.intent == "reasoning":
                await bus.share("Reasoning", {"content": thought.content})

        await bus.broadcast(
            "Predicted", {"persona": persona}
        )

        return Outcome(
            success=True,
            message="Prediction complete",
            data={"persona_id": persona.id},
        )

    except EngineConnectionError as e:
        await bus.broadcast(
            "Prediction failed",
            {"reason": "connection", "error": str(e)},
        )
        return Outcome(
            success=False,
            message="Could not connect to the inference engine for prediction.",
        )


async def oversee(persona: Persona) -> Outcome[dict]:
    """It lets you look into your persona's mind — what it knows what it learned, and how it sees you."""
    await bus.propose("Overseeing persona", {"persona": persona})

    try:
        facts = await person.identified_by(persona)
        traits = await person.traits_toward(persona)
        agent_data = await agent.identity(persona)
        skill_list = await skills.names(persona)
        conversations = await history.entries(persona)

        await bus.broadcast("Persona overseen", {"persona": persona})

        return Outcome(
            success=True,
            message="Persona overview ready",
            data={
                "person": system.make_rows_traceable(facts, "pi"),
                "traits": system.make_rows_traceable(traits, "pt"),
                "agent": system.make_rows_traceable(agent_data["identity"], "pai")
                    + system.make_rows_traceable(agent_data["context"], "pc"),
                "skills": system.make_rows_traceable(skill_list, "sk"),
                "history": system.make_rows_traceable(conversations, "hist"),
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
                await person.delete_identity(persona, hash_part)
            elif prefix == "pt":
                await person.delete_trait(persona, hash_part)
            elif prefix == "pai":
                await agent.delete_identity(persona, hash_part)
            elif prefix == "pc":
                await agent.delete_context(persona, hash_part)
            elif prefix == "sk":
                await skills.delete(persona, hash_part)
            elif prefix == "hist":
                await history.delete(persona, hash_part)

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
        await diary.record(persona.storage_dir, phrase)

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


async def sleep(persona: Persona) -> Outcome[dict]:
    """It lets your persona rest, reflect, and grow stronger from everything it experienced."""
    await bus.propose("Sleeping", {"persona": persona})

    try:
        conversations = await history.recall(persona)
        if conversations:
            observed = await local_model.observe(persona.model.name, conversations)
            await observations.effect(persona, observed)

        synthesis = dna.assemble_synthesis(persona)
        if persona.frontier:
            new_dna = await frontier.respond(persona.frontier, synthesis)
        else:
            new_dna = await local_model.respond(persona.model.name, synthesis)
        await dna.evolve(persona, new_dna)

        prompt = await agent.sleep(persona)

        if persona.frontier:
            training_set = await frontier.respond(persona.frontier, prompt)
        else:
            training_set = await local_model.respond(persona.model.name, prompt)

        await agent.save_training_set(persona, training_set)

        old_model = persona.model.name
        new_model = models.generate_name(persona.base_model, persona.id)
        await local_inference_engine.fine_tune(persona.base_model, training_set, new_model)

        if not await local_inference_engine.check(new_model):
            await bus.broadcast("Sleep failed", {"reason": "fine_tune", "persona": persona})
            return Outcome(success=False, message="Fine-tuned model failed verification. Previous model is still available.")

        try:
            await local_inference_engine.delete(old_model)
        except EngineConnectionError:
            pass

        await agent.wake_up(persona, new_model)

        outcome = await write_diary(persona)
        if not outcome.success:
            await bus.broadcast("Sleep failed", {"reason": "diary", "persona": persona})
            return outcome

        await bus.broadcast("Slept", {
            "persona": persona,
            "model": new_model,
            "channels": [ch for ch in (persona.channels or [])],
        })

        return Outcome(
            success=True,
            message="Persona slept and grew stronger",
            data={"persona_id": persona.id, "model": new_model},
        )

    except IdentityError as e:
        await bus.broadcast("Sleep failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not process persona files during sleep.")

    except PersonError as e:
        await bus.broadcast("Sleep failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations during sleep.")

    except EngineConnectionError as e:
        await bus.broadcast("Sleep failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not connect to the inference engine. Please make sure it is running.")

    except FrontierError as e:
        await bus.broadcast("Sleep failed", {"reason": "frontier", "error": str(e)})
        return Outcome(success=False, message="Could not reach the frontier model. Please check your credentials and connection.")


async def start(persona: Persona) -> Outcome[dict]:
    """Open all channels for a persona and start listening."""
    await bus.propose("Starting gateway", {"persona": persona})

    if not (persona.channels or []):
        await bus.broadcast("Gateway start failed", {"persona": persona, "reason": "no_channels"})
        return Outcome(success=False, message="No channels configured for this persona.")

    try:
        for channel in persona.channels:
            async def on_message(text: str, ch=channel):
                outcome = await sense(persona, text, ch)
                if not outcome.success:
                    await channels.send(ch, outcome.message)

            gateway = channels.listen(persona, channel, on_message)
            gateways.of(persona).add(gateway)

        await bus.broadcast("Gateway started", {"persona": persona})

        return Outcome(success=True, message="Gateway started", data={"persona_id": persona.id})

    except ChannelError as e:
        await bus.broadcast("Gateway start failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))


async def stop(persona: Persona) -> Outcome[dict]:
    """Close all channels for a persona."""
    await bus.propose("Stopping gateway", {"persona": persona})

    if not gateways.of(persona).close_all():
        await bus.broadcast("Gateway stop failed", {"persona": persona, "reason": "not_running"})
        return Outcome(success=False, message="No active gateway for this persona.")

    await bus.broadcast("Gateway stopped", {"persona": persona})

    return Outcome(success=True, message="Gateway stopped", data={"persona_id": persona.id})
