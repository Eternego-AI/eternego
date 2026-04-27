"""Manager — thin orchestration.

Constructs connections, owns the agent registry, and exposes
`find / add / remove / restart / start / stop`. Every lifecycle and
signal concern for a served persona lives on the Agent itself."""

import asyncio
import os
import threading

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.agents import Consultant, Ego, Eye, Living, Teacher
from application.core.brain.mind import mind
from application.core.brain.pulse import Pulse
from application.core.data import Channel, Message, Persona, Prompt
from application.platform import datetimes
from application.platform import discord as discord_platform
from application.platform import logger
from application.platform import telegram as telegram_platform
from application.platform import web as web_platform
from application.platform.asyncio_worker import Worker
from application.platform.observer import Command, Message as MessageSignal, subscribe, unsubscribe


_agents: dict[str, "Agent"] = {}

telegram: telegram_platform.Connection | None = None
discord: discord_platform.Connection | None = None
web: web_platform.Connection | None = None

_on_thread = lambda fn: threading.Thread(target=fn, daemon=True).start()

DEFAULT_COMMANDS = [
    {"command": "start", "description": "Pair this chat with the persona"},
    {"command": "stop", "description": "Stop the persona"},
    {"command": "restart", "description": "Restart the persona"},
]


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent:
    """The body — holds the persona's voices and Living, connects nerves
    (gateways), routes stimuli to business specs. Contains no business
    logic itself."""

    def __init__(self, persona: Persona, connections: dict):
        self.persona = persona
        self.connections = connections
        self.gateways: list[dict] = []
        self.pairing_codes: dict = {}
        self.last_channel: Channel | None = None
        self._pending_connects: list = []
        self._subscribers: list = []

        worker = Worker()
        pulse = Pulse(worker)
        self.ego = Ego(persona)
        self.eye = Eye(persona)
        self.consultant = Consultant(persona)
        self.teacher = Teacher(persona)
        self.living = Living(
            pulse=pulse,
            ego=self.ego,
            eye=self.eye,
            consultant=self.consultant,
            teacher=self.teacher,
        )
        self.living.cycle = mind(self.living)

    async def start(self) -> None:
        """Wake the brain, connect nerves, wire reflexes."""
        for channel in (self.persona.channels or []):
            if channel.type not in self.connections:
                logger.error("Cannot start agent — no connection for channel type",
                             {"persona": self.persona, "channel_type": channel.type})
                return

        from application.business.persona import wake
        await wake(self.ego, self.living)

        for channel in (self.persona.channels or []):
            self._pending_connects.append(asyncio.create_task(self.connect(channel)))

        import secrets
        from application.business.persona.hear import hear
        from application.business.persona.see import see

        persona = self.persona
        ego = self.ego

        def find_gateway(channel_type, token, target):
            for gw in self.gateways:
                if gw["channel"].type != channel_type:
                    continue
                if not gw["channel"].verified_at:
                    continue
                if gw["channel"].name != target:
                    continue
                if token and gw["token"] != token:
                    continue
                return gw
            return None

        async def try_claim(channel_type, token, target):
            for gw in self.gateways:
                if gw["channel"].type != channel_type:
                    continue
                if gw["channel"].verified_at is not None:
                    continue
                if token and gw["token"] != token:
                    continue
                gw["channel"].name = target
                code = secrets.token_hex(3).upper()
                try:
                    await gw["connection"].send(gw["token"], target,
                        f"Your pairing code is: {code}\n\n"
                        "Enter this code in the Eternego web UI to verify this channel.\n"
                        "This code expires in 10 minutes.")
                except Exception:
                    return
                from application.platform import datetimes
                self.pairing_codes[code] = {
                    "channel": Channel(
                        type=gw["channel"].type,
                        name=target,
                        credentials=gw["channel"].credentials,
                    ),
                    "created_at": datetimes.now(),
                }
                return

        def save_media(source_path, channel):
            from application.core import paths
            from application.platform import datetimes, filesystem
            if not source_path:
                return source_path
            media_path = paths.media(persona.id)
            ext = os.path.splitext(source_path)[1] or ".jpg"
            filename = f"{channel.type}-{datetimes.now().strftime('%Y%m%d-%H%M%S')}{ext}"
            dest = os.path.join(str(media_path), filename)
            filesystem.copy_file(source_path, dest)
            return dest

        async def download_and_save(channel, url, filename):
            import tempfile
            import urllib.request
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".jpg"
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)
            try:
                await asyncio.to_thread(urllib.request.urlretrieve, url, temp_path)
            except Exception:
                return ""
            return save_media(temp_path, channel)

        async def on_say(command: Command):
            if command.title != "Persona wants to say":
                return
            if command.details.get("persona") is not persona:
                return
            text = command.details.get("text", "")
            if not text:
                return
            self.ego.memory.remember(Message(
                content=text,
                prompt=Prompt(role="assistant", content=text),
            ))
            if self.last_channel:
                targets = [gw for gw in self.gateways
                           if gw["channel"].type == self.last_channel.type
                           and gw["channel"].name == self.last_channel.name]
                entry_channel = {"type": self.last_channel.type, "name": self.last_channel.name or ""}
            else:
                targets = list(self.gateways)
                entry_channel = None
            for gw in targets:
                try:
                    await gw["connection"].send(gw["token"], gw["channel"].name, text)
                except Exception:
                    pass
            paths.append_jsonl(paths.conversation(persona.id), {
                "role": "persona",
                "content": text,
                "channel": entry_channel,
                "time": datetimes.iso_8601(datetimes.now()),
            })
            bus.broadcast("Said", {
                "persona": persona,
                "content": text,
                "channel": self.last_channel,
            })

        async def on_notify(command: Command):
            if command.title != "Persona wants to notify":
                return
            if command.details.get("persona") is not persona:
                return
            text = command.details.get("text", "")
            if not text:
                return
            targets = [gw for gw in self.gateways if gw["channel"].verified_at]
            for gw in targets:
                try:
                    await gw["connection"].send(gw["token"], gw["channel"].name, text)
                except Exception:
                    pass
            paths.append_jsonl(paths.conversation(persona.id), {
                "role": "persona",
                "content": text,
                "channel": None,
                "time": datetimes.iso_8601(datetimes.now()),
            })
            bus.broadcast("Notified", {
                "persona": persona,
                "content": text,
            })

        async def on_typing(command: Command):
            if command.title != "Persona wants to type":
                return
            if command.details.get("persona") is not persona:
                return
            if self.last_channel:
                targets = [gw for gw in self.gateways
                           if gw["channel"].type == self.last_channel.type
                           and gw["channel"].name == self.last_channel.name]
            else:
                targets = list(self.gateways)
            for gw in targets:
                try:
                    await gw["connection"].typing(gw["token"], gw["channel"].name)
                except Exception:
                    pass

        async def on_persona_stop(command: Command):
            if command.title != "Persona requested stop":
                return
            if command.details.get("persona") is not persona:
                return
            await self.living.pulse.worker.stop()

        async def on_persona_sick(command: Command):
            if command.title != "Persona became sick":
                return
            if command.details.get("persona") is not persona:
                return
            asyncio.create_task(remove(persona.id))

        async def on_telegram_message(signal: MessageSignal):
            if signal.title not in ("Telegram message received", "Telegram media received"):
                return
            token = signal.details.get("token", "")
            chat_id = signal.details.get("chat_id", "")
            gw = find_gateway("telegram", token, chat_id)
            if gw is None:
                await try_claim("telegram", token, chat_id)
                return
            if gw["channel"].verified_at:
                self.last_channel = gw["channel"]
            if signal.title == "Telegram message received":
                await hear(ego, self.living, content=signal.details.get("content", ""), channel=gw["channel"])
            else:
                path = signal.details.get("attachment_path", "")
                saved = save_media(path, gw["channel"]) if path else ""
                if saved:
                    await see(ego, self.living, source=saved, caption=signal.details.get("content", ""), channel=gw["channel"])

        async def on_telegram_command(signal: Command):
            if signal.title != "Telegram command received":
                return
            token = signal.details.get("token", "")
            chat_id = signal.details.get("chat_id", "")
            gw = find_gateway("telegram", token, chat_id)
            if gw is None:
                await try_claim("telegram", token, chat_id)
                return
            cmd = signal.details.get("command", "")
            if cmd == "stop":
                await self.living.pulse.worker.stop()
            elif cmd == "restart":
                asyncio.create_task(restart(persona.id))

        async def on_discord_message(signal: MessageSignal):
            if signal.title != "Discord message received":
                return
            token = signal.details.get("token", "")
            channel_id = signal.details.get("channel_id", "")
            gw = find_gateway("discord", token, channel_id)
            if gw is None:
                await try_claim("discord", token, channel_id)
                return
            if gw["channel"].verified_at:
                self.last_channel = gw["channel"]
            attachment_url = signal.details.get("attachment_url", "")
            if attachment_url:
                filename = signal.details.get("attachment_filename", "")
                saved = await download_and_save(gw["channel"], attachment_url, filename)
                if saved:
                    await see(ego, self.living, source=saved, caption=signal.details.get("content", ""), channel=gw["channel"])
            else:
                await hear(ego, self.living, content=signal.details.get("content", ""), channel=gw["channel"])

        async def on_web_message(signal: MessageSignal):
            if signal.title not in ("Web message received", "Web media received"):
                return
            persona_id = signal.details.get("persona_id", "")
            if persona_id != persona.id:
                return
            gw = next((g for g in self.gateways if g["channel"].type == "web"), None)
            if gw is None:
                return
            self.last_channel = gw["channel"]
            if signal.title == "Web message received":
                await hear(ego, self.living, content=signal.details.get("content", ""), channel=gw["channel"])
            else:
                path = signal.details.get("attachment_path", "")
                saved = save_media(path, gw["channel"]) if path else ""
                if saved:
                    await see(ego, self.living, source=saved, caption=signal.details.get("content", ""), channel=gw["channel"])

        self._subscribers = [
            on_say, on_notify, on_typing, on_persona_stop, on_persona_sick,
            on_telegram_message, on_telegram_command,
            on_discord_message, on_web_message,
        ]
        subscribe(*self._subscribers)

        logger.info("Serving persona", {"persona": self.persona})

    async def stop(self) -> None:
        """Disconnect nerves, stop brain."""
        logger.info("Tearing down agent", {"persona": self.persona})

        unsubscribe(*self._subscribers)
        self._subscribers.clear()

        for task in self._pending_connects:
            task.cancel()
        await asyncio.gather(*self._pending_connects, return_exceptions=True)

        for gw in list(self.gateways):
            try:
                gw["connection"].close_gateway(gw["token"])
            except Exception:
                pass
        self.gateways.clear()

        await self.living.pulse.worker.stop()
        self.living.dispose()

    async def heartbeat_tick(self) -> None:
        from application.business.persona import heartbeat
        try:
            await heartbeat(self.ego, self.living, sleep_fn=self.sleep)
        except Exception as e:
            logger.warning("Heartbeat failed", {"persona": self.persona, "error": str(e)})

    async def sleep(self):
        from application.business.persona import sleep
        return await sleep(self.ego, self.living)

    async def connect(self, channel: Channel) -> None:
        for gw in self.gateways:
            if gw["channel"] is channel:
                return
            if gw["channel"].type == channel.type and gw["channel"].name and gw["channel"].name == channel.name:
                return

        from application.core import paths
        conn = self.connections[channel.type]
        token = (channel.credentials or {}).get("token", "")
        media_path = str(paths.media(self.persona.id))

        if channel.type == "telegram":
            conn.open_gateway(
                token,
                filter_by=telegram_platform.direct_or_mentioned(self.persona.name),
                media_path=media_path,
                commands=DEFAULT_COMMANDS,
            )
        elif channel.type == "discord":
            conn.open_gateway(
                token,
                intents=discord_platform.INTENT_DIRECT_MESSAGES | discord_platform.INTENT_MESSAGE_CONTENT,
            )
        elif channel.type == "web":
            conn.open_gateway(channel)

        self.gateways.append({"channel": channel, "connection": conn, "token": token})

    async def disconnect(self, channel: Channel) -> None:
        gw = next(
            (g for g in self.gateways if g["channel"] is channel
             or (g["channel"].type == channel.type and g["channel"].name == channel.name and channel.name)),
            None,
        )
        if gw is None:
            return
        if gw in self.gateways:
            self.gateways.remove(gw)
        try:
            gw["connection"].close_gateway(gw["token"])
        except Exception:
            pass

    async def pair(self, code: str) -> Outcome:
        from application.business import environment
        from application.platform import datetimes
        from datetime import timedelta

        code_upper = code.upper()
        entry = self.pairing_codes.get(code_upper)
        if not entry:
            return Outcome(success=False, message="Pairing code is invalid or has expired.")
        if datetimes.now() - entry["created_at"] > timedelta(minutes=10):
            self.pairing_codes.pop(code_upper, None)
            return Outcome(success=False, message="Pairing code is invalid or has expired.")
        self.pairing_codes.pop(code_upper, None)
        from application.business.persona.pair import pair
        return await pair(self.persona, entry["channel"])


