"""Persona — creation, migration, identity, learning, and lifecycle."""

from application.core import bus, agent, person, frontier, diary, system, external_llms, prompts
from application.core.bus import Message
from application.core.data import Channel, Model, Observation, Persona, Thought
from application.core.exceptions import (
    UnsupportedOS, EngineConnectionError, SecretStorageError,
    DiaryError, IdentityError, PersonError, ExternalDataError, FrontierError,
    ExecutionError,
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

    except IdentityError as e:
        await bus.broadcast("Persona creation failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not set up persona identity files.")

    except PersonError as e:
        await bus.broadcast("Persona creation failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not set up person files.")

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

    except IdentityError as e:
        await bus.broadcast("Persona growth failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not save context observations to persona.")

    except PersonError as e:
        await bus.broadcast("Persona growth failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not save person observations to persona.")


async def sense(persona: Persona, prompt: str, channel: Channel) -> Outcome[dict]:
    """It lets the persona sense a stimulus from a channel and process it."""
    await bus.propose(
        "Sensing", {"persona_id": persona.id, "channel": channel.name}
    )

    try:
        think = agent.given(persona, {"type": "stimulus", "role": "user", "content": prompt, "channel": channel.name})

        failed = False
        async for thought in think.reason():
            if thought.intent == "saying":
                await say(persona, thought, channel)
            elif thought.intent == "doing":
                if failed:
                    agent.note({
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
            "Sensed", {"persona_id": persona.id, "channel": channel.name}
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
        "Saying", {"persona_id": persona.id}
    )

    channels = [channel] if channel else persona.channels or []

    signals = await bus.order(
        "Say", {"content": thought.content, "channels": [ch.name for ch in channels]}
    )

    for signal in signals:
        if (
            signal.title == "Communicated"
            and signal.details.get("content") == thought.content
        ):
            person.heard({
                "type": "communicated",
                "channel": signal.details.get("channel"),
                "content": thought.content,
            })

            await bus.broadcast(
                "Said", {"persona_id": persona.id, "channel": signal.details.get("channel")}
            )

            return Outcome(
                success=True,
                message="Thought expressed",
                data={"persona_id": persona.id},
            )

    await bus.broadcast(
        "Saying failed", {"persona_id": persona.id}
    )

    return Outcome(
        success=False,
        message="No channel communicated the thought.",
        data={"persona_id": persona.id},
    )


async def act(persona: Persona, thought: Thought) -> Outcome[dict]:
    """It lets the persona act on the world by executing a tool call."""
    await bus.propose(
        "Acting", {"persona_id": persona.id, "tool": thought.tool_calls}
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
        agent.note({
            "type": "act",
            "tool_calls": thought.tool_calls,
            "result": "Rejected — the person declined to run this command.",
        })

        await bus.broadcast(
            "Acting rejected",
            {"persona_id": persona.id, "tool": thought.tool_calls},
        )

        return Outcome(
            success=False,
            message="Command rejected by the person.",
            data={"persona_id": persona.id},
        )

    try:
        result = await system.execute(thought.tool_calls)

        agent.note({"type": "act", "tool_calls": thought.tool_calls, "result": result})

        await bus.broadcast(
            "Acted", {"persona_id": persona.id, "tool": thought.tool_calls}
        )

        return Outcome(
            success=True,
            message="Action executed",
            data={"persona_id": persona.id},
        )

    except ExecutionError as e:
        agent.note({
            "type": "act",
            "tool_calls": thought.tool_calls,
            "result": f"Failed: {e}",
        })

        await bus.broadcast(
            "Acting failed",
            {"persona_id": persona.id, "tool": thought.tool_calls, "error": str(e)},
        )

        return Outcome(
            success=False,
            message="Command failed to execute.",
            data={"persona_id": persona.id},
        )

    except UnsupportedOS as e:
        agent.note({
            "type": "act",
            "tool_calls": thought.tool_calls,
            "result": f"Failed: {e}",
        })

        await bus.broadcast(
            "Acting failed",
            {"persona_id": persona.id, "tool": thought.tool_calls, "error": str(e)},
        )

        return Outcome(
            success=False,
            message="Your operating system is not supported.",
            data={"persona_id": persona.id},
        )


async def escalate(persona: Persona, prompt: str, channel: Channel) -> Outcome[dict]:
    """It lets the persona escalate to a frontier model when the task exceeds its ability."""
    await bus.propose(
        "Escalating", {"persona_id": persona.id}
    )

    try:
        observation = [{"role": "user", "content": prompt}]

        failed = False
        async for response in frontier.consulting(persona.frontier, prompt).reason():
            if response.intent == "saying":
                observation.append({"role": "assistant", "content": response.content})
                await say(persona, response, channel)
            elif response.intent == "doing":
                observation.append({"role": "assistant", "tool_calls": response.tool_calls})
                if failed:
                    agent.note({
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

        agent.observe(observation)

        await bus.broadcast(
            "Escalated", {"persona_id": persona.id}
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
        "Reflecting", {"persona_id": persona.id}
    )

    try:
        think = agent.given(persona, prompts.reflection())

        async for thought in think.reason():
            if thought.intent == "saying":
                await say(persona, thought, channel)
            elif thought.intent == "reasoning":
                await bus.share("Reasoning", {"content": thought.content})

        await bus.broadcast(
            "Reflected", {"persona_id": persona.id}
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
        "Predicting", {"persona_id": persona.id}
    )

    try:
        think = agent.given(persona, prompts.prediction())

        async for thought in think.reason():
            if thought.intent == "saying":
                await say(persona, thought, channel)
            elif thought.intent == "reasoning":
                await bus.share("Reasoning", {"content": thought.content})

        await bus.broadcast(
            "Predicted", {"persona_id": persona.id}
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
    """It lets you look into your persona's mind — what it knows, what it learned, and how it sees you."""
    await bus.propose("Overseeing persona", {"persona_id": persona.id})

    try:
        facts = await person.identified_by(persona)
        traits = await person.traits_toward(persona)
        agent_data = await agent.identity(persona)
        skill_list = await agent.skills(persona)
        conversations = await agent.conversations(persona)

        await bus.broadcast("Persona overseen", {"persona_id": persona.id})

        return Outcome(
            success=True,
            message="Persona overview ready",
            data={
                "person": system.make_rows_traceable(facts, "pi"),
                "traits": system.make_rows_traceable(traits, "pt"),
                "agent": system.make_rows_traceable(agent_data["identity"], "pai")
                    + system.make_rows_traceable(agent_data["context"], "pc"),
                "skills": system.make_rows_traceable(skill_list, "sk"),
                "memory": system.make_rows_traceable(conversations, "mem"),
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
    await bus.propose("Controlling persona", {"persona_id": persona.id, "count": len(entry_ids)})

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
                await agent.delete_skill(persona, hash_part)
            elif prefix == "mem":
                await agent.delete_memory(persona, hash_part)

        await bus.broadcast("Persona controlled", {"persona_id": persona.id, "removed": len(entry_ids)})

        return Outcome(
            success=True,
            message="Entries removed successfully",
            data={"removed": len(entry_ids)},
        )

    except ValueError:
        await bus.broadcast("Persona control failed", {"reason": "invalid_id", "persona_id": persona.id})
        return Outcome(success=False, message="Invalid entry ID format.")

    except IdentityError as e:
        await bus.broadcast("Persona control failed", {"reason": "identity", "error": str(e)})
        return Outcome(success=False, message="Could not remove agent entry. It may have been modified or already deleted.")

    except PersonError as e:
        await bus.broadcast("Persona control failed", {"reason": "person", "error": str(e)})
        return Outcome(success=False, message="Could not remove person entry. It may have been modified or already deleted.")


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
