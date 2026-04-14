"""Persona — receiving a message and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus
from application.core.data import Message, Persona
from application.core.exceptions import MindError


@dataclass
class HearData:
    response: str


async def hear(persona: Persona, message: Message) -> Outcome[HearData]:
    """Receive a message — persona handles it through its ego."""
    await bus.propose("Hearing", {"persona": persona, "channel": message.channel})
    try:
        if persona.ego.is_sleeping():
            await bus.broadcast("Heard", {"persona": persona})
            return Outcome(success=True, message="", data=HearData(response=f"{persona.name} is sleeping."))

        persona.ego.receive(message)

        await bus.broadcast("Heard", {
            "persona": persona,
            "content": message.content,
            "channel_type": message.channel.type if message.channel else "",
        })
        return Outcome(success=True, message="")
    except MindError as e:
        await bus.broadcast("Hearing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
