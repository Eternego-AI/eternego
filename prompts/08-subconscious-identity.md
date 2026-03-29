# Subconscious — Extract Identity Facts

Runs during sleep. Extracts stable facts about the person from conversation.

Source: `application/core/brain/mind/subconscious.py:27`

---

## System Prompt

```
# Extract Identity Facts

Read the conversation below. Extract concrete facts about the person.

What counts:
- Name, age, birthday, gender
- Where they live, their timezone
- Job, employer, profession
- Family: spouse, children, parents
- Important contacts: doctors, close friends (include name, phone, address when given)
- Strong long-term preferences they stated clearly

What does NOT count: moods, plans, opinions, how they talk, things the assistant said.

Only extract from what the person said (user messages).

## Current Facts

{existing facts or '(none yet)'}

Merge new facts into the list above. Keep everything that is still true. If the conversation adds nothing new, return the current facts unchanged.

Format: one fact per line, each starting with 'The person '. No bullets, no headers, no commentary.
```

## Messages

The conversation as user/assistant message pairs.

## Expected Response

Plain text, one fact per line starting with "The person ".

---

## Audit

### Fixed: no more overwrite risk
Code now checks for "(none yet)" and unchanged content — skips saving when nothing new.

### Fixed: "even a single clear signal counts"
Removed the "recurring" requirement. A concrete fact mentioned once is worth keeping.

### "What counts / What does NOT count" structure
Concrete bullet lists instead of prose. A small model can scan these quickly.
