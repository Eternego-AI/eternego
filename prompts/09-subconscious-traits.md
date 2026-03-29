# Subconscious — Extract Behavioral Traits

Runs during sleep. Extracts communication patterns and style preferences.

Source: `application/core/brain/mind/subconscious.py:50`

---

## System Prompt

```
# Extract Behavioral Traits

Read the conversation below. Extract how the person communicates and what style they prefer.

What counts:
- Short or long messages? Formal or casual?
- Do they use humor? Emojis? Are they direct or roundabout?
- Do they want details or just the answer?
- Any clear preference they showed in how they want to be talked to

What does NOT count: identity facts (name, job, location), things the assistant said.

Only extract from what the person said (user messages). Even a single clear signal counts — if they obviously prefer brevity, note it.

## Current Traits

{existing traits or '(none yet)'}

Merge new traits into the list above. Keep everything that is still true. If the conversation adds nothing new, return the current traits unchanged.

Format: one trait per line, each starting with 'The person '. No bullets, no headers, no commentary.
```

## Audit

### Fixed: lowered threshold
"Even a single clear signal counts" — no more requiring "recurring patterns."

### Concrete questions instead of abstract criteria
"Short or long messages? Formal or casual?" gives the model specific things to look for.
