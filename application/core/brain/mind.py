"""Mind — the persona's cognitive state and orchestrator.

One Mind instance per persona. Mind is the single entry point for all
external inputs and runs the full cognitive cycle internally.

Signals accumulate in memory throughout the day. Closed threads (last
signal from assistant) are passed as context to all thinking stages.
Open threads (last signal from user) are what the persona acts on.

_tick() is a long-running loop started once on load. It watches _mode:
  - Wakeup:  fires immediately on load; runs a full cognitive cycle.
  - Normal:  triggered by interrupt(); runs a full cognitive cycle.
  - Rest:    set at end of each cycle; _change_mode starts an idle timer.
             After _IDLE_DELAY, timer fires and transitions to Rethink.
  - Rethink: fired by the idle timer; runs a review cycle to catch
             unfinished commitments.
  - Sleep:   set by sleep(); tick idles. Only Wakeup can exit sleep.

_change_mode() enforces transition rules. Mid-cycle interrupts are
detected by comparing self._mode identity against current_think.

Permissions: two in-memory session lists —
  _pending_permissions: tool names awaiting a decision from the person.
  _allowed_permissions: tool names granted this session (fast-path for legalize).
Each tick tries to resolve pending tools via ego.grant_or_reject using the focused
thread's conversation. Resolved tools move to _allowed or are dropped from pending.
legalize() skips _allowed_permissions tools and checks the rest against permissions.json;
if any tool is not fully granted the plan halts and the person is told what's missing.
grant_permission/reject_permission tools are model-callable to persist strong decisions
across sessions.

Persistence: signals are saved to mind.json via persistent_memory on every interrupt/reflect.
On restart, signals are restored and mode starts as Rest — no processing until a new interrupt
arrives. sleep() clears mind.json after archiving so the next start is fresh.

mind.interrupt(prompt, channel) — urgent signal: wakes tick or interrupts mid-cycle
mind.reflect(prompt)            — passive signal: added to presence, no tick woken
mind.execute(tool, params)      — run any tool directly
mind.next_task(taking)          — peek or consume the next plan step
mind.load(persona)              — the only way to create a Mind
mind.sleep()                    — archive signals, grow; stays in Sleep until restart
"""

import asyncio
from datetime import datetime

from application.core.data import Persona, Prompt, Channel
from application.core.brain.data import Signal, Step, Thinking, Meaning
from application.core.brain.thinking import Normal, Rethink, Wakeup, Sleep, Rest, Limited
from application.core import paths, local_model
from application.platform import logger, processes, persistent_memory


def _signal_to_dict(signal: Signal) -> dict:
    return {
        "id": signal.id,
        "role": signal.prompt.role,
        "content": signal.prompt.content,
        "channel_type": signal.channel.type if signal.channel else None,
        "channel_name": signal.channel.name if signal.channel else None,
        "created_at": signal.created_at.isoformat(),
    }


def _signal_from_dict(d: dict) -> Signal:
    channel = Channel(type=d["channel_type"], name=d.get("channel_name", "")) if d.get("channel_type") else None
    return Signal(
        id=d["id"],
        prompt=Prompt(role=d["role"], content=d["content"]),
        channel=channel,
        created_at=datetime.fromisoformat(d["created_at"]),
    )


def get(persona_id: str) -> "Mind | None":
    """Return the in-process Mind for a persona, or None if not loaded."""
    from application.core import registry
    return registry.get_mind(persona_id)


