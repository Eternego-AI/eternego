"""Persona — periodic self-check: read recent faults from living.signals,
disable unhealthy services, shut down if thinking is compromised, recover
the worker if it crashed, process due destiny entries."""

import time
from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, paths
from application.core.brain.signals import BrainFault
from application.core.data import Message, Persona, Prompt
from application.platform import datetimes, filesystem, logger, objects
from application.platform.observer import Command, dispatch


# Faults are scanned in a window matching the heartbeat interval. Anything
# older has been handled by a prior health_check call. Coupled to the
# heartbeat cadence in `manager._heartbeat_loop` (60s sleep).
_FAULT_WINDOW_NS = 60 * 1_000_000_000


@dataclass
class HealthCheckData:
    persona: Persona
    log_entry: dict


async def health_check(ego, living, dt) -> Outcome[HealthCheckData]:
    """Every minute, check how the persona's body has been feeling.

    Reads recent BrainFault signals from living.signals (the felt stream)
    in a one-minute window. Per field:
    - thinking faulted → sick + shutdown (returns early, no recovery)
    - frontier faulted → null persona.frontier, tell person, persist
    - vision faulted → same, for persona.vision

    Recovery: if worker went idle-with-error AND we're not going sick,
    apologize, reset, nudge.

    Then process due destiny entries (inject 'due for:' message + nudge).

    All paths broadcast either "Health checked" (routine) or "Persona became
    sick" (terminal) so the Plan dispatched at the top always has a matching
    Event for subscribers.
    """
    persona = ego.persona
    bus.propose("Health check", {"persona": persona})

    cutoff_ns = time.time_ns() - _FAULT_WINDOW_NS
    window = [s for s in living.signals if s.time >= cutoff_ns]
    faults = [s for s in window if isinstance(s, BrainFault)]
    signals_record = []
    for s in window:
        d = s.details if isinstance(s.details, dict) else {}
        d = {k: v for k, v in d.items() if k != "persona"}
        signals_record.append({
            "type": type(s).__name__,
            "title": s.title,
            "time": s.time,
            "details": objects.safe(d),
        })
    log_entry = {
        "time": datetimes.iso_8601(datetimes.now()),
        "fault_count": len(faults),
        "fault_providers": sorted({s.details.get("provider") for s in faults if s.details.get("provider")}),
        "signals": signals_record,
    }
    paths.append_jsonl(paths.health_log(persona.id), log_entry)

    # Thinking fault → going sick. Skip recovery (we're going down anyway).
    thinking_provider = persona.thinking.provider or "ollama"
    thinking_faults = [s for s in faults if s.details.get("provider") == thinking_provider]
    if thinking_faults:
        persona.status = "sick"
        paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)
        sample = next((s.details.get("error") for s in thinking_faults if s.details.get("error")), "")
        message = f"{persona.name} ran into trouble thinking ({thinking_provider})"
        if sample:
            message += f": {sample}"
        message += ". Stepping out for now."
        dispatch(Command("Persona wants to say", {"persona": persona, "text": message}))
        bus.order("Persona became sick", {"persona": persona, "log_entry": log_entry})
        return Outcome(
            success=True,
            message=f"{persona.name} became sick — {thinking_provider} unreachable for thinking.",
            data=HealthCheckData(persona=persona, log_entry=log_entry),
        )

    try:
        # Recovery: worker hit unexpected error and went idle. Apologize,
        # reset, nudge. Only fires when we're not going sick (handled above).
        if living.pulse.worker.idle and living.pulse.worker.error:
            error = living.pulse.worker.error
            logger.info("Recovering ego from unexpected error", {"persona": persona, "error": str(error)})
            text = "Sorry, it seems I got distracted. Let me see what I should be doing."
            dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))
            living.pulse.worker.reset()
            living.pulse.worker.nudge()

        if persona.frontier:
            frontier_provider = persona.frontier.provider or "ollama"
            frontier_faults = [s for s in faults if s.details.get("provider") == frontier_provider]
            if frontier_faults:
                sample = next((s.details.get("error") for s in frontier_faults if s.details.get("error")), "")
                message = f"{persona.name} couldn't reach {frontier_provider}"
                if sample:
                    message += f": {sample}"
                message += ". Escalation disabled until you restart."
                dispatch(Command("Persona wants to say", {"persona": persona, "text": message}))
                persona.frontier = None
                paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        if persona.vision:
            vision_provider = persona.vision.provider or "ollama"
            vision_faults = [s for s in faults if s.details.get("provider") == vision_provider]
            if vision_faults:
                sample = next((s.details.get("error") for s in vision_faults if s.details.get("error")), "")
                message = f"{persona.name} couldn't reach {vision_provider}"
                if sample:
                    message += f": {sample}"
                message += ". Vision disabled until you restart."
                dispatch(Command("Persona wants to say", {"persona": persona, "text": message}))
                persona.vision = None
                paths.save_as_json(persona.id, paths.persona_identity(persona.id), persona)

        due = paths.due_destiny_entries(persona.id, dt)
        if due:
            notifications = []
            for filepath, content in due:
                paths.add_history_entry(persona.id, filepath.stem, content)
                filesystem.delete(filepath)
                notifications.append(content)
            due_text = "due for:\n" + "\n---\n".join(notifications)
            ego.memory.remember(Message(content=due_text, prompt=Prompt(role="user", content=due_text)))
            living.pulse.worker.nudge()

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
