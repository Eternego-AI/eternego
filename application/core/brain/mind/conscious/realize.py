"""Conscious — route unattended signals to perception threads."""

from application.core.brain import perceptions, signals
from application.core import bus, models
from application.platform import logger


async def realize(memory, persona, identity_fn, express_thinking_fn) -> None:
    """Route unattended signals to existing or new perception threads."""
    if not memory.needs_realizing:
        return

    logger.debug("Realize", {"persona": persona})
    await bus.share("Pipeline: realize", {"persona": persona, "stage": "realize", "unattended": len(memory.needs_realizing)})

    await express_thinking_fn()

    known = memory.perceptions
    thread_map = {i + 1: p for i, p in enumerate(known)}
    unattended = list(memory.needs_realizing)
    signal_map = {i + 1: s for i, s in enumerate(unattended)}

    threads_text = "\n\n".join(
        f"{i}. {p.impression}\n{perceptions.conversation(p)}"
        for i, p in thread_map.items()
    ) if known else "None"

    signals_text = "\n".join(
        f"{i}. {signals.labeled(s)}"
        for i, s in signal_map.items()
    )

    system = (
        identity_fn()
        + "\n\n# Task: Route incoming signals to conversation threads\n"
        "Threads and signals are both numbered. For each signal number, decide:\n"
        "- Does it **directly continue** an existing thread? Only if it is a reply or follow-up "
        "to that specific conversation topic. A new unrelated message does NOT continue a thread "
        "just because the same person sent it.\n"
        "- Otherwise, create a new impression that captures the topic.\n\n"
        "Return routes ordered by importance — most urgent or significant first.\n\n"
        "Return JSON:\n"
        "{\n"
        '  "routes": [\n'
        '    {"signal": 1, "threads": [1], "new_impressions": ["new topic"]}\n'
        "  ]\n"
        "}\n"
        "Use empty lists when not applicable. When in doubt, prefer a new impression "
        "over forcing a signal into an unrelated thread.\n\n"
        f"Known threads:\n{threads_text}\n\n"
        f"Signals to route:\n{signals_text}"
    )

    messages = [{"role": "system", "content": system}, {"role": "user", "content": "Route each signal by its number."}]
    result = await models.chat_json_stream(persona.thinking, messages)
    routes = result.get("routes", [])

    routed = set()
    for route in routes:
        signal_num = route.get("signal")
        if not isinstance(signal_num, (int, float)):
            continue
        signal = signal_map.get(int(signal_num))
        if not signal:
            continue

        routed.add(signal.id)

        for thread_num in route.get("threads", []):
            perception = thread_map.get(thread_num)
            if perception:
                memory.realize(signal, perception.impression)

        for impression in route.get("new_impressions", []):
            if impression:
                memory.realize(signal, impression)

        if not route.get("threads") and not route.get("new_impressions"):
            logger.warning("realize: route with no threads or impressions", {"signal_id": signal.id})

    for signal in unattended:
        if signal.id not in routed:
            logger.warning("realize: unrouted signal, stays unattended", {"signal_id": signal.id})