class Mind:
    _IDLE_DELAY = 300  # seconds of inactivity before idle review fires

    def __init__(self, persona: Persona):
        self._persona_id = persona.id
        self._plan: list[Step] = []
        self._pending_permissions: list[str] = []   # tool names awaiting a decision this session
        self._allowed_permissions: list[str] = []   # tool names granted this session
        self._event = asyncio.Event()
        self._idle_task: asyncio.Task | None = None
        self._stage_task: asyncio.Task | None = None

        persistent_memory.load(self._storage_id, paths.mind(persona.id))
        self.signals: list[Signal] = [_signal_from_dict(d) for d in persistent_memory.read(self._storage_id)]

        if self.signals:
            self.__mode: Thinking = Rest()  # restored signals — wait for a new interrupt
        else:
            self.__mode: Thinking = Wakeup()
            self._event.set()  # fresh start — Wakeup fires immediately

    @property
    def _storage_id(self) -> str:
        return f"mind_{self._persona_id}"

    @property
    def _mode(self) -> Thinking:
        return self.__mode

    def _change_mode(self, value: Thinking) -> None:
        """Change mode, enforcing allowed transitions.

        Sleep mode is protected: only Wakeup can replace it.
        Setting Rest starts the idle timer; any other transition cancels it.
        """
        if isinstance(self._mode, Sleep) and not isinstance(value, Wakeup):
            logger.info("mind._change_mode: blocked during sleep", {"persona_id": self._persona_id, "attempted": type(value).__name__})
            return
        if self._idle_task is not None:
            self._idle_task.cancel()
            self._idle_task = None
        if self._stage_task is not None and not self._stage_task.done():
            self._stage_task.cancel()
            self._stage_task = None
        self.__mode = value
        self._event.set()
        if isinstance(value, Rest):
            self._idle_task = asyncio.create_task(self._idle_rethink())

    async def _idle_rethink(self) -> None:
        """After IDLE_DELAY of rest, transition to Rethink."""
        try:
            await asyncio.sleep(self._IDLE_DELAY)
            logger.info("mind._idle_rethink: idle delay elapsed", {"persona_id": self._persona_id})
            self._change_mode(Rethink())
        except asyncio.CancelledError:
            pass

    @classmethod
    def load(cls, persona: Persona) -> "Mind":
        """Create a fresh Mind for this persona and register it in-process."""
        from application.core import registry
        mind = cls(persona)
        registry.save(persona, mind)
        processes.run_async(mind._tick)
        return mind

    @property
    def persona(self) -> Persona:
        """Return the live persona from the registry."""
        from application.core import registry
        return registry.get_persona(self._persona_id)

    # ── Public ────────────────────────────────────────────────────────────

    def interrupt(self, prompt: Prompt, channel: Channel | None = None) -> None:
        """Add an urgent signal and set mode to Normal, waking the tick loop."""
        signal = Signal(prompt=prompt, channel=channel)
        self.signals.append(signal)
        persistent_memory.append(self._storage_id, _signal_to_dict(signal))
        self._change_mode(Normal(signal))
        logger.info("mind.interrupt", {"persona_id": self._persona_id})

    def reflect(self, prompt: Prompt) -> None:
        """Add a passive signal to presence without starting a tick."""
        signal = Signal(prompt=prompt)
        self.signals.append(signal)
        persistent_memory.append(self._storage_id, _signal_to_dict(signal))
        logger.info("mind.reflect", {"persona_id": self._persona_id})

    async def execute(self, tool_name: str, params: dict) -> str:
        """Run a single tool. Reflects on success; interrupts on failure."""
        from application.core.brain import tools
        logger.info("mind.execute", {"persona_id": self._persona_id, "tool": tool_name})
        persona = self.persona
        tool = tools.for_name(tool_name)
        if tool is None:
            self.interrupt(Prompt(role="user", content=f"[{tool_name}] failed: unknown tool"))
            return f"error: unknown tool '{tool_name}'"
        try:
            fn = tool.execution(**params)
            output = await fn(persona)
            # reflect tool calls mind.interrupt internally — don't double-reflect
            if tool_name != "reflect":
                self.reflect(Prompt(role="assistant", content=f"[{tool_name}] {output}"))
            return output
        except Exception as e:
            error = str(e)
            self.interrupt(Prompt(role="user", content=f"[{tool_name}] failed: {error}"))
            return f"error: {error}"

    def present(self) -> list[Signal]:
        """Return all signals — the full day's presence."""
        return list(self.signals)

    def next_task(self, taking: bool = False) -> Step | None:
        """Return the next plan step, or None if the plan is exhausted."""
        if not self._plan:
            return None
        if taking:
            return self._plan.pop(0)
        return self._plan[0]

    # ── Internal ─────────────────────────────────────────────────────────

    async def _think(self, coro):
        """Run a coroutine as a cancellable stage task.

        When _change_mode cancels _stage_task, CancelledError propagates through
        the await chain all the way to the Ollama HTTP connection, closing it.
        Returns None if cancelled so _tick can detect the mode change gracefully.
        """
        self._stage_task = asyncio.create_task(coro)
        try:
            return await self._stage_task
        except asyncio.CancelledError:
            return None
        finally:
            self._stage_task = None

    async def _tick(self) -> None:
        """Long-running loop: wait for _mode, dispatch on type, repeat."""
        from application.core.brain import ego

        while True:
            await self._event.wait()
            self._event.clear()
            mode = self._mode

            current_think = mode
            persona = self.persona
            self._plan = []
            logger.info("mind._tick", {"persona_id": self._persona_id, "mode": type(current_think).__name__})

            try:
                signals = self.present()
                if not signals:
                    continue

                threads = await self._think(ego.realize(persona, signals))
                if not threads:
                    continue

                if self._mode is not current_think:
                    continue
                perceptions = await self._think(current_think.understanding(persona, threads))
                if not perceptions:
                    continue
                perception = perceptions[0]
                closed = [t for t in threads if t is not perception.thread]

                # Resolve any pending permissions using the focused thread's conversation
                if self._pending_permissions:
                    decisions = await self._think(ego.grant_or_reject(persona, self._pending_permissions, perception.thread.signals))
                    for tool_name in decisions.get("granted", []):
                        self._allowed_permissions.append(tool_name)
                        self._pending_permissions = [t for t in self._pending_permissions if t != tool_name]
                    for tool_name in decisions.get("rejected", []):
                        self._pending_permissions = [t for t in self._pending_permissions if t != tool_name]

                if self._mode is not current_think:
                    continue
                meaning = await self._think(current_think.focus(persona, perception, closed))
                if not meaning.tools:
                    meaning.tools = ["say"]

                if self._mode is not current_think:
                    continue
                thought = await self._think(current_think.think(persona, perception, meaning, closed))
                if not thought:
                    continue
                meaning.path = thought
                self._plan = thought
                paths.append_meaning_path(
                    persona.id, meaning.title,
                    meaning.tools,
                    [s.tool for s in meaning.path],
                )

                if self._mode is not current_think:
                    continue
                from application.core.brain import tools as brain_tools
                plan_to_check = [
                    s for s in self._plan
                    if s.tool not in self._allowed_permissions
                    and (t := brain_tools.for_name(s.tool)) is not None
                    and t.requires_permission
                ]
                permission = await self._think(ego.legalize(persona, plan_to_check))
                not_granted = (permission or {}).get("rejected", []) + (permission or {}).get("unknown", [])
                if not_granted:
                    logger.info("mind._tick: permission required", {"persona_id": self._persona_id, "not_granted": not_granted})
                    for t in not_granted:
                        if t not in self._pending_permissions:
                            self._pending_permissions.append(t)
                    limited_meaning = Meaning(perception.thread.title, ["say"])
                    thought = await self._think(Limited().think(persona, perception, limited_meaning, not_granted, closed))
                    if not thought:
                        continue
                    self._plan = thought

                while self._mode is current_think:
                    step = self.next_task(taking=True)
                    if step is None:
                        break
                    await self.execute(step.tool, step.params)

            except Exception as e:
                logger.warning("mind._tick: unhandled error", {"persona_id": self._persona_id, "error": str(e)})
                continue

            # Cycle complete — rest until idle timer fires Rethink
            self._change_mode(Rest())

    async def sleep(self) -> None:
        """Archive the day's signals and grow. Stays in Sleep until restart."""
        from application.core.brain import ego
        logger.info("mind.sleep", {"persona_id": self._persona_id})
        self._change_mode(Sleep())
        persona = self.persona
        signals = self.present()
        if signals:
            threads = await ego.realize(persona, signals)
            for thread in threads:
                summary = await ego.recap(persona, thread.signals, "")
                signal_ids = [s.id for s in thread.signals]
                await self.execute("archive", {"signal_ids": signal_ids, "title": thread.title, "recap": summary})
            logger.info("mind.sleep: consolidated", {"persona_id": self._persona_id, "threads": len(threads)})
        persistent_memory.clear(self._storage_id)
        await self._grow()

    async def _grow(self) -> None:
        """Evolve DNA, generate per-item training pairs, and fine-tune."""
        import json
        from application.core import frontier, local_inference_engine, models, prompts
        from application.core.exceptions import DNAError
        from application.platform import strings
        persona = self.persona
        logger.info("mind._grow", {"persona_id": self._persona_id})

        synthesis = prompts.dna_synthesis(
            previous_dna=paths.read(paths.dna(persona.id)),
            person_traits=paths.read(paths.person_traits(persona.id)),
            persona_context=paths.read(paths.context(persona.id)),
            history_briefing=paths.read_history_brief(persona.id, "(no history yet)"),
        )
        if persona.frontier:
            try:
                new_dna = await frontier.chat(persona.frontier, synthesis)
            except Exception as e:
                logger.warning("mind._grow: frontier failed for DNA synthesis, falling back to local model", {"persona_id": self._persona_id, "error": str(e)})
                new_dna = await local_model.generate(persona.model.name, synthesis)
        else:
            new_dna = await local_model.generate(persona.model.name, synthesis)
        paths.write_dna(persona.id, new_dna)

        dna_items = [line.strip() for line in new_dna.splitlines() if line.strip() and not line.strip().startswith("#")]
        all_pairs = []
        for item in dna_items:
            item_prompt = prompts.grow(dna=item, max_pairs=5)
            if persona.frontier:
                try:
                    response = await frontier.chat(persona.frontier, item_prompt)
                except Exception as e:
                    logger.warning("mind._grow: frontier failed for training pair, falling back to local model", {"persona_id": self._persona_id, "error": str(e)})
                    response = await local_model.generate(persona.model.name, item_prompt, json_mode=True)
            else:
                response = await local_model.generate(persona.model.name, item_prompt, json_mode=True)
            try:
                parsed = strings.extract_json(response)
            except json.JSONDecodeError:
                parsed = {}
            if parsed and "training_pairs" in parsed:
                all_pairs.extend(parsed["training_pairs"])

        training_set = json.dumps({"training_pairs": all_pairs}, indent=2)
        paths.add_training_set(persona.id, training_set)

        old_model = persona.model.name
        new_model = models.generate(persona.base_model, persona.id)
        await local_inference_engine.fine_tune(persona.base_model, training_set, new_model.name)

        if not await local_inference_engine.check(new_model.name):
            raise DNAError("Fine-tuned model failed verification — previous model is still active")

        await local_inference_engine.delete(old_model)
        paths.clear(paths.person_traits(persona.id))

        persona.model = new_model
        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)
