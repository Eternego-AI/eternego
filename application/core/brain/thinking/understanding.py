"""Understanding — routes incoming Signals to existing or new Perception threads.

Active threads are numbered (1, 2, 3...) for the duration of the LLM call.
The model returns row numbers to route to existing threads, or new impression
strings for new topics. Row numbers are resolved back to Perceptions by index —
no IDs stored, no string matching required.
"""

from application.core.data import Prompt
from application.core.brain import perceptions, signals
from application.platform import logger


async def by(reason, mind) -> None:
    if not mind.unrealized:
        return

    persona = mind.persona
    logger.info("understanding.by", {"unrealized": len(mind.unrealized)})

    active = mind.awareness
    row_map = {i + 1: p for i, p in enumerate(active)}  # 1-based row → Perception

    threads_text = "\n\n".join(
        f"{i}.\n{perceptions.thread(p)}" for i, p in row_map.items()
    ) if active else "None"

    signals_text = "\n".join(
        f"- {signals.contain_id(s)}" for s in mind.unrealized
    )

    system = (
        "# Task: Route incoming signals to conversation threads\n"
        "Each active thread is numbered. For each signal, return the row number(s) "
        "of threads it continues, or a new short impression (max 8 words) if it starts "
        "a new topic. A signal can belong to multiple threads if it spans subjects.\n\n"
        "Return routes ordered by importance — most urgent or significant thread first.\n\n"
        "Return JSON:\n"
        "{\n"
        '  "routes": [\n'
        '    {"signal_id": "...", "rows": [1, 3], "new_impressions": ["new topic"]}\n'
        "  ]\n"
        "}\n"
        "Use empty lists when not applicable. Prefer rows over new_impressions."
    )

    prompts = [Prompt(role="user", content=(
        f"Active threads:\n{threads_text}\n\n"
        f"Signals to route:\n{signals_text}\n\n"
        "Route each signal using row numbers or new impressions."
    ))]

    result = await reason(persona, system, prompts)
    routes = result.get("routes", [])

    signal_map = {s.id: s for s in mind.unrealized}

    for route in routes:
        signal = signal_map.get(route.get("signal_id"))
        if not signal:
            continue

        for row in route.get("rows", []):
            perception = row_map.get(row)
            if perception:
                mind.understand(signal, perception.impression)

        for impression in route.get("new_impressions", []):
            if impression:
                mind.understand(signal, impression)

        if not route.get("rows") and not route.get("new_impressions"):
            mind.understand(signal, signal.content[:60])
