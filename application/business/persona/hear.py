"""Persona — receiving a message and triggering the mind."""

from application.business.outcome import Outcome
from application.core import agents, bus, paths
from application.core.brain import situation
from application.core.brain.data import Signal, SignalEvent
from application.core.data import Message, Persona
from application.core.exceptions import MindError
from application.platform import datetimes


async def hear(persona: Persona, message: Message) -> Outcome[dict]:
    """Receive a message, write to conversation, trigger the mind tick."""
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
