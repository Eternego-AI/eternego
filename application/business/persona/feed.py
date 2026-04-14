"""Persona — feeding external AI history."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus, models
from application.core.brain import functions
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import EngineConnectionError, FrontierError


@dataclass
class FeedData:
    persona: Persona


async def feed(persona: Persona, data: str, source: str) -> Outcome[FeedData]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    await bus.propose("Feeding persona", {"persona": persona, "source": source})

    @dataclass
    class VirtualMemory:
        messages: list
        prompts: list


    try:
        conversations = await models.read_external_history(data, source)
        ego = agents.persona(persona)
        identity = ego.identity()

        for conversation in conversations:
            messages = []
            for m in conversation:
                role = "user" if m.get("role") == "user" else "assistant"
                content = m.get("content", "")
                messages.append(Message(
                    content=content,
                    prompt=Prompt(role=role, content=content),
                ))
            
            
            feed_memory = VirtualMemory(
                messages=messages,
                prompts=[{"role": m.prompt.role, "content": m.prompt.content} for m in messages],
            )
            await functions.transform(persona, identity, feed_memory)

        await bus.broadcast("Persona fed", {"persona": persona, "source": source})
        return Outcome(
            success=True,
            message="Persona fed successfully",
            data=FeedData(persona=persona),
        )

    except FrontierError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except EngineConnectionError as e:
        await bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")
