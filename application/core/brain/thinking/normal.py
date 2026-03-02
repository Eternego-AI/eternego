"""Normal — triggered by an urgent incoming signal."""

from application.core.data import Persona
from application.core.brain.data import Signal, Thread, Perception, Meaning, Step
from application.core.brain.data import Thinking


class Normal(Thinking):
    """Normal thinking mode: triggered by an urgent incoming signal."""

    def __init__(self, signal: Signal):
        self.signal = signal

    async def understanding(self, persona: Persona, threads: list[Thread]) -> list[Perception] | None:
        from application.core.brain.signals import classify
        from application.core.brain import ego, current

        active, closed = classify(threads)
        if not active:
            return None
        if len(active) == 1:
            return [Perception(thread=active[0], order=0)]

        lines = [
            "These are your open threads — conversations still waiting for your response.",
            "Order them by priority: most recent first, then by what is most urgent or logically the next step given where each thread stands.",
            'Return JSON: {"order": [2, 0, 1]} — 0-based indices, most important first.\n',
        ]
        for i, t in enumerate(active):
            last = t.signals[-1]
            time = last.created_at.strftime("%H:%M")
            lines.append(f"{i}. [{time}] {t.title} — last: {last.prompt.content[:120]}")
        prompt = "\n".join(lines)

        if closed:
            context = ["Today's context (threads already addressed today, for reference):"]
            for t in closed:
                context.append(f"- {t.title}: {t.signals[-1].prompt.content[:120]}")
            context.append("")
            response = await ego.reason(persona, "\n".join(context) + "\n" + prompt, system=current.time())
        else:
            response = await ego.reason(persona, prompt, system=current.time())

        indices = response.get("order") if isinstance(response, dict) else None
        if not isinstance(indices, list):
            return [Perception(thread=t, order=i) for i, t in enumerate(active)]

        seen = set()
        result = []
        for order, i in enumerate(indices):
            if isinstance(i, int) and 0 <= i < len(active) and i not in seen:
                result.append(Perception(thread=active[i], order=order))
                seen.add(i)
        for i, t in enumerate(active):
            if i not in seen:
                result.append(Perception(thread=t, order=len(result)))
        return result or None

    async def focus(self, persona: Persona, perception: Perception, closed: list[Thread] | None = None) -> Meaning:
        from application.core.brain import ego, current, tools as brain_tools
        from application.platform import logger
        logger.info("thinking.Normal.focus", {"persona_id": persona.id, "thread": perception.thread.title})

        tool_list = current.tools()
        skill_list = current.skills(persona)
        signals_text = "\n".join(
            f"  [{s.id}] [{s.prompt.role}{' via ' + s.channel.name if s.channel else ''} at {s.created_at.strftime('%H:%M')}] {s.prompt.content}"
            for s in perception.thread.signals
        )
        lines = [
            f"Thread: {perception.thread.title}\n{signals_text}\n",
            "Read this thread. What is actually happening here, and what do you need to engage with it fully — as yourself?",
            "Choose the tools and skills that give you what you need.\n",
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
        prompt = "\n".join(lines)

        if closed:
            context = ["Today's context (threads already addressed today, for reference):"]
            for t in closed:
                context.append(f"- {t.title}: {t.signals[-1].prompt.content[:120]}")
            context.append("")
            response = await ego.reason(persona, "\n".join(context) + "\n" + prompt, system=current.time())
        else:
            response = await ego.reason(persona, prompt, system=current.time())

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

    async def think(self, persona: Persona, perception: Perception, meaning: Meaning, closed: list[Thread] | None = None) -> list[Step]:
        from application.core.brain import ego, current, tools as brain_tools
        from application.platform import logger
        logger.info("thinking.Normal.think", {"persona_id": persona.id, "thread": perception.thread.title, "tools": meaning.tools})

        signals_text = "\n".join(
            f"  [{s.id}] [{s.prompt.role}{' via ' + s.channel.name if s.channel else ''} at {s.created_at.strftime('%H:%M')}] {s.prompt.content}"
            for s in perception.thread.signals
        )
        last_user = next((s for s in reversed(perception.thread.signals) if s.prompt.role == "user"), None)
        focal = f"\nMessage [{last_user.id}] is waiting for your reply." if last_user else ""
        allowed = ", ".join(meaning.tools) if meaning.tools else "say"
        prompt = "\n".join([
            f"Conversation:\n{signals_text}{focal}\n",
            f"You have these tools: {allowed}\n",
            "How do you want to handle this? Plan your steps.",
            'Return JSON: {"steps": [{"number": 1, "tool": "...", "params": {...}}]}',
        ])

        if closed:
            context = ["Today's context (threads already addressed today, for reference):"]
            for t in closed:
                context.append(f"- {t.title}: {t.signals[-1].prompt.content[:120]}")
            context.append("")
            response = await ego.reason(persona, "\n".join(context) + "\n" + prompt, system=current.situation(persona, meaning))
        else:
            response = await ego.reason(persona, prompt, system=current.situation(persona, meaning))

        items = response.get("steps") if isinstance(response, dict) else None
        if not isinstance(items, list) or not items:
            logger.warning("thinking.Normal.think: unexpected response", {"persona_id": persona.id})
            return []
        result = []
        for item in items:
            number = item.get("number")
            tool_name = item.get("tool")
            params = item.get("params") or {}
            if not isinstance(number, int) or not tool_name:
                continue
            if brain_tools.for_name(tool_name) is None:
                logger.warning("thinking.Normal.think: unknown tool", {"persona_id": persona.id, "tool": tool_name})
                continue
            result.append(Step(number=number, tool=tool_name, params=params))
        return result