# ── Channel validation ────────────────────────────────────────────────────────

async def validate_channel(channel_type: str, credentials: dict) -> Channel:
    """Validate credentials against the provider. Returns a Channel or raises."""
    token = (credentials or {}).get("token", "")
    if channel_type == "telegram":
        await asyncio.to_thread(telegram_platform.get_me, token)
    elif channel_type == "discord":
        await asyncio.to_thread(discord_platform.get_me, token)
    elif channel_type != "web":
        raise ValueError(f"Unsupported channel type: {channel_type}")
    return Channel(type=channel_type, credentials=credentials)


# ── Registry and orchestration ────────────────────────────────────────────────

def find(persona_id: str) -> Agent | None:
    return _agents.get(persona_id)


def all_agents() -> list[Agent]:
    return list(_agents.values())


_heartbeat_task: asyncio.Task | None = None
on_fatal = None


async def start() -> None:
    """Boot: create connections, start the heart, load active personas."""
    global _heartbeat_task, telegram, discord, web

    telegram = telegram_platform.Connection(
        timeout=30,
        polling=_on_thread,
    )
    discord = discord_platform.Connection(
        timeout=30,
        websocket=_on_thread,
        properties={"os": "linux", "browser": "eternego", "device": "eternego"},
        user_agent="DiscordBot (eternego, 0.1)",
    )
    web = web_platform.Connection()

    _heartbeat_task = asyncio.create_task(_heartbeat_loop())

    from application.business.persona import get_list
    outcome = await get_list()
    personas = outcome.data.personas if outcome.data else []
    for p in personas:
        if p.status != "active":
            logger.info("Skipping inactive persona", {"persona": p, "status": p.status})
            continue
        try:
            await add(p)
        except Exception as e:
            logger.warning("Failed to add persona at boot", {"persona": p, "error": str(e)})


