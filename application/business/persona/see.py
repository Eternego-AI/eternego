"""Persona — receiving an image and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.brain.pulse import Phase
from application.core.data import Media, Message
from application.core.exceptions import MindError
from application.platform import datetimes


@dataclass
class SeeData:
    response: str


async def see(ego, living, source: str, caption: str = "", channel=None) -> Outcome[SeeData]:
    """Receive an image — log to conversation, write to memory, flip to day, nudge.

    Source is expected to be a path already saved under the persona's media
    dir. The prompt is intentionally left unset on the Message — realize
    builds the image content block (base64 or vision tool-call)."""
    if channel and channel.type != "web" and not channel.verified_at:
        return Outcome(success=True, message="", data=SeeData(response="Channel not verified."))

    persona = ego.persona
    bus.propose("Seeing", {"persona": persona, "channel": channel})
    try:
        if living.pulse.phase == Phase.NIGHT:
            bus.broadcast("Seen", {"persona": persona})
            return Outcome(success=True, message="", data=SeeData(response=f"{persona.name} is sleeping."))

        entry = {
            "role": "person",
            "content": caption,
            "channel": {"type": channel.type, "name": channel.name or ""} if channel else None,
            "time": datetimes.iso_8601(datetimes.now()),
            "media": {"source": source, "caption": caption},
        }
        paths.append_jsonl(paths.conversation(persona.id), entry)

        media = Media(source=source, caption=caption)
        message = Message(channel=channel, content=caption, media=media)
        ego.memory.remember(message)
        living.pulse.phase = Phase.DAY
        living.pulse.worker.nudge()

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
