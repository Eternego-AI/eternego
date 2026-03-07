"""Mind — the persona's cognitive state.

One Mind instance per persona, loaded once at startup.

answer(cause)      add occurrence, run tick in background, return immediate response.
interrupt(prompt)  add occurrence from prompt, run tick in background (fire-and-forget).
clear()            clear all occurrences from memory and persistent store.

Cognitive tick:
  1. ego.realize(occurrences)          → threads (awareness)
  2. ego.understand(threads)           → ordered perceptions with impressions
  3. ego.grant_or_reject(pending)      → resolve pending permissions from conversation
  4. ego.decide(top perception)        → plan steps (calls focus internally)
  5. ego.legalize(plan)                → permissions check
  6. execute steps — each result becomes an Occurrence:
       success → Occurrence(cause="[tool]: output", effect="")
       failure → Occurrence(cause="[tool] failed: error", effect="")
       reflect → inject text as Occurrence, restart tick
  7. re-tick so the model sees results and decides: continue, retry, or close
  8. tick ends when decide returns nothing — recap the perception and stop

Persistence: occurrences are saved to mind.json on every update.
On restart, occurrences are restored and the next interrupt resumes from where things left off.
"""

import asyncio
from datetime import datetime

from application.core.brain.data import Occurrence
from application.core.data import Persona, Prompt
from application.core.brain import ego
from application.core import paths
from application.core.exceptions import MindError
from application.platform import logger, persistent_memory


