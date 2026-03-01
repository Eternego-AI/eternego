"""Limited — say-only thinking when tool permissions are pending."""

from application.core.data import Persona
from application.core.brain.data import Perception, Meaning, Step


class Limited:
    """Used by tick after legalize fails.

    think() receives a pre-built Meaning(["say"]) and the not_granted tools,
    calls the model with the thread context and permission limitation in the
    system prompt, and returns the say plan for tick to execute.
    """

    async def think(
        self,
        persona: Persona,
        perception: Perception,
        meaning: Meaning,
        not_granted: list[str],
        closed: list | None = None,
    ) -> list[Step]:
        from application.core.brain import ego, current
        from application.platform import logger
        logger.info("thinking.Limited.think", {"persona_id": persona.id, "not_granted": not_granted})

        signals_text = "\n".join(
            f"  [{s.id}] [{s.prompt.role}{' via ' + s.channel.name if s.channel else ''} at {s.created_at.strftime('%H:%M')}] {s.prompt.content}"
            for s in perception.thread.signals
        )
        prompt = "\n".join([
            f"Conversation:\n{signals_text}\n",
            "Allowed tools: say\n",
            "Plan how to communicate the permission issue naturally, given the context of this conversation.",
            'Return JSON: {"steps": [{"number": 1, "tool": "say", "params": {}}]}',
        ])
        system = "\n\n".join(filter(None, [
            current.situation(persona, meaning),
            f"You cannot proceed because these tools require permission: {', '.join(not_granted)}. "
            "Communicate this naturally to the person given the context of the conversation.",
        ]))

        response = await ego.reason(persona, prompt, system=system)
        items = response.get("steps") if isinstance(response, dict) else None
        if not isinstance(items, list) or not items:
            logger.warning("thinking.Limited.think: unexpected response", {"persona_id": persona.id})
            return []

        result = []
        for item in items:
            number = item.get("number")
            params = item.get("params") or {}
            if not isinstance(number, int):
                continue
            result.append(Step(number=number, tool="say", params=params))
        return result
