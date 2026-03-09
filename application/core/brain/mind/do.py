"""Do — execute authorized Thoughts.

Guard: any Thought with authorized = True.
Job:   execute steps in order.
       Before each step, inject $tool_output params with the previous step's output.
       Step success → add result Signal to perception's signals, add output_of edge.
       Step failure → add result Signal (success=False), remove Thought,
                      clear impression/meaning for re-planning.
       All steps succeed → remove Thought; think will plan the next section on next tick.

prompt() → always returns None (no LLM needed; pure tool execution).
run(None) → executes authorized thoughts directly.
"""

from application.core.brain.data import Signal, Step
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger, datetimes


def prompt(memory: Memory, persona: Persona) -> None:
    return None


async def run(data: dict | None, memory: Memory, persona: Persona) -> bool:
    authorized = [t for t in memory.thoughts() if t.authorized]
    if not authorized:
        return False

    changed = False

    for thought in authorized:
        perception = memory.nodes.get(thought.perception_id)
        if perception is None:
            memory.remove_node(thought.id)
            changed = True
            continue

        success = True
        last_output = ""
        for step in thought.steps:
            resolved_step = _resolve_step(step, last_output)
            try:
                output = await _run_step(resolved_step, persona)
                last_output = output
                out_signal = Signal(
                    role="result",
                    data={"tool": step.tool, "output": output, "success": True},
                )
                memory.add_node(out_signal)
                perception.signals.append(out_signal)
                memory.add_edge(out_signal.id, perception.id, "perceived_as")
                memory.add_edge(out_signal.id, thought.id, "output_of")
                logger.info("do: step succeeded", {
                    "persona_id": persona.id,
                    "tool": step.tool,
                    "thought_id": thought.id,
                })
            except Exception as e:
                logger.warning("do: step failed", {
                    "persona_id": persona.id,
                    "tool": step.tool,
                    "error": str(e),
                })
                fail_signal = Signal(
                    role="result",
                    data={"tool": step.tool, "output": str(e), "success": False},
                )
                memory.add_node(fail_signal)
                perception.signals.append(fail_signal)
                memory.add_edge(fail_signal.id, perception.id, "perceived_as")
                # Remove thought and clear perception for re-planning
                memory.remove_node(thought.id)
                perception.impression = None
                perception.meaning = None
                success = False
                break

        if success:
            thought.completed_at = datetimes.now()
            memory.remove_node(thought.id)
            logger.info("do: thought executed", {
                "persona_id": persona.id,
                "perception_id": perception.id,
            })

        changed = True

    return changed


def _resolve_step(step: Step, last_output: str) -> Step:
    """Replace $tool_output param values with the previous step's output."""
    if not any(v == "$tool_output" for v in step.params.values()):
        return step
    resolved_params = {
        k: (last_output if v == "$tool_output" else v)
        for k, v in step.params.items()
    }
    return Step(number=step.number, tool=step.tool, params=resolved_params)


async def _run_step(step: Step, persona) -> str:
    from application.core.brain import tools as brain_tools
    tool = brain_tools.for_name(step.tool)
    if tool is None:
        raise ValueError(f"unknown tool: {step.tool}")
    return await tool.execution(**step.params)(persona)