class Mind:

    def __init__(self, persona: Persona):
        self._persona_id = persona.id
        self._tick_task: asyncio.Task | None = None
        self._pending_permissions: list[str] = []

        try:
            persistent_memory.load(self._storage_id, paths.mind(persona.id))
        except Exception as e:
            raise MindError(f"Failed to load mind storage: {e}") from e
        self.occurrences: list[Occurrence] = [
            Occurrence(
                id=d["id"],
                cause=Prompt(role=d["cause"]["role"], content=d["cause"]["content"]),
                effect=Prompt(role=d["effect"]["role"], content=d["effect"]["content"]),
                created_at=datetime.fromisoformat(d["cause"]["time"]),
            )
            for d in persistent_memory.read(self._storage_id)
        ]

    @property
    def _storage_id(self) -> str:
        return f"mind_{self._persona_id}"

    @property
    def persona(self) -> Persona:
        from application.core import registry
        return registry.get_persona(self._persona_id)

    @classmethod
    def load(cls, persona: Persona) -> "Mind":
        """Create and register a Mind for this persona."""
        m = cls(persona)
        from application.core import registry
        registry.save(persona, m)
        logger.info("mind.load", {"persona_id": persona.id, "restored": len(m.occurrences)})
        return m

    def _persist(self, occurrence: Occurrence) -> None:
        try:
            persistent_memory.append(self._storage_id, {
                "id": occurrence.id,
                "cause": {"role": occurrence.cause.role, "content": occurrence.cause.content, "time": occurrence.created_at.isoformat()},
                "effect": {"role": occurrence.effect.role, "content": occurrence.effect.content, "time": occurrence.created_at.isoformat()},
            })
        except Exception as e:
            raise MindError(f"Failed to persist occurrence: {e}") from e

    def clear(self) -> None:
        """Clear all occurrences from memory and persistent store."""
        self.occurrences = []
        persistent_memory.clear(self._storage_id)

    async def answer(self, cause: Prompt) -> str:
        """Stop tick, generate response, record occurrence, resume tick."""
        await self._change_mindset(cause)

        effect_text = await ego.response(self.persona, cause)

        await self._change_mindset(cause, Prompt(role="assistant", content=effect_text))
        return effect_text

    def interrupt(self, prompt: Prompt) -> None:
        """Add an occurrence from a prompt and start a fresh tick."""
        occurrence = Occurrence(
            cause=prompt,
            effect=Prompt(role="assistant", content=""),
        )
        self.occurrences.append(occurrence)
        self._persist(occurrence)
        self._start_tick()

    async def _change_mindset(self, cause: Prompt, effect: Prompt | None = None) -> None:
        """Called with cause only: stop tick. Called with cause+effect: record occurrence and start tick."""
        if effect is None:
            if self._tick_task and not self._tick_task.done():
                self._tick_task.cancel()
                try:
                    await self._tick_task
                except (asyncio.CancelledError, Exception):
                    pass
        else:
            occurrence = Occurrence(cause=cause, effect=effect)
            self.occurrences.append(occurrence)
            self._persist(occurrence)
            self._start_tick()

    def _start_tick(self) -> None:
        """Cancel any running tick and start a fresh one."""
        if self._tick_task and not self._tick_task.done():
            self._tick_task.cancel()
        self._tick_task = asyncio.create_task(self._run_tick())

    async def _run_tick(self) -> None:
        try:
            await self._tick()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("mind._run_tick: unhandled error", {"persona_id": self._persona_id, "error": str(e)})

    async def _tick(self) -> None:
        """One full cognitive cycle. Re-ticks after execution so model can continue or close."""
        occurrences = list(self.occurrences)
        if not occurrences:
            return

        threads = await ego.realize(self.persona, occurrences)
        if not threads:
            return

        perceptions = await ego.understand(self.persona, threads)
        if not perceptions:
            return

        perception = perceptions[0]
        closed = [t for t in threads if t is not perception.thread]

        # Resolve any pending permissions using the focused thread's conversation
        if self._pending_permissions:
            resolved = await ego.grant_or_reject(
                self.persona, self._pending_permissions, perception.thread.occurrences
            )
            for tool in resolved.get("granted", []) + resolved.get("rejected", []):
                if tool in self._pending_permissions:
                    self._pending_permissions.remove(tool)

        thought = await ego.decide(self.persona, perception, closed)
        if not thought:
            recap_text = await ego.recap(self.persona, perception.thread.occurrences, "")
            perception.result = recap_text
            closing = Occurrence(
                cause=Prompt(role="assistant", content=f"[closed]: {recap_text}"),
                effect=Prompt(role="assistant", content=""),
            )
            self.occurrences.append(closing)
            self._persist(closing)
            return

        from application.core.brain import tools as brain_tools
        plan_to_check = [
            s for s in thought.steps
            if (t := brain_tools.for_name(s.tool)) is not None and t.requires_permission
        ]
        permission = await ego.legalize(self.persona, plan_to_check)
        not_granted = (permission or {}).get("rejected", []) + (permission or {}).get("unknown", [])

        if not_granted:
            for tool in not_granted:
                if tool not in self._pending_permissions:
                    self._pending_permissions.append(tool)
            thought = await ego.deny(self.persona, perception, not_granted, closed)
            if not thought:
                return

        executed = False
        for step in thought.steps:
            tool = brain_tools.for_name(step.tool)
            if tool is None:
                logger.warning("mind._tick: unknown tool", {"persona_id": self._persona_id, "tool": step.tool})
                continue

            if step.tool == "reflect":
                reflect_text = step.params.get("text", "")
                if reflect_text:
                    occurrence = Occurrence(
                        cause=Prompt(role="user", content=reflect_text),
                        effect=Prompt(role="assistant", content=""),
                    )
                    self.occurrences.append(occurrence)
                    self._persist(occurrence)
                await self._tick()
                return

            try:
                output = await tool.execution(**step.params)(self.persona)
                occurrence = Occurrence(
                    cause=Prompt(role="user", content=f"[{step.tool}]: {output}"),
                    effect=Prompt(role="assistant", content=""),
                )
                self.occurrences.append(occurrence)
                self._persist(occurrence)
                executed = True
            except Exception as e:
                logger.warning("mind._tick: tool error", {"persona_id": self._persona_id, "tool": step.tool, "error": str(e)})
                occurrence = Occurrence(
                    cause=Prompt(role="user", content=f"[{step.tool}] failed: {e}"),
                    effect=Prompt(role="assistant", content=""),
                )
                self.occurrences.append(occurrence)
                self._persist(occurrence)
                executed = True

        if executed:
            await self._tick()
