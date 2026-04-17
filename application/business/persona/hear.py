"""Persona — receiving a message and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus
from application.core.data import Channel, Message, Persona
from application.core.exceptions import MindError


@dataclass
class HearData:
    response: str


async def hear(persona: Persona, content: str, channel_type: str = "", channel_name: str = "", channel_credentials: dict | None = None) -> Outcome[HearData]:
    """Receive a message — filter noise, construct the core Message, pass it to the ego."""
    if channel_type and channel_type != "web":
        verified = next(
            (c for c in (persona.channels or [])
             if c.type == channel_type and c.verified_at),
            None,
        )
        if not verified:
            return Outcome(success=True, message="", data=HearData(response="Channel not verified."))

    channel = Channel(type=channel_type, name=channel_name, credentials=channel_credentials)
    message = Message(channel=channel, content=content)
    await bus.propose("Hearing", {"persona": persona, "channel": channel})
    try:
        if persona.ego.is_sleeping():
            await bus.broadcast("Heard", {"persona": persona})
            return Outcome(success=True, message="", data=HearData(response=f"{persona.name} is sleeping."))

        persona.ego.receive(message)

        await bus.broadcast("Heard", {
            "persona": persona,
            "content": content,
            "channel_type": channel_type,
        })
        return Outcome(success=True, message="")
    except MindError as e:
        await bus.broadcast("Hearing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
