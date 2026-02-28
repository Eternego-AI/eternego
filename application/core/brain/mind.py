"""Mind — the persona's cognitive state and orchestrator.

One Mind instance per persona. Mind is the single entry point for all
external inputs and runs the full cognitive cycle internally.

Signals accumulate in memory throughout the day. Closed threads (last
signal from assistant) are passed as context to all ego stages. Open
threads (last signal from user) are what the persona acts on. Sleep
consolidates and archives the full day.

The tick lock is held for the full cognitive cycle. interrupt() knocks
if the gate is open (starts a tick) or sets the interrupting signal if
the gate is closed (tick is running).

mind.interrupt(prompt, channel) — urgent signal: starts tick if idle, interrupts if busy
mind.reflect(prompt)            — passive signal: added to presence, no tick started
mind.execute(tool, params)     — run any tool directly
mind.next_task(taking)          — peek or consume the next plan step
mind.load(persona)              — the only way to create a Mind
grow(persona)                   — evolve DNA, generate training, fine-tune
"""

import asyncio

from application.core.data import Persona, Prompt, Channel
from application.core.brain.data import Signal, Perception, Step
from application.core import paths, local_model
from application.platform import logger, processes


def get(persona_id: str) -> "Mind | None":
    """Return the in-process Mind for a persona, or None if not loaded."""
    from application.core import registry
    return registry.get_mind(persona_id)


class Mind:
    def __init__(self, persona: Persona):
        self._persona_id = persona.id
        self.signals: list[Signal] = []
        self._plan: list[Step] = []
        self._lock = asyncio.Lock()
        self._interrupting_signal: Signal | None = None

    @classmethod
    def load(cls, persona: Persona) -> "Mind":
        """Create a fresh Mind for this persona and register it in-process."""
        from application.core import registry
        mind = cls(persona)
        registry.save(persona, mind)
        return mind

    @property
    def persona(self) -> Persona:
        """Return the live persona from the registry."""
        from application.core import registry
        return registry.get_persona(self._persona_id)

    # ── Public ────────────────────────────────────────────────────────────

    def interrupt(self, prompt: Prompt, channel: Channel | None = None) -> None:
        """Add an urgent signal. Knocks to start tick if idle; sets interrupting signal if busy."""
        signal = Signal(prompt=prompt, channel=channel)
        self.signals.append(signal)
        self._interrupting_signal = signal
        logger.debug("mind.interrupt", {"persona_id": self._persona_id, "locked": self._lock.locked()})
        if not self._lock.locked():
            processes.run_async(self._tick)

    def reflect(self, prompt: Prompt) -> None:
        """Add a passive signal to presence without starting a tick."""
        signal = Signal(prompt=prompt)
        self.signals.append(signal)
        logger.debug("mind.reflect", {"persona_id": self._persona_id})

    async def execute(self, tool_name: str, params: dict) -> str:
        """Run a single tool. Reflects on success; interrupts on failure."""
        from application.core.brain import tools
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

    async def _tick(self) -> None:
        """Full cognitive cycle: realize → split closed/open → understand → focus → think → execute."""
        from application.core.brain import ego, signals as brain_signals
        from application.core import channels

        async with self._lock:
            self._interrupting_signal = None  # reset: triggering signal is already in signals

            persona = self.persona
            if persona is None:
                return

            perception: Perception | None = None
            meaning = None
            self._plan = []
            channel = channels.default_channel(persona)

            try:
                signals = self.present()
                if not signals:
                    return

                if channel:
                    await channels.in_progress(channel)
                logger.debug("mind._tick: realizing", {"persona_id": self._persona_id, "signals": len(signals)})
                all_perceptions = await ego.realize(persona, signals)
                if not all_perceptions:
                    logger.debug("mind._tick: no perceptions, exiting", {"persona_id": self._persona_id})
                    return

                open_perceptions, closed = brain_signals.classify(all_perceptions)
                if not open_perceptions:
                    logger.debug("mind._tick: no open threads, nothing to do", {"persona_id": self._persona_id})
                    return

                if self._interrupting_signal is None:
                    if channel:
                        await channels.in_progress(channel)
                    logger.debug("mind._tick: understanding", {"persona_id": self._persona_id, "open": len(open_perceptions), "closed": len(closed)})
                    awareness = await ego.understand(persona, open_perceptions, closed)
                    if not awareness:
                        logger.debug("mind._tick: no awareness, exiting", {"persona_id": self._persona_id})
                        return
                    perception = awareness[0]

                # Resolve pending permission if signals have arrived after the request
                if self._interrupting_signal is None and perception is not None:
                    pending_idx = next(
                        (i for i, s in enumerate(perception.thread.signals) if s.pending_permission),
                        None,
                    )
                    if pending_idx is not None:
                        subsequent = perception.thread.signals[pending_idx + 1:]
                        if subsequent:
                            pending_signal = perception.thread.signals[pending_idx]
                            decisions = await ego.grant_or_reject(
                                persona, pending_signal.pending_permission, subsequent,
                            )
                            await self._authorize(persona, pending_signal, decisions)

                if self._interrupting_signal is None and perception is not None:
                    if channel:
                        await channels.in_progress(channel)
                    logger.debug("mind._tick: focusing", {"persona_id": self._persona_id})
                    meaning = await ego.focus(persona, perception, closed)
                    if not meaning.tools:
                        meaning.tools = ["say"]

                if self._interrupting_signal is None and meaning is not None:
                    if channel:
                        await channels.in_progress(channel)
                    logger.debug("mind._tick: thought", {"persona_id": self._persona_id, "tools": meaning.tools})
                    thought = await ego.think(persona, perception, meaning, closed)
                    if not thought:
                        logger.debug("mind._tick: no thought, exiting", {"persona_id": self._persona_id})
                        return
                    meaning.path = thought
                    self._plan = thought
                    paths.append_meaning_path(
                        persona.id, meaning.title,
                        meaning.tools,
                        [s.tool for s in meaning.path],
                    )

                # Legalize: check which steps require permission
                if self._interrupting_signal is None and perception is not None:
                    blocked = await ego.legalize(persona, self._plan)
                    if blocked:
                        logger.debug("mind._tick: blocked by permissions", {"persona_id": self._persona_id, "blocked": blocked})
                        if perception.thread.signals:
                            perception.thread.signals[-1].pending_permission = blocked
                        self.signals.append(Signal(
                            prompt=Prompt(
                                role="user",
                                content=(
                                    f"You are not allowed to run: {', '.join(blocked)}. "
                                    "Let the person know and ask if they want to grant permission."
                                ),
                            )
                        ))
                        processes.run_async(self._tick)
                        return

                logger.debug("mind._tick: executing", {"persona_id": self._persona_id, "steps": len(self._plan)})
                while self._interrupting_signal is None:
                    step = self.next_task(taking=True)
                    if step is None:
                        break
                    logger.debug("mind._tick: running tool", {"persona_id": self._persona_id, "tool": step.tool})
                    await self.execute(step.tool, step.params)

            except Exception as e:
                logger.warning("mind._tick: unhandled error", {"persona_id": self._persona_id, "error": str(e)})

        # An interrupt may have arrived while the lock was held — restart so it is not stranded.
        if self._interrupting_signal is not None:
            processes.run_async(self._tick)

    async def _authorize(self, persona: Persona, pending_signal: Signal, decisions: dict) -> None:
        """Write grant/reject decisions to permissions.md and signal the outcome."""
        from application.platform import filesystem
        p = paths.permissions(persona.id)
        for t in decisions.get("granted", []):
            filesystem.append(p, f"granted: {t}\n")
        for t in decisions.get("rejected", []):
            filesystem.append(p, f"rejected: {t}\n")
        granted = decisions.get("granted", [])
        rejected = decisions.get("rejected", [])
        if granted or rejected:
            pending_signal.pending_permission = []
            parts = []
            if granted:
                parts.append(f"permission granted for: {', '.join(granted)}")
            if rejected:
                parts.append(f"permission rejected for: {', '.join(rejected)}")
            self.interrupt(Prompt(role="user", content="; ".join(parts)))