async def stop() -> None:
    """Teardown: stop every agent, stop every connection, stop the heart."""
    global _heartbeat_task
    if _heartbeat_task and not _heartbeat_task.done():
        _heartbeat_task.cancel()
    if _heartbeat_task:
        try:
            await _heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
    _heartbeat_task = None

    for agent in list(_agents.values()):
        await agent.stop()
    _agents.clear()

    if telegram:
        telegram.stop()
    if discord:
        discord.stop()
    if web:
        web.stop()


async def _heartbeat_loop() -> None:
    """Every 60s, tick every agent's heartbeat. If this loop dies, the daemon
    shuts down — the body can't live without a heart."""
    try:
        while True:
            await asyncio.sleep(60)
            agents = list(_agents.values())
            if agents:
                await asyncio.gather(
                    *[a.heartbeat_tick() for a in agents],
                    return_exceptions=True,
                )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Heartbeat loop crashed — daemon must shut down", {"error": str(e)})
        if on_fatal:
            on_fatal()
        raise


async def add(persona: Persona) -> Agent:
    agent = Agent(persona, {"telegram": telegram, "discord": discord, "web": web})
    _agents[persona.id] = agent
    await agent.start()
    return agent


async def remove(persona_id: str) -> None:
    agent = _agents.pop(persona_id, None)
    if agent:
        await agent.stop()


async def restart(persona_id: str) -> Agent | None:
    agent = _agents.get(persona_id)
    if not agent:
        return None
    p = agent.persona
    await remove(persona_id)
    if p.status != "active":
        logger.info("Restart skipped — persona not active", {"persona": p})
        return None
    return await add(p)
