"""Persona — receiving an image and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus
from application.core.data import Media, Message
from application.core.exceptions import MindError


@dataclass
class SeeData:
    response: str


async def see(ego, source: str, caption: str = "", channel=None) -> Outcome[SeeData]:
    """Receive an image — assumes source is already in the persona's media dir."""
    if channel and channel.type != "web" and not channel.verified_at:
        return Outcome(success=True, message="", data=SeeData(response="Channel not verified."))

    persona = ego.persona
    media = Media(source=source, caption=caption)
    message = Message(channel=channel, content=caption, media=media)
    bus.propose("Seeing", {"persona": persona, "channel": channel})
    try:
        if ego.is_sleeping():
            bus.broadcast("Seen", {"persona": persona})
            return Outcome(success=True, message="", data=SeeData(response=f"{persona.name} is sleeping."))

        ego.receive(message)

        bus.broadcast("Seen", {
            "persona": persona,
            "source": source,
            "caption": caption,
            "channel": channel,
        })
        return Outcome(success=True, message="")
    except MindError as e:
        bus.broadcast("Seeing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
