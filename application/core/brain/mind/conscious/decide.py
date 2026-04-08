"""Conscious — execute the action for a pending thought."""

import json
import uuid

from application.core.brain.data import Signal, SignalEvent
from application.core import bus, models
from application.platform import logger


async def decide(memory, persona, identity_fn, express_thinking_fn) -> None:
    """Execute the action for the most important pending thought."""
    thought = memory.most_important_thought(memory.needs_decision)
    if not thought:
        return

    await express_thinking_fn()

    logger.debug("Decide", {"persona": persona, "impression": thought.perception.impression})
    await bus.share("Pipeline: decide", {"persona": persona, "stage": "decide", "impression": thought.perception.impression, "meaning": thought.meaning.name})

    system = (
        identity_fn()
        + "\n\n" + thought.meaning.path()
        + "\n\nAdd a \"recap\" field to your JSON — one sentence on what you did or are doing.\n"
        "If already fulfilled, return just: {\"recap\": \"what was accomplished\"}."
    )
    messages = [{"role": "system", "content": system}] + memory.prompts(thought)
    result = await models.chat_json_stream(persona.thinking, messages)
    recap = result.pop("recap", None) if isinstance(result, dict) else None

    if not result:
        memory.answer(thought, recap or "", SignalEvent.recap)
        return

    decision_text = json.dumps(result)
    memory.answer(thought, decision_text, SignalEvent.decided)

    try:
        action = await thought.meaning.run(result)
    except Exception as e:
        logger.error("Decide: run failed", {"persona": persona, "error": str(e)})
        memory.inform(thought, Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content=f"[{thought.meaning.name}: {decision_text}] Error: {e}",
        ))
        return

    if action is None:
        memory.answer(thought, recap or "", SignalEvent.recap)
        return

    try:
        output = await action()
    except Exception as e:
        logger.error("Decide: action failed", {"persona": persona, "error": str(e)})
        output = f"Error: {e}"

    if output is not None:
        content = f"[{thought.meaning.name}: {decision_text}]"
        if output:
            content += f" {output}"
        memory.inform(thought, Signal(
            id=str(uuid.uuid4()), event=SignalEvent.executed,
            content=content,
        ))
    else:
        memory.answer(thought, recap or "", SignalEvent.recap)
