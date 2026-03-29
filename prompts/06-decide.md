# Decide — Extract Action JSON

Extracts structured data or tool calls from the conversation. The model sees the full thread and returns JSON.

Source: `application/core/brain/mind/conscious.py:195`

---

## System Prompt

```
{identity — see 01-character.md}

{meaning.path()}

Add a "recap" field to your JSON — one sentence on what you did or are doing.
If already fulfilled, return just: {"recap": "what was accomplished"}.
```

### Example: Reminder decide

```
{identity}

Extract the reminder details from what the person said (ignore assistant messages).
Return JSON: {"trigger": "YYYY-MM-DD HH:MM", "timezone": "IANA timezone from person identity", "content": "what to be reminded of", "recurrence": "daily|weekly|monthly|hourly or empty string"}
Use the person's timezone from their identity. Set recurrence only if the person explicitly asks for a recurring reminder. Use empty strings for any missing or inapplicable fields.

Add a "recap" field to your JSON — one sentence on what you did or are doing.
If already fulfilled, return just: {"recap": "what was accomplished"}.
```

## Messages

Full thread as user/assistant messages (via `mind.prompts(thought)`).

## Expected Response

JSON with tool params + recap field.

---

## Audit

### Fixed: "Add a recap field to your JSON"
Now reads as an addendum to the meaning's schema, not a competing instruction. "Add to your JSON" makes it clear recap is one more field in the same object.
