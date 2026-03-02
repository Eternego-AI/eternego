"""Rethink — idle review mode, set at the end of each Normal cycle."""

from application.core.data import Persona
from application.core.brain.data import Thread, Perception, Meaning, Step, Thought
from application.core.brain.data import Thinking


class Rethink(Thinking):
    """Rethink mode: set by the tick itself at the end of a cycle.

    No signal — the tick proactively waits _IDLE_DELAY, then runs a
    review cycle to catch unfinished commitments.
    """

    async def understanding(self, persona: Persona, threads: list[Thread]) -> list[Perception] | None:
        from application.core.brain import ego

        if not threads:
            return None
        if len(threads) == 1:
            return [Perception(thread=threads[0], order=0)]

        lines = [
            "Review today's threads and look for ones that are genuinely open — not yet at closure.",
            "A thread needs follow-up if: (a) you made a commitment or took on a task you haven't delivered yet, or (b) you asked the person something and are still waiting for their response.",
            "A thread is closed if the matter was resolved, or you said what needed to be said and the person acknowledged it.",
            "Order open threads by urgency — most urgent first. Return an empty list if everything is settled.",
            'Return JSON: {"order": [2, 0, 1]} — 0-based indices.\n',
        ]
        for i, t in enumerate(threads):
            last = t.signals[-1] if t.signals else None
            time = last.created_at.strftime("%H:%M") if last else ""
            role = last.prompt.role if last else ""
            content = last.prompt.content[:120] if last else ""
            lines.append(f"{i}. [{time}] {t.title} — last from {role}: {content}")

        response = await ego.reason(persona, "\n".join(lines))
        indices = response.get("order") if isinstance(response, dict) else None
        if not isinstance(indices, list) or not indices:
            return None

        seen = set()
        result = []
        for order, i in enumerate(indices):
            if isinstance(i, int) and 0 <= i < len(threads) and i not in seen:
                result.append(Perception(thread=threads[i], order=order))
                seen.add(i)
        for i, t in enumerate(threads):
            if i not in seen:
                result.append(Perception(thread=t, order=len(result)))
        return result or None

    async def focus(self, persona: Persona, perception: Perception, closed: list[Thread] | None = None) -> Meaning:
        from application.core.brain import ego, current, tools as brain_tools
        from application.platform import logger
        logger.info("thinking.Rethink.focus", {"persona_id": persona.id, "thread": perception.thread.title})

        tool_list = current.tools()
        skill_list = current.skills(persona)
        signals_text = "\n".join(
            f"  [{s.id}] [{s.prompt.role}{' via ' + s.channel.name if s.channel else ''} at {s.created_at.strftime('%H:%M')}] {s.prompt.content}"
            for s in perception.thread.signals
        )
        lines = [
            f"Thread: {perception.thread.title}\n{signals_text}\n",
            "Revisit this thread. Is there something still open — a commitment you haven't fulfilled, a question unanswered, something the person is waiting on?",
            "Choose the tools and skills you would need to act on it.\n",
            'Return JSON: {"tools": ["tool_name", ...], "skills": ["skill_name", ...]}\n',
            "Available tools:",
        ]
        for t in tool_list:
            if t.description:
                lines.append(f"- {t.name}: {t.description}")
        if skill_list:
            lines.append("\nAvailable skills:")
            for s in skill_list:
                if s.description:
                    lines.append(f"- {s.name}: {s.description}")

        response = await ego.reason(persona, "\n".join(lines), system=current.time())

        if not isinstance(response, dict):
            return Meaning(perception.thread.title)
        selected_tools = response.get("tools") or []
        selected_skills = response.get("skills") or []
        if not isinstance(selected_tools, list):
            return Meaning(perception.thread.title)
        valid_skill_names = {s.name for s in current.skills(persona)}
        valid_tools = [t for t in selected_tools if isinstance(t, str) and brain_tools.for_name(t) is not None]
        valid_skills = [s for s in selected_skills if isinstance(s, str) and s in valid_skill_names]
        return Meaning(perception.thread.title, valid_tools, valid_skills)

    async def decide(self, persona: Persona, perception: Perception, meaning: Meaning, closed: list[Thread] | None = None) -> Thought | None:
        from application.core.brain import ego, current, tools as brain_tools
        from application.platform import logger
        logger.info("thinking.Rethink.decide", {"persona_id": persona.id, "thread": perception.thread.title, "tools": meaning.tools})

        signals_text = "\n".join(
            f"  [{s.id}] [{s.prompt.role}{' via ' + s.channel.name if s.channel else ''} at {s.created_at.strftime('%H:%M')}] {s.prompt.content}"
            for s in perception.thread.signals
        )
        allowed = ", ".join(meaning.tools) if meaning.tools else "say"
        prompt = "\n".join([
            f"Conversation:\n{signals_text}\n",
            f"You have these tools: {allowed}\n",
            "Does this thread still need something from you, or has it reached closure?",
            "If there is nothing left to do, return empty steps. If something is still open, plan what you want to do.",
            'Return JSON: {"steps": [{"number": 1, "tool": "...", "params": {...}}]}',
        ])

        response = await ego.reason(persona, prompt, system=current.situation(persona, meaning))

        items = response.get("steps") if isinstance(response, dict) else None
        if not isinstance(items, list):
            logger.warning("thinking.Rethink.decide: unexpected response", {"persona_id": persona.id})
            return None
        if not items:
            logger.info("thinking.Rethink.decide: thread closed, no steps needed", {"persona_id": persona.id})
            return None
        result = []
        for item in items:
            number = item.get("number")
            tool_name = item.get("tool")
            params = item.get("params") or {}
            if not isinstance(number, int) or not tool_name:
                continue
            if brain_tools.for_name(tool_name) is None:
                logger.warning("thinking.Rethink.decide: unknown tool", {"persona_id": persona.id, "tool": tool_name})
                continue
            result.append(Step(number=number, tool=tool_name, params=params))
        return Thought(meaning=meaning, steps=result) if result else None
