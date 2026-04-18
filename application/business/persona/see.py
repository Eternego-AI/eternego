"""Persona — receiving an image and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus
from application.core.data import Channel, Media, Message, Persona
from application.core.exceptions import MindError


@dataclass
class SeeData:
    response: str


async def see(persona: Persona, source: str, query: str, channel: Channel | None = None) -> Outcome[SeeData]:
    """Receive an image — filter noise, construct the core Message with Media, pass it to the ego."""
    if channel and channel.type != "web" and not channel.verified_at:
        return Outcome(success=True, message="", data=SeeData(response="Channel not verified."))

    media = Media(source=source, query=query)
    message = Message(channel=channel, content=query, media=media)
    await bus.propose("Seeing", {"persona": persona, "channel": channel})
    try:
        if persona.ego.is_sleeping():
            await bus.broadcast("Seen", {"persona": persona})
            return Outcome(success=True, message="", data=SeeData(response=f"{persona.name} is sleeping."))

        persona.ego.receive(message)

        await bus.broadcast("Seen", {
            "persona": persona,
            "source": source,
            "channel": channel,
        })
        return Outcome(success=True, message="")
    except MindError as e:
        await bus.broadcast("Seeing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
