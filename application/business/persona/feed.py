"""Persona — feeding external AI history."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, models
from application.core.brain import functions
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import EngineConnectionError, ModelError


@dataclass
class FeedData:
    persona: Persona


async def feed(ego, data: str, source: str) -> Outcome[FeedData]:
    """It lets you feed your persona with your existing AI history so it can know you faster."""
    persona = ego.persona
    bus.propose("Feeding persona", {"persona": persona, "source": source})

    @dataclass
    class VirtualMemory:
        messages: list
        prompts: list
        archive: list

    try:
        conversations = await models.read_external_history(data, source)
        identity = ego.personality()

        for conversation in conversations:
            messages = []
            for m in conversation:
                role = "user" if m.get("role") == "user" else "assistant"
                content = m.get("content", "")
                prompt_content = f"The person said: {content}" if role == "user" else content
                messages.append(Message(
                    content=content,
                    prompt=Prompt(role=role, content=prompt_content),
                ))

            feed_memory = VirtualMemory(
                messages=messages,
                prompts=[{"role": m.prompt.role, "content": m.prompt.content} for m in messages],
                archive=[messages],
            )
            await functions.transform(ego, identity, feed_memory)

        bus.broadcast("Persona fed", {"persona": persona, "source": source})
        return Outcome(
            success=True,
            message="Persona fed successfully",
            data=FeedData(persona=persona),
        )

    except ModelError as e:
        bus.broadcast("Persona feeding failed", {"reason": "external_data", "error": str(e)})
        return Outcome(success=False, message="Could not parse the external data. Please check the file format.")

    except EngineConnectionError as e:
        bus.broadcast("Persona feeding failed", {"reason": "connection", "error": str(e)})
        return Outcome(success=False, message="Could not analyze the conversations. Please make sure the model is running.")
