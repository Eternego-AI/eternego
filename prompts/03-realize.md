# Realize — Route Signals to Threads

Maps incoming signals to existing conversation threads or creates new ones.

Source: `application/core/brain/mind/conscious.py:17`

---

## System Prompt

```
{identity — see 01-character.md}

# Task: Route incoming signals to conversation threads
Threads and signals are both numbered. For each signal number, decide:
- Does it **directly continue** an existing thread? Only if it is a reply or follow-up to that specific conversation topic. A new unrelated message does NOT continue a thread just because the same person sent it.
- Otherwise, create a new impression that captures the topic.

Return routes ordered by importance — most urgent or significant first.

Return JSON:
{
  "routes": [
    {"signal": 1, "threads": [1], "new_impressions": ["new topic"]}
  ]
}
Use empty lists when not applicable. When in doubt, prefer a new impression over forcing a signal into an unrelated thread.

Known threads:
1. Daily greetings
[2026-03-28 16:45 UTC] person: Hello!
[2026-03-28 16:46 UTC] persona: Hello!

Signals to route:
1. [person, telegram] Good morning
```

## User Message

```
Route each signal by its number.
```

## Expected Response

JSON: `{"routes": [{"signal": 1, "threads": [1], "new_impressions": []}]}`

---

## Audit

### Identity is overwhelming for this task
The full character (values, morals, cornerstone) is prepended, but this task is purely mechanical — route signal X to thread Y. The model doesn't need to know about integrity, compassion, or courage to route a message. For a 7B model, the identity preamble adds noise and pushes the actual task further into the context.

### JSON example shows all fields at once
The example `{"signal": 1, "threads": [1], "new_impressions": ["new topic"]}` uses both threads AND new_impressions simultaneously. A small model might think it should always fill both. Better to show two separate examples: one for continuing a thread, one for creating new.

### "Return routes ordered by importance" — unnecessary complexity
With typically 1-2 signals, ordering by importance adds cognitive load for no benefit. The model might overthink priority instead of just routing.

### Clear and well-structured overall
The distinction between "directly continue" and "new impression" is well explained. The warning about not forcing signals into unrelated threads is good.
