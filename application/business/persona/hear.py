"""Persona — receiving a text message and triggering the mind."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.brain.pulse import Phase
from application.core.data import Message, Prompt
from application.core.exceptions import MindError
from application.platform import datetimes


@dataclass
class HearData:
    response: str


async def hear(ego, living, content: str, channel=None) -> Outcome[HearData]:
    """Receive a text message — log to conversation, write to memory, flip to day, nudge."""
    if channel and channel.type != "web" and not channel.verified_at:
        return Outcome(success=True, message="", data=HearData(response="Channel not verified."))

    persona = ego.persona
    bus.propose("Hearing", {"persona": persona, "channel": channel})
    try:
        if living.pulse.phase == Phase.NIGHT:
            bus.broadcast("Heard", {"persona": persona})
            return Outcome(success=True, message="", data=HearData(response=f"{persona.name} is sleeping."))

        entry = {
            "role": "person",
            "content": content,
            "channel": {"type": channel.type, "name": channel.name or ""} if channel else None,
            "time": datetimes.iso_8601(datetimes.now()),
        }
        paths.append_jsonl(paths.conversation(persona.id), entry)

        message = Message(
            channel=channel,
            content=content,
            prompt=Prompt(role="user", content=content),
        )
        ego.memory.remember(message)
        living.pulse.phase = Phase.DAY
        living.pulse.worker.nudge()

        bus.broadcast("Heard", {
            "persona": persona,
            "content": content,
            "channel": channel,
        })
        return Outcome(success=True, message="")
    except MindError as e:
        bus.broadcast("Hearing failed", {"persona": persona, "error": str(e)})
        return Outcome(success=False, message="Something went wrong. Please try again.")
