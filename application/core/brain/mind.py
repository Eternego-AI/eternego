"""Mind — the persona's cognitive state and orchestrator.

One Mind instance per persona. Mind is the single entry point for all
external inputs and runs the full cognitive cycle internally.

Mind is ephemeral — no state is persisted to disk. Completed thoughts
are archived to history; everything else is discarded on restart.

Stages:
  rest         — idle, ready for the next tick
  realizing    — grouping signals into threads and naming them
  ordering     — prioritising perceptions
  planning     — planning steps for the top perception
  executing    — running the step loop
  interrupting — a new signal arrived mid-cycle; executor will summarise then stop

mind.hear(message)          — receive a message from the outside world
mind.interrupt(text)        — inject an internal signal and interrupt the current cycle
mind.execute(trait, params) — run any trait directly
mind.next_task(taking)      — peek or consume the next plan step
mind.load(persona)          — the only way to create a Mind
grow(persona)               — evolve DNA, generate training, fine-tune
"""

from application.core.data import Persona, Message, Prompt
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
        # Presence — ephemeral, rebuilt from scratch on restart
        self._signals: list[Signal] = []
        # Derived layers — rebuilt each tick
        self._awareness: list[Perception] = []
        self._order: list[Perception] = []
        self._plan: list[Step] = []
        self._current_step: int = 0
        # Orchestration state
        self._stage: str = "rest"   # rest | realizing | ordering | preparing | planning | executing | interrupting

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

    def hear(self, message: Message) -> None:
        """Receive a message, add as a signal, and trigger the cognitive cycle."""
        self._signals.append(Signal(
            prompt=Prompt(role="user", content=message.content),
            channel=message.channel,
        ))
        logger.info("mind.hear: signal received", {"persona_id": self._persona_id})

        if self._stage != "rest":
            self._stage = "interrupting"
        else:
            processes.run_async(self._tick)

    async def execute(self, trait_name: str, params: dict) -> str:
        """Run a single trait and return its output. Public — can run any trait."""
        from application.core.brain import traits
        persona = self.persona
        trait = traits.for_name(trait_name)
        if trait is None:
            output = f"error: unknown trait '{trait_name}'"
        else:
            try:
                fn = trait.execution(**params)
                output = await fn(persona)
            except Exception as e:
                output = f"error: {str(e)}"

        if trait_name == "summarize":
            async def _commit():
                if output:
                    self._signals.append(Signal(prompt=Prompt(role="user", content=output)))
                processes.run_async(self._tick)
            processes.run_async(_commit)

        return output

    def interrupt(self, text: str) -> None:
        """Inject an internal signal and interrupt the current cycle."""
        self._signals.append(Signal(prompt=Prompt(role="user", content=text)))
        logger.info("mind.interrupt: internal signal", {"persona_id": self._persona_id})
        if self._stage != "rest":
            self._stage = "interrupting"
        else:
            processes.run_async(self._tick)

    def next_task(self, taking: bool = False) -> Step | None:
        """Return the next plan step, or None if the plan is exhausted.

        taking=False  — peek: returns the step without advancing the plan.
        taking=True   — consume: advances the plan pointer (used by the executor).
        """
        if self._current_step >= len(self._plan):
            return None
        step = self._plan[self._current_step]
        if taking:
            self._current_step += 1
        return step

    # ── Internal ─────────────────────────────────────────────────────────

    async def _tick(self) -> None:
        """Full cognitive cycle: realize → order → plan → execute → archive."""
        from application.core.brain import ego

        if self._stage != "rest":
            return

        # Cache persona at tick start — survives any registry changes during execution
        persona = self.persona
        if persona is None:
            return

        try:
            signals = list(self._signals)
            if not signals:
                return

            self._stage = "realizing"
            self._awareness = await ego.realize(persona, signals)
            if not self._awareness:
                return

            if self._stage != "interrupting":
                self._stage = "ordering"
                self._order = await ego.order(persona, self._awareness)
                if not self._order:
                    return

            # Resolve pending permission if signals have arrived after the request
            if self._stage != "interrupting":
                top = self._order[0]
                pending_idx = next(
                    (i for i, s in enumerate(top.thread.signals) if s.pending_permission),
                    None,
                )
                if pending_idx is not None:
                    subsequent = top.thread.signals[pending_idx + 1:]
                    if subsequent:
                        pending_signal = top.thread.signals[pending_idx]
                        decisions = await ego.grant_or_reject(
                            persona, pending_signal.pending_permission, subsequent,
                        )
                        await self._authorize(persona, pending_signal, decisions)

            meaning = None
            if self._stage != "interrupting":
                self._stage = "preparing"
                meaning = await ego.prepare(persona, self._order[0])
                if not meaning.traits:
                    meaning.traits = ["say"]

            if self._stage != "interrupting" and meaning is not None:
                self._stage = "planning"
                steps = await ego.plan(persona, self._order[0], meaning)
                if not steps:
                    return
                meaning.path = steps
                self._plan = steps
                self._current_step = 0
                paths.append_meaning_path(
                    persona.id, meaning.title,
                    meaning.traits,
                    [s.trait for s in meaning.path],
                )

            # Legalize: check which steps require permission
            if self._stage != "interrupting":
                blocked = await ego.legalize(persona, self._plan)
                if blocked:
                    top = self._order[0]
                    if top.thread.signals:
                        top.thread.signals[-1].pending_permission = blocked
                    self._signals.append(Signal(
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

            interrupted = self._stage == "interrupting"
            self._stage = "executing"
            results = ""

            while True:
                step = self.next_task(taking=True)
                if step is None:
                    break
                output = await self.execute(step.trait, step.params)
                results += f"[{step.trait}] {output}\n"
                if self._stage == "interrupting":
                    interrupted = True
                    break

            if interrupted:
                results += "Interrupted: a new message arrived before execution completed."

            if results:
                await self.execute("summarize", {"text": f"Summarize these execution results into a concise record:\n\n{results}"})

            if not interrupted and self._order:
                await self._archive(persona, self._order[0])

        except Exception as e:
            logger.warning("mind._tick: unhandled error", {"persona_id": self._persona_id, "error": str(e)})
        finally:
            self._stage = "rest"

    async def _authorize(self, persona: Persona, pending_signal: Signal, decisions: dict) -> None:
        """Write grant/reject decisions to permissions.md, clear the pending flag, and signal the outcome."""
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
            self.interrupt("; ".join(parts))

    async def _archive(self, persona: Persona, perception: Perception) -> None:
        """Write the completed thought to history and update the briefing index."""
        from application.platform import datetimes
        lines = []
        for signal in perception.thread.signals:
            channel = f" via {signal.channel.name}" if signal.channel else ""
            time = signal.created_at.strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"[{signal.prompt.role}{channel} at {time}]: {signal.prompt.content}")
        timestamp = datetimes.date_stamp(datetimes.now())
        filename = f"{perception.title}-{timestamp}.md"
        paths.add_history_entry(persona.id, perception.title, "\n\n".join(lines))
        paths.add_history_briefing(
            persona.id,
            "| Date | Title | File |",
            f"| {timestamp} | {perception.title} | {filename} |",
        )


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
