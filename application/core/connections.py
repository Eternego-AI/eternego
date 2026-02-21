"""Connections — persistent network connections, one per network per persona."""

import asyncio
import threading
import urllib.error
from collections.abc import Callable, Coroutine

from application.platform import logger, telegram
from application.core.data import Channel, Gateway, Message, Network, Persona
from application.core.exceptions import NetworkError


_pollers: dict[str, dict[str, threading.Event]] = {}  # persona_id → {network_id → stop_event}


async def verify(network: Network) -> bool:
    """Verify the network credentials are valid."""
    logger.info("Verifying network", {"type": network.type})
    try:
        if network.type == "telegram":
            response = await asyncio.to_thread(telegram.get_me, network.credentials["token"])
            return response.get("ok", False)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False
    return False


def connect(
    persona: Persona,
    network: Network,
    on_message: Callable[[Message], Coroutine[None, None, None]],
) -> None:
    """Start a persistent connection for a network. For telegram, starts a polling thread."""
    logger.info("Connecting to network", {"type": network.type, "persona": persona.id})
    from application.core import gateways as gw_module

    loop = asyncio.get_running_loop()

    if network.type == "telegram":
        token = (network.credentials or {})["token"]
        stop_event = threading.Event()

        def bridge(text: str, msg_chat_id: str):
            from application.core import channels, pairing
            if not channels.is_verified(persona, network.id, msg_chat_id):
                code = pairing.generate(persona.id, network.id, msg_chat_id)
                asyncio.run_coroutine_threadsafe(
                    asyncio.to_thread(
                        telegram.send,
                        token=token,
                        chat_id=msg_chat_id,
                        message=(
                            f"Your pairing code is: {code}\n\n"
                            f"Run: eternego pair {code}\n\n"
                            f"This code expires in 10 minutes."
                        ),
                    ),
                    loop,
                )
                return
            channel = Channel(type=network.type, name=msg_chat_id)
            gw = gw_module.of(persona).find(channel)
            if gw is None:
                _token = token
                _chat_id = msg_chat_id
                gw = Gateway(
                    channel=channel,
                    send=lambda t: asyncio.to_thread(telegram.send, token=_token, chat_id=_chat_id, message=t),
                )
                gw_module.of(persona).add(gw)
            message = Message(channel=channel, content=text)
            asyncio.run_coroutine_threadsafe(on_message(message), loop)

        def on_error(exc: Exception):
            logger.warning(
                f"Polling error on {network.type} for {persona.name}",
                {"network": network.type, "persona": persona.id, "error": str(exc)},
            )

        thread = threading.Thread(
            target=telegram.poll,
            kwargs={
                "token": token,
                "username": persona.name,
                "on_message": bridge,
                "stop": lambda: stop_event.is_set(),
                "on_error": on_error,
            },
            daemon=True,
        )
        thread.start()
        _pollers.setdefault(persona.id, {})[network.id] = stop_event

    else:
        raise NetworkError(f"Unsupported network type: {network.type}")


def disconnect_all(persona: Persona) -> bool:
    """Stop all network connections for a persona. Returns True if any were active."""
    logger.info("Disconnecting all networks", {"persona": persona.id})
    stops = _pollers.pop(persona.id, {})
    for event in stops.values():
        event.set()
    from application.core import gateways as gw_module
    gw_module.of(persona).close_all()
    return bool(stops)
