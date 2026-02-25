"""Cognitive — the persona's active cognitive system.

Two concerns:

  identity  — what the persona is, exposed through character and ego
  runtime   — how the persona thinks, driven by memory and clock

Usage:
    from application.core.brain import cognitive

    cognitive.character.shape(persona)             # full character prompt
    cognitive.ego.effect(persona, mem)             # full ego system prompt
    cognitive.ego.reason(persona, mem, prompt)     # atomic LLM call in JSON mode
    mem = await cognitive.memory.load(persona)     # load (or init) memory
    cognitive.clock.start(persona, mem)            # start all cognitive loops
"""

from application.core.brain.cognitive import character, ego, memory, clock
