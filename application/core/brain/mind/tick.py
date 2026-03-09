"""Tick — the cognitive loop.

Each module exposes:
  prompt(memory, persona) -> tuple[str, str] | None
      Synchronous. Returns (prompt_text, system_text) or None if no LLM needed / guard not met.
  run(data, memory, persona) -> bool
      Async. data = parsed JSON from ego.reason(), or None if no prompt was needed.
      Returns True if memory changed.

Tick calls prompt() on each module in order. If a prompt is returned, tick calls
ego.reason() to get the LLM result, then calls run(data). If no prompt, tick calls
run(None) directly.

Resets to the first module on any memory change. Goes idle when no module reports a change.

Mid-request cancellation: start() cancels any running task and creates a fresh one.
When memory changes while an LLM call is in-flight, the asyncio.CancelledError propagates
up through ego.reason(), the task ends, and a new task starts with fresh state.

Loop order (reflects priority):
  conclusion → authorize → realize → understand → recognize → confirm → experience →
  think → legalize → do → person_identifier → trait_identifier → wish_identifier → struggle_identifier
"""

import asyncio

from application.platform import logger


class Tick:

    def __init__(self, persona_id: str, memory, persona):
        self._persona_id = persona_id
        self._memory = memory
        self._persona = persona
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Cancel any running loop and start a fresh one (enables mid-request cancellation)."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._loop())

    def cancel(self) -> None:
        """Cancel the running loop task."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        from application.core.brain.mind import (
            conclusion, authorize, realize, understand, recognize, confirm,
            experience, think, legalize, do,
            person_identifier, trait_identifier, wish_identifier, struggle_identifier,
        )
        from application.core.brain import ego

        modules = [
            conclusion, authorize, realize, understand, recognize, confirm,
            experience, think, legalize, do,
            person_identifier, trait_identifier, wish_identifier, struggle_identifier,
        ]

        logger.info("tick.start", {"persona_id": self._persona_id})

        while True:
            changed = False
            for module in modules:
                try:
                    result = module.prompt(self._memory, self._persona)
                    if result is not None:
                        prompt_str, system_str = result
                        data = await ego.reason(self._persona, prompt_str, system=system_str)
                    else:
                        data = None
                    changed = await module.run(data, self._memory, self._persona)
                except asyncio.CancelledError:
                    raise  # propagate — a new tick will start with fresh state
                except Exception as e:
                    logger.warning(f"tick: {module.__name__} error", {
                        "persona_id": self._persona_id, "error": str(e)
                    })
                if changed:
                    self._memory.persist()
                    break
            if not changed:
                logger.info("tick.idle", {"persona_id": self._persona_id})
                return
