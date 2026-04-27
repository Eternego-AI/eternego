"""Web — browser-facing channel.

The Connection is a passive main-thread adapter. Per-persona broadcast
hubs hold subscribed send callbacks (browser WebSockets). Inbound
messages fire observer signals for agent subscribers to pick up.
"""

import inspect
import json

from application.platform.observer import Message as MessageSignal, dispatch


class Connection:
    """Web platform adapter. Main-thread, passive."""

    def __init__(self):
        self._hubs: dict[str, dict] = {}
        self._stopped = False

    async def send(self, token, persona_id, text):
        hub = self._hubs.get(persona_id)
        if not hub:
            return
        data = json.dumps({"type": "chat_message", "persona_id": persona_id, "content": text})
        for sub in list(hub["subscribers"]):
            try:
                result = sub(data)
                if inspect.iscoroutine(result):
                    await result
            except Exception:
                if sub in hub["subscribers"]:
                    hub["subscribers"].remove(sub)

    async def typing(self, token, persona_id):
        pass

    def open_gateway(self, channel):
        self._hubs.setdefault(channel.name, {"subscribers": []})

    def close_gateway(self, token):
        hub = self._hubs.pop(token, None)
        if hub:
            hub["subscribers"].clear()

    def stop(self):
        self._stopped = True
        self._hubs.clear()

    def subscribe(self, persona_id, callback):
        self._hubs.setdefault(persona_id, {"subscribers": []})["subscribers"].append(callback)

    def unsubscribe(self, persona_id, callback):
        hub = self._hubs.get(persona_id)
        if hub and callback in hub["subscribers"]:
            hub["subscribers"].remove(callback)

    def dispatch_message(self, persona_id, content):
        dispatch(MessageSignal("Web message received", {
            "persona_id": persona_id,
            "content": content,
        }))

    def dispatch_media(self, persona_id, source, caption):
        dispatch(MessageSignal("Web media received", {
            "persona_id": persona_id,
            "content": caption,
            "attachment_path": source,
        }))
