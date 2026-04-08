"""Subconscious — sleep-time knowledge extraction.

Each function receives (persona, conversation_text), where conversation_text
is a narrative rendering of the conversation. The system prompt tells the
model what to extract; the conversation is passed as a single user message
so the model treats it as data to analyse, not a chat to continue.
"""

import importlib
import pkgutil

for _, _name, _ in pkgutil.iter_modules(__path__):
    _module = importlib.import_module(f".{_name}", __name__)
    globals()[_name] = getattr(_module, _name)
