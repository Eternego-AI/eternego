"""Manager — assigns agents to desks, keeps the floor plan.

Agent: the desk — self-sufficient, creates its own Ego, opens its own
channels, stores pairing codes that specs produce.

Registry: just the floor plan — {persona_id: agent}. No business logic.

serve(persona): create agent, register routes, track.
release(persona_id): teardown, remove routes, dismiss.
"""

import asyncio
import threading

from application.core.agents import Ego
from application.core.brain import situation
from application.core.brain.mind import clock
from application.core.data import Channel, Message, Persona, Prompt
from application.core.exceptions import AgentError
from application.platform import logger
from application.platform.asyncio_worker import Worker
from application.platform.observer import Command, Message as MessageSignal, Signal, subscribe


# ── Agent (the desk) ──────────────────────────────────────────────────────────

class Agent:
    """A self-sufficient desk that serves one persona.

    Creates Ego, connects its own channels, runs its own heartbeat.
    """

    def __init__(self, persona: Persona, commands: dict):
        self.persona = persona
        self.commands = commands
        self._stops: dict = {}  # channel_key -> stop callable
        self._pending_connects = []  # in-flight connect tasks
        self.persona.ego = Ego(self.persona, Worker(), situation.wake)

        wake_text = f"Wake up {self.persona.name}"
        self.persona.ego.memory.remember(Message(
            content=wake_text,
            prompt=Prompt(role="user", content=wake_text),
        ))

        for channel in (self.persona.channels or []):
            self._pending_connects.append(asyncio.create_task(self.connect(channel)))

        self.persona.ego.worker.run(clock.tick, self.persona.ego.consciousness(), self.persona.ego.worker)

        async def beat():
            from application.business.persona import heartbeat
            while True:
                await asyncio.sleep(60)
                try:
                    await heartbeat(self.persona)
                except Exception as e:
                    logger.warning("Heartbeat failed", {"persona": self.persona, "error": str(e)})

        async def check_schedule():
            from application.business.routine import trigger
            while True:
                await asyncio.sleep(60)
                try:
                    await trigger(self.persona, self.sleep)
                except Exception as e:
                    logger.warning("Schedule check failed", {"persona": self.persona, "error": str(e)})

        self.heartbeat_task = asyncio.create_task(beat())
        self.schedule_task = asyncio.create_task(check_schedule())

    async def sleep(self):
        """End-of-shift: set sleep situation, settle, do paperwork, swap in a fresh worker."""
        from application.business.persona import sleep
        ego = self.persona.ego
        ego.current_situation = situation.sleep
        ego.memory.remember(Message(
            content="Go to sleep",
            prompt=Prompt(role="user", content="Go to sleep"),
        ))
        await ego.settle()
        outcome = await sleep(self.persona)

        # Fresh worker for tomorrow — no restart, channels and routes stay.
        await ego.worker.stop()
        ego.worker = Worker()
        ego.current_situation = situation.wake
        wake_text = f"Wake up {self.persona.name}"
        ego.memory.remember(Message(
            content=wake_text,
            prompt=Prompt(role="user", content=wake_text),
        ))
        ego.worker.run(clock.tick, ego.consciousness(), ego.worker)

        return outcome

    async def handle_command(self, command: str, details: dict, channel=None):
        """Look up a command in the agent's command map and run it.

        If the channel is not verified, send a pairing code instead.
        """
        if channel and not channel.verified_at:
            from application.business.persona.pair_by import pair_by
            outcome = await pair_by(self.persona, channel)
            if outcome.success and outcome.data:
                _pairing_codes[outcome.data.code] = {
                    "channel_type": channel.type,
                    "channel_name": channel.name,
                    "created_at": outcome.data.created_at,
                }
            return
        entry = self.commands.get(command)
        if not entry:
            return
        logger.info("Handling command", {"persona": self.persona, "command": command})
        handler = entry.get("handler")
        if handler:
            await handler(self.persona, details)

    async def connect(self, channel: Channel):
        """Connect a channel — called at construction and from WebSocket route."""
        key = f"{channel.type}:{channel.name}"
        if key in self._stops:
            return

        from application.business.persona import connect
        channel_commands = [
            {"command": name, "description": entry["description"]}
            for name, entry in self.commands.items()
        ]
        outcome = await connect(self.persona, channel, channel_commands)
        if not outcome.success or not outcome.data:
            return

        conn = outcome.data
        self.persona.ego.channels.append(conn.channel)

        if conn.poll is None:
            self._stops[key] = conn.close
            return

        running = [True]
        poll = conn.poll

        def poll_loop():
            while running[0]:
                try:
                    poll()
                except Exception as e:
                    logger.warning("Gateway polling error", {
                        "channel": f"{channel.type}:{channel.name}",
                        "error": str(e),
                    })

        threading.Thread(target=poll_loop, daemon=True).start()

        def stop():
            running[0] = False
            conn.close()

        self._stops[key] = stop

    async def disconnect(self, channel: Channel):
        """Disconnect a specific channel — called from WebSocket route on close."""
        key = f"{channel.type}:{channel.name}"
        stop = self._stops.pop(key, None)
        if stop:
            stop()
        if self.persona.ego:
            self.persona.ego.channels = [
                c for c in self.persona.ego.channels
                if f"{c.type}:{c.name}" != key
            ]

    async def teardown(self):
        """Stop periodic tasks, close all connections, turn off the computer, save work."""
        logger.info("Tearing down agent", {"persona": self.persona})
        self.heartbeat_task.cancel()
        self.schedule_task.cancel()

        # Cancel in-flight connects and wait so no channel lands after teardown.
        for task in self._pending_connects:
            task.cancel()
        await asyncio.gather(*self._pending_connects, return_exceptions=True)

        for stop in self._stops.values():
            stop()
        self._stops.clear()
        if self.persona.ego:
            await self.persona.ego.stop()
            self.persona.ego = None



