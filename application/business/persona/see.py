"""Persona — receiving an image and triggering the mind."""

import os
from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Channel, Media, Message, Persona
from application.core.exceptions import MindError
from application.platform import datetimes, filesystem


@dataclass
class SeeData:
    response: str


async def see(persona: Persona, source: str, caption: str = "", channel: Channel | None = None) -> Outcome[SeeData]:
    """Receive an image — copy to media if needed, construct the core Message with Media, pass it to the ego."""
    if channel and channel.type != "web" and not channel.verified_at:
        return Outcome(success=True, message="", data=SeeData(response="Channel not verified."))

    media_dir = str(paths.media(persona.id))
    if not source.startswith(media_dir):
        ext = os.path.splitext(source)[1] or ".jpg"
        channel_name = channel.type if channel else "unknown"
        filename = f"{channel_name}-{datetimes.now().strftime('%Y%m%d-%H%M%S')}{ext}"
        dest = os.path.join(media_dir, filename)
        filesystem.copy_file(source, dest)
        source = dest

    media = Media(source=source, caption=caption)
    message = Message(channel=channel, content=caption, media=media)
    bus.propose("Seeing", {"persona": persona, "channel": channel})
    try:
        if persona.ego.is_sleeping():
            bus.broadcast("Seen", {"persona": persona})
            return Outcome(success=True, message="", data=SeeData(response=f"{persona.name} is sleeping."))

        persona.ego.receive(message)

        bus.broadcast("Seen", {
            "persona": persona,
            "source": source,
            "channel": channel,
        })
        return Outcome(success=True, message="")
    except MindError as e:
        bus.broadcast("Seeing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
