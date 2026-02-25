"""Skills — learned capabilities the persona can draw on during thinking.

Each skill is a module with:
  name: str       — identifier used to load the skill
  summary: str    — one-line description shown in the system prompt
  skill(persona)  — returns the full skill text injected into context
"""