# ── Registry (the floor plan) ────────────────────────────────────────────────

_agents: dict[str, Agent] = {}
_pairing_codes: dict[str, dict] = {}
_app = None


def find(persona_id: str) -> Agent:
    """Look up the floor plan. Raises AgentError if not found."""
    agent = _agents.get(persona_id)
    if agent is None:
        raise AgentError(f"No agent assigned for '{persona_id}'.")
    return agent


def find_or_none(persona_id: str) -> Agent | None:
    return _agents.get(persona_id)


def all_agents() -> list[Agent]:
    return list(_agents.values())


# ── Manager operations ────────────────────────────────────────────────────────

def claim_pairing_code(code: str) -> dict | None:
    """Look up and consume a pairing code. Returns {channel_type, channel_name} or None."""
    from application.platform import datetimes
    from datetime import timedelta

    code_upper = code.upper()
    entry = _pairing_codes.get(code_upper)
    if not entry:
        return None
    if datetimes.now() - entry["created_at"] > timedelta(minutes=10):
        _pairing_codes.pop(code_upper, None)
        return None
    _pairing_codes.pop(code_upper, None)
    return {"channel_type": entry["channel_type"], "channel_name": entry["channel_name"]}


def start(app) -> None:
    """Initialize the manager: store the web app and subscribe signals."""
    global _app
    _app = app

    async def on_channel_paired(signal: Signal):
        if signal.title != "Channel paired":
            return
        p = signal.details.get("persona")
        if not p:
            return
        await restart(p.id)

    async def restart_gateway(command: Command):
        if command.title != "Restart gateway":
            return
        p = command.details.get("persona")
        if not p:
            return
        await restart(p.id)

    async def on_telegram_command(command: Command):
        if not command.title.startswith("Telegram command:"):
            return
        cmd = command.details.get("command")
        chat_id = command.details.get("chat_id")
        if not cmd or not chat_id:
            return
        for agent in all_agents():
            for ch in (agent.persona.channels or []):
                if ch.type == "telegram" and ch.name == chat_id:
                    await agent.handle_command(cmd, command.details, ch)
                    return
        for agent in all_agents():
            for ch in (agent.persona.channels or []):
                if ch.type == "telegram" and not ch.verified_at:
                    ch.name = chat_id
                    await agent.handle_command(cmd, command.details, ch)
                    return
        logger.warning("Telegram command from unknown channel", {"chat_id": chat_id, "command": cmd})

    async def on_telegram_message(signal: MessageSignal):
        if signal.title not in ("Telegram message received", "Telegram media received"):
            return
        chat_id = signal.details.get("chat_id", "")
        if not chat_id:
            return
        for agent in all_agents():
            for ch in (agent.persona.channels or []):
                if ch.type == "telegram" and ch.name == chat_id:
                    if signal.title == "Telegram message received":
                        text = signal.details.get("text", "")
                        if text:
                            from application.business.persona.hear import hear
                            await hear(agent.persona, content=text, channel=ch)
                    elif signal.title == "Telegram media received":
                        media_source = signal.details.get("media_source", "")
                        caption = signal.details.get("media_caption", "") or signal.details.get("text", "")
                        if media_source:
                            from application.business.persona.see import see
                            await see(agent.persona, source=media_source, caption=caption, channel=ch)
                    return

    async def on_persona_stop(command: Command):
        if command.title != "Persona requested stop":
            return
        persona = command.details.get("persona")
        agent = find_or_none(persona.id)
        if agent and agent.persona.ego:
            logger.info("Persona requested stop", {"persona": persona})
            await agent.persona.ego.stop()

    async def on_persona_sick(command: Command):
        if command.title != "Persona became sick":
            return
        persona = command.details.get("persona")
        if not find_or_none(persona.id):
            return
        logger.info("Persona became sick — releasing", {"persona": persona})
        await release(persona.id)

    subscribe(restart_gateway, on_channel_paired, on_telegram_command, on_telegram_message, on_persona_stop, on_persona_sick)


def serve(persona: Persona) -> Agent:
    """Assign an agent for this persona — construct, register routes, track."""

    async def handle_stop(p, details):
        if p.ego:
            await p.ego.stop()

    async def handle_restart(p, details):
        await restart(p.id)

    commands = {
        "start": {"description": "Pair this chat with the persona"},
        "stop": {"description": "Stop the persona", "handler": handle_stop},
        "restart": {"description": "Restart the persona", "handler": handle_restart},
    }

    agent = Agent(persona, commands)
    _agents[persona.id] = agent

    from web.routes.agent_routes import register_routes
    register_routes(_app, agent)

    logger.info("Serving persona", {"persona": persona})
    return agent


async def release(persona_id: str) -> None:
    """Release an agent — teardown, remove routes, dismiss."""
    agent = _agents.pop(persona_id, None)
    if not agent:
        return
    await agent.teardown()

    from web.routes.agent_routes import unregister_routes
    unregister_routes(_app, persona_id)

    logger.info("Released persona", {"persona_id": persona_id})


async def restart(persona_id: str) -> Agent | None:
    """Release the old agent and assign a fresh one. Skips if the persona is no
    longer active (sick / hibernating) — the person has to wake it deliberately."""
    agent = find_or_none(persona_id)
    if not agent:
        return None
    p = agent.persona
    await release(persona_id)
    if p.status != "active":
        logger.info("Restart skipped — persona not active", {"persona": p})
        return None
    return serve(p)


async def release_all() -> None:
    """Release all agents — used during shutdown."""
    for agent in list(_agents.values()):
        await agent.teardown()
    _agents.clear()