# ── Consolidation ─────────────────────────────────────────────────────────────

async def consolidate(persona: Persona) -> None:
    """Archive the full day's signals at sleep time.

    Groups all accumulated signals into threads, recaps each thread,
    then delegates writing and signal removal to the archive tool.
    """
    from application.core.brain import ego

    m = get(persona.id)
    if m is None:
        logger.warning("mind.consolidate: mind not loaded", {"persona_id": persona.id})
        return

    signals = m.present()
    if not signals:
        logger.debug("mind.consolidate: no signals to archive", {"persona_id": persona.id})
        return

    logger.info("mind.consolidate: archiving day's signals", {"persona_id": persona.id, "signals": len(signals)})
    all_perceptions = await ego.realize(persona, signals)

    for perception in all_perceptions:
        summary = await ego.recap(persona, perception.thread.signals, "")
        signal_ids = [s.id for s in perception.thread.signals]
        await m.execute("archive", {"signal_ids": signal_ids, "title": perception.title, "recap": summary})

    logger.info("mind.consolidate: done", {"persona_id": persona.id, "threads": len(all_perceptions)})


# ── Growth ────────────────────────────────────────────────────────────────────

async def grow(persona: Persona) -> None:
    """Evolve DNA, generate per-item training pairs, fine-tune, and wake up."""
    import json
    from application.core import frontier, local_inference_engine, models, prompts
    from application.core.exceptions import DNAError
    from application.platform import strings

    logger.info("mind.grow: growing persona", {"persona_id": persona.id})

    synthesis = prompts.dna_synthesis(
        previous_dna=paths.read(paths.dna(persona.id)),
        person_traits=paths.read(paths.person_traits(persona.id)),
        persona_context=paths.read(paths.context(persona.id)),
        history_briefing=paths.read_history_brief(persona.id, "(no history yet)"),
    )
    if persona.frontier:
        new_dna = await frontier.chat(persona.frontier, synthesis)
    else:
        new_dna = await local_model.generate(persona.model.name, synthesis)
    paths.write_dna(persona.id, new_dna)

    dna_items = [line.strip() for line in new_dna.splitlines() if line.strip() and not line.strip().startswith("#")]
    all_pairs = []
    for item in dna_items:
        item_prompt = prompts.grow(dna=item, max_pairs=5)
        if persona.frontier:
            response = await frontier.chat(persona.frontier, item_prompt)
        else:
            response = await local_model.generate_json(persona.model.name, item_prompt)
        parsed = strings.to_json(response)
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
