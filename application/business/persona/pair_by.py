"""Persona — generating a pairing code for an unverified channel and sending it."""

import secrets
from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, channels
from application.core.data import Channel, Persona
from application.platform import datetimes


@dataclass
class PairingData:
    code: str
    created_at: object


async def pair_by(persona: Persona, channel: Channel) -> Outcome[PairingData]:
    """Generate a pairing code for a channel and send it to the person."""
    bus.propose("Initiating pairing", {"persona": persona, "channel": channel})

    code = secrets.token_hex(3).upper()

    await channels.send(
        channel,
        f"Your pairing code is: {code}\n\n"
        "Enter this code in the Eternego web UI to verify this channel.\n\n"
        "This code expires in 10 minutes.",
    )

    bus.broadcast("Pairing initiated", {"persona": persona, "channel": channel, "code": code})
    return Outcome(
        success=True,
        message="",
        data=PairingData(
            code=code,
            created_at=datetimes.now(),
        ),
    )
