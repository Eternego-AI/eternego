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
from application.platform.observer import Command, Signal, subscribe


# ── Agent (the desk) ──────────────────────────────────────────────────────────

class Agent:
    """A self-sufficient desk that serves one persona.

    Creates Ego, connects its own channels, runs its own heartbeat.
    """

    def __init__(self, persona: Persona):
        self.persona = persona
        self._stops: dict = {}  # channel_key -> stop callable
        self._pending_connects = []  # in-flight connect tasks
        self.pairing_codes: dict = {}
        self.persona.ego = Ego(self.persona, Worker(), situation.wake)

        wake_text = f"Wake up {self.persona.name}"
        self.persona.ego.memory.add(Message(
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
        ego.memory.add(Message(
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
        ego.memory.add(Message(
            content=wake_text,
            prompt=Prompt(role="user", content=wake_text),
        ))
        ego.worker.run(clock.tick, ego.consciousness(), ego.worker)

        return outcome

    async def connect(self, channel: Channel):
        """Connect a channel — called at construction and from WebSocket route."""
        key = f"{channel.type}:{channel.name}"
        if key in self._stops:
            return

        from application.business.persona import connect
        outcome = await connect(self.persona, channel, self.pairing_codes)
        if not outcome.success or not outcome.data:
            return

        conn = outcome.data
        self.persona.ego.channels.append(conn.channel)

        if conn.poll is None:
            self._stops[key] = conn.close
            return

        # Keep the channel alive: poll in a background thread, dispatch to the handler.
        running = [True]
        loop = asyncio.get_running_loop()
        poll = conn.poll
        handle_message = conn.handle_message

        def poll_loop():
            while running[0]:
                try:
                    messages = poll()
                    if messages:
                        for msg in messages:
                            asyncio.run_coroutine_threadsafe(handle_message(msg), loop)
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
            self.persona.ego.persist()
            self.persona.ego = None



# ── Registry (the floor plan) ────────────────────────────────────────────────

_agents: dict[str, Agent] = {}
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

    subscribe(restart_gateway, on_channel_paired)


def serve(persona: Persona) -> Agent:
    """Assign an agent for this persona — construct, register routes, track."""
    agent = Agent(persona)
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
    """Release the old agent, assign a fresh one."""
    agent = find_or_none(persona_id)
    if not agent:
        return None
    p = agent.persona
    await release(persona_id)
    return serve(p)


async def release_all() -> None:
    """Release all agents — used during shutdown."""
    for agent in list(_agents.values()):
        await agent.teardown()
    _agents.clear()
