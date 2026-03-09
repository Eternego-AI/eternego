"""Legalize — authorize planned Thoughts.

Guard: any Thought with authorized = False.
Job:   filter steps to those requiring permission.
       All clear / none require permission → thought.authorized = True (no LLM needed).

       First pass (pending_tools empty):
         Call ego.legalize to check current permissions file.
         Rejected → generate denial, deliver via mind.reply() (always, ignores verbosity),
                    add assistant signal to perception, mark perception completed.
         Unknown  → request permission via mind.reply() (always delivers), add assistant
                    signal to perception, set thought.pending_tools.
         Granted  → thought.authorized = True.

       Subsequent passes (pending_tools set, waiting for user reply):
         Once the last signal in the perception is from the user, call
         ego.grant_or_reject to detect the decision and persist it.
         Granted  → clear pending_tools, thought.authorized = True.
         Rejected → deny + deliver, remove thought.
         No decision yet → wait (return False for this thought).

prompt() → returns None; all LLM calls happen inside run() via ego.legalize / ego.grant_or_reject.
run(None) → handles auto-authorization, orphan cleanup, and permission requests.
"""

from application.core.brain.data import Signal
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger


def prompt(memory: Memory, persona: Persona) -> None:
    """Legalize LLM calls are managed internally in run() via ego.legalize / ego.grant_or_reject."""
    return None


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    unauthorized = [t for t in memory.thoughts() if not t.authorized]
    if not unauthorized:
        return False

    from application.core.brain import ego, tools as brain_tools
    from application.core import registry
    changed = False

    for thought in unauthorized:
        perception = memory.nodes.get(thought.perception_id)
        if perception is None:
            memory.remove_node(thought.id)
            changed = True
            continue

        # Only steps that actually require permission
        steps_needing = [
            s for s in thought.steps
            if (t := brain_tools.for_name(s.tool)) is not None and t.requires_permission
        ]
        if not steps_needing:
            thought.authorized = True
            logger.info("legalize: authorized (no permission needed)", {
                "persona_id": persona.id,
                "thought_id": thought.id,
            })
            changed = True
            continue

        if thought.pending_tools:
            # Permission request was already sent — check if user replied
            last = perception.signals[-1] if perception.signals else None
            if last and last.role == "user":
                decision = await ego.grant_or_reject(persona, thought.pending_tools, perception.signals)
                granted = decision.get("granted", [])
                rejected = decision.get("rejected", [])

                if rejected:
                    deny_text = await ego.deny(persona, perception, rejected)
                    memory.remove_node(thought.id)
                    await _deliver_and_record(deny_text, perception, memory, registry, persona)
                    perception.completed = True
                    changed = True
                elif granted:
                    still_unknown = [t for t in thought.pending_tools if t not in granted]
                    if not still_unknown:
                        thought.pending_tools = []
                        thought.authorized = True
                        logger.info("legalize: permission granted", {
                            "persona_id": persona.id,
                            "thought_id": thought.id,
                        })
                    else:
                        # Partially granted — ask for remaining tools
                        thought.pending_tools = still_unknown
                        tool_list = ", ".join(still_unknown)
                        text = f"I still need permission for: {tool_list}. May I proceed?"
                        await _deliver_and_record(text, perception, memory, registry, persona)
                    changed = True
            # else: user hasn't replied yet — leave thought pending, no change

        else:
            # First pass — check permissions file
            result = await ego.legalize(persona, steps_needing)
            granted = result.get("granted", [])
            rejected = result.get("rejected", [])
            unknown = result.get("unknown", [])

            if rejected:
                deny_text = await ego.deny(persona, perception, rejected)
                memory.remove_node(thought.id)
                await _deliver_and_record(deny_text, perception, memory, registry, persona)
                perception.completed = True
                changed = True

            elif unknown:
                tool_list = ", ".join(unknown)
                text = f"I need permission to use: {tool_list}. May I proceed?"
                await _deliver_and_record(text, perception, memory, registry, persona)
                thought.pending_tools = unknown
                logger.info("legalize: permission requested", {
                    "persona_id": persona.id,
                    "thought_id": thought.id,
                    "tools": unknown,
                })
                changed = True

            else:
                thought.authorized = True
                logger.info("legalize: authorized", {
                    "persona_id": persona.id,
                    "thought_id": thought.id,
                })
                changed = True

    return changed


async def _deliver_and_record(text: str, perception, memory, registry, persona) -> None:
    """Add assistant signal to perception for history and deliver to person (always — permission messages bypass verbosity)."""
    sig = Signal(role="assistant", data={"content": text})
    memory.add_node(sig)
    perception.signals.append(sig)
    memory.add_edge(sig.id, perception.id, "perceived_as")

    mind = registry.mind(persona.id)
    if mind:
        await mind.reply(text)
