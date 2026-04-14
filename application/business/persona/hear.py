"""Persona — receiving a message and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import agents, bus, paths
from application.core.brain import situation
from application.core.data import Message, Persona
from application.core.exceptions import MindError
from application.platform import datetimes


@dataclass
class HearData:
    response: str


async def hear(persona: Persona, message: Message) -> Outcome[HearData]:
    """Receive a message, write to conversation, add to memory, trigger the mind."""
    await bus.propose("Hearing", {"persona": persona, "channel": message.channel})
    try:
        ego = agents.persona(persona)
        if ego.current_situation is situation.sleep:
            await bus.broadcast("Heard", {"persona": persona})
            return Outcome(success=True, message="", data=HearData(response=f"{persona.name} is sleeping."))

        paths.append_jsonl(paths.conversation(persona.id), {
            "role": "person",
            "content": message.content,
            "channel": message.channel.type if message.channel else "",
            "time": datetimes.iso_8601(datetimes.now()),
        })

        ego.memory.add(message)
        ego.current_situation = situation.normal
        ego.worker.nudge()

        await bus.broadcast("Heard", {
            "persona": persona,
            "content": message.content,
            "channel_type": message.channel.type if message.channel else "",
        })
        return Outcome(success=True, message="")
    except MindError as e:
        await bus.broadcast("Hearing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
