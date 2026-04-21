"""Persona — receiving a message and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus
from application.core.data import Message
from application.core.exceptions import MindError


@dataclass
class HearData:
    response: str


async def hear(ego, content: str, channel=None) -> Outcome[HearData]:
    """Receive a text message — filter noise, construct the core Message, pass it to the ego."""
    if channel and channel.type != "web" and not channel.verified_at:
        return Outcome(success=True, message="", data=HearData(response="Channel not verified."))

    persona = ego.persona
    message = Message(channel=channel, content=content)
    bus.propose("Hearing", {"persona": persona, "channel": channel})
    try:
        if ego.is_sleeping():
            bus.broadcast("Heard", {"persona": persona})
            return Outcome(success=True, message="", data=HearData(response=f"{persona.name} is sleeping."))

        ego.receive(message)

        bus.broadcast("Heard", {
            "persona": persona,
            "content": content,
            "channel": channel,
        })
        return Outcome(success=True, message="")
    except MindError as e:
        bus.broadcast("Hearing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
