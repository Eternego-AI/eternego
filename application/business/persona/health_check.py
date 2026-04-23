"""Persona — periodic self-check: read body events, disable unhealthy services,
shut down if thinking is compromised, process due destiny entries."""

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.data import Message, Persona, Prompt
from application.platform import datetimes, filesystem, logger
from application.platform.observer import Command, dispatch


@dataclass
class HealthCheckData:
    persona: Persona
    log_entry: dict


async def health_check(ego, dt) -> Outcome[HealthCheckData]:
    """Every minute, check how the persona's body has been feeling.

    Log the observation first. Then, per field: thinking faulted → sick + shut
    down; the returned Outcome's message tells the story and data carries the
    persona and the log entry. Frontier faulted → null persona.frontier, tell
    the person (include the error), persist. Vision faulted → same, for
    persona.vision. Multiple fields can be hit in one tick when providers
    differ. After that, process due destiny entries.

    Nudge the worker only when something genuinely new is in memory — a recovery
    apology or a 'Due now' notification. Disabled capacities don't nudge;
    the tick is either running (and will see the updated config next
    iteration) or idle with nothing to do.
    """
    persona = ego.persona
    bus.propose("Health check", {"persona": persona})

    if ego.pulse.worker.idle and ego.pulse.worker.error:
        error = ego.pulse.worker.error
        logger.info("Recovering ego from unexpected error", {"persona": persona, "error": str(error)})
        text = "Sorry, it seems I got distracted. Let me see what I should be doing."
        ego.memory.remember(Message(content=text, prompt=Prompt(role="assistant", content=text)))
        dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))
        ego.pulse.worker.reset()
        ego.pulse.worker.nudge()

    faults = [e for e in ego.pulse.events if e.kind == "fault"]
    log_entry = {
        "time": datetimes.iso_8601(datetimes.now()),
        "loop_number": ego.pulse.loop_number,
        "fault_count": len(faults),
        "fault_providers": sorted({e.provider for e in faults if e.provider}),
    }
    paths.append_jsonl(paths.health_log(persona.id), log_entry)

    thinking_provider = persona.thinking.provider or "ollama"
    thinking_faults = [e for e in faults if e.provider == thinking_provider]
    if thinking_faults:
        persona.status = "sick"
        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)
        sample = next((e.error for e in thinking_faults if e.error), "")
        message = f"{persona.name} ran into trouble thinking ({thinking_provider})"
        if sample:
            message += f": {sample}"
        message += ". Stepping out for now."
        dispatch(Command("Persona wants to say", {"persona": persona, "text": message}))
        ego.pulse.clear_events()
        bus.order("Persona became sick", {"persona": persona, "log_entry": log_entry})
        return Outcome(
            success=True,
            message=f"{persona.name} became sick — {thinking_provider} unreachable for thinking.",
            data=HealthCheckData(persona=persona, log_entry=log_entry),
        )

    if persona.frontier:
        frontier_provider = persona.frontier.provider or "ollama"
        frontier_faults = [e for e in faults if e.provider == frontier_provider]
        if frontier_faults:
            sample = next((e.error for e in frontier_faults if e.error), "")
            message = f"{persona.name} couldn't reach {frontier_provider}"
            if sample:
                message += f": {sample}"
            message += ". Escalation disabled until you restart."
            dispatch(Command("Persona wants to say", {"persona": persona, "text": message}))
            persona.frontier = None
            paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

    if persona.vision:
        vision_provider = persona.vision.provider or "ollama"
        vision_faults = [e for e in faults if e.provider == vision_provider]
        if vision_faults:
            sample = next((e.error for e in vision_faults if e.error), "")
            message = f"{persona.name} couldn't reach {vision_provider}"
            if sample:
                message += f": {sample}"
            message += ". Vision disabled until you restart."
            dispatch(Command("Persona wants to say", {"persona": persona, "text": message}))
            persona.vision = None
            paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

    ego.pulse.clear_events()

    try:
        due = paths.due_destiny_entries(persona.id, dt)
        if due:
            notifications = []
            for filepath, content in due:
                paths.add_history_entry(persona.id, filepath.stem, content)
                filesystem.delete(filepath)
                notifications.append(content)
            due_text = "due for:\n" + "\n---\n".join(notifications)
            ego.memory.remember(Message(content=due_text, prompt=Prompt(role="user", content=due_text)))
            ego.pulse.worker.nudge()

        bus.broadcast("Health checked", {"persona": persona, "log_entry": log_entry})
        return Outcome(
            success=True,
            message="",
            data=HealthCheckData(persona=persona, log_entry=log_entry),
        )
    except Exception as e:
        bus.broadcast("Health check failed", {"persona": persona, "error": str(e)})
        return Outcome(
            success=False,
            message=str(e),
            data=HealthCheckData(persona=persona, log_entry=log_entry),
        )
