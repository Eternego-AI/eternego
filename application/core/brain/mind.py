"""Mind — the persona's cognitive processing core."""

import json

from application.platform import logger, strings, processes, reflections
from application.platform.observer import Command
from application.core import bus, local_model
from application.core.brain import abilities, memories
from application.core.brain import values
from application.core.data import Channel, Persona, Prompt, Thread


async def grow(persona: Persona, channel: Channel) -> None:
    """Evolve DNA, generate per-item training, fine-tune, and wake up."""
    import json
    from application.core import frontier, local_inference_engine, models, paths, prompts
    from application.core.exceptions import DNAError

    logger.info("Mind growing", {"persona": persona.id})
    await bus.propose("Growing", {"persona": persona, "channel": channel})

    # Evolve DNA incorporating history briefing
    synthesis = prompts.dna_synthesis(
        previous_dna=await paths.read(await paths.dna(persona.id)),
        person_traits=await paths.read(await paths.person_traits(persona.id)),
        persona_context=await paths.read(await paths.context(persona.id)),
        history_briefing=await paths.read_history_brief(persona.id, "(no history yet)"),
    )
    if persona.frontier:
        new_dna = await frontier.chat(persona.frontier, synthesis)
    else:
        new_dna = await local_model.generate(persona.model.name, synthesis)
    await paths.write_dna(persona.id, new_dna)

    # Generate per-item training set
    dna_items = [line.strip() for line in new_dna.splitlines() if line.strip() and not line.strip().startswith("#")]
    all_pairs = []
    for item in dna_items:
        item_prompt = prompts.grow(dna=item, max_pairs=5)
        if persona.frontier:
            response = await frontier.chat(persona.frontier, item_prompt)
        else:
            response = await local_model.generate_json(persona.model.name, item_prompt)
        parsed = strings.to_json(response)
        if parsed and "training_pairs" in parsed:
            all_pairs.extend(parsed["training_pairs"])

    training_set = json.dumps({"training_pairs": all_pairs}, indent=2)
    await paths.add_training_set(persona.id, training_set)

    # Fine-tune and wake up
    old_model = persona.model.name
    new_model = models.generate(persona.base_model, persona.id)
    await local_inference_engine.fine_tune(persona.base_model, training_set, new_model.name)

    if not await local_inference_engine.check(new_model.name):
        raise DNAError("Fine-tuned model failed verification — previous model is still active")

    await local_inference_engine.delete(old_model)

    await paths.clear(await paths.person_traits(persona.id))

    persona.model = new_model
    await paths.save_as_json(persona.id, await paths.persona_identity(persona.id), persona)

    await bus.broadcast("Growth Concluded", {"persona": persona, "channel": channel})


async def summarize(persona: Persona, thread: Thread, channel: Channel, items: list[Thread]) -> None:
    """Summarize a single thread via reflective reasoning and archive it to history."""
    for summarizing_thread in items:
        thread_messages = memories.agent(persona).as_messages(summarizing_thread.id)
        if len(thread_messages) < 2:
            continue
        conversation = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in thread_messages
            if msg.get("content")
        )
        await reason(persona, thread, channel, [
            {"role": "system", "content": values.build(persona, channel)},
            {"role": "user", "content": f"Below is a conversation from your memory. Summarize it and archive it to your long-term history using the archive ability.\n\n{conversation}"},
        ])


def think(persona: Persona, thread: Thread, channel: Channel) -> None:
    """Schedule thinking as a background task — never blocks the caller."""
    logger.info("Mind thinking", {"persona": persona.id, "thread": thread.id})
    messages = [{"role": "system", "content": values.build(persona, channel)}]
    messages += memories.agent(persona).as_messages(thread.id)

    async def _run():
        await bus.propose("Thinking", {"persona": persona, "thread": thread})
        reasons = await reason(persona, thread, channel, messages)
        await bus.broadcast("Thought Concluded", {"persona": persona, "thread": thread, "loops": reasons})

    processes.run_async(_run)


async def reason(persona: Persona, thread: Thread, channel: Channel, messages: list[dict]) -> int:
    loop = 0
    while True:
        responses = await bus.ask("Reasoning Thought", {"persona": persona, "thread": thread, "loop": loop})
        if any(isinstance(r, Command) and r.title == "Stop Reasoning" for r in responses):
            break

        plan_title = "Reasoning" if loop == 0 else "Chaining"
        responses = await bus.propose(plan_title, {"persona": persona, "thread": thread, "channel": channel, "loop": loop})
        if any(isinstance(r, Command) and r.title == "Stop Reasoning" for r in responses):
            break

        response = await local_model.chat_json(persona.model.name, messages)

        if not response or not isinstance(response, dict):
            response = {"say": [response]} if response else {}

        messages.append({"role": "assistant", "content": json.dumps(response)})
        loop += 1

        if not response:
            if loop == 1:
                messages.append({"role": "user", "content": "You must respond to the person. Use the say ability to send them a message."})
                continue
            break

        new_prompts = []
        for key, value in response.items():
            if not value or not reflections.has_ability(abilities, key, "ability"):
                continue
            value = value if isinstance(value, list) else [value]
            fn = getattr(abilities, key)
            if channel.authority not in fn.ability_scopes:
                new_prompts.append(Prompt(role="user", content=f"{key} is not available on this channel."))
                continue
            try:
                result = await fn(persona, thread, channel, value)
                if result:
                    new_prompts.append(result)
            except Exception as e:
                logger.warning("Ability failed", {"ability": key, "error": str(e)})
                new_prompts.append(Prompt(role="user", content=f"{key} failed: {e}"))

        if not new_prompts:
            break

        for p in new_prompts:
            messages.append({"role": p.role, "content": p.content})

    return loop
