"""Prompts — all prompts used across the application."""


EXTRACTION = """Analyze the following conversations and extract observations about the person.

Return a JSON object with three arrays:
- "facts": objective facts about the person (name, age, job, location, family, etc.)
- "traits": behavioral preferences and patterns (communication style, technical preferences, habits, etc.)
- "context": information from the persona's perspective about who this person is and how they work

Conversations:
{conversations}

Return ONLY valid JSON, no other text."""


RECOVERY_PHRASE = "Generate a 24-word recovery phrase using random common English words. Return only the 24 words separated by spaces, nothing else."
