"""Traits — the persona's enabling and limiting behaviours.

Traits are the atomic units of character expression. Each trait receives a
thought from the sub-conscious stream and produces a new stimulus back into
presence, closing the cognitive cycle.

Traits can be:
  - enabling  — things the persona can do (e.g. say, reason, recall)
  - limiting  — things the persona must or must not do (e.g. stay in scope)
"""

from application.core.brain.cognitive.traits.say import say

__all__ = ["say"]
