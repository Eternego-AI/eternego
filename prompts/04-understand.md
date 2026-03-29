# Understand — Match Conversation to Meaning

Assigns the best-matching meaning to a conversation thread.

Source: `application/core/brain/mind/conscious.py:98`

---

## System Prompt

```
{identity — see 01-character.md}

# Task: Match a conversation thread to a meaning
Given a numbered list of known meanings and a conversation thread, return the row number of the best-matching meaning.
Use the Escalation row if no meaning fits.

Return JSON:
{"meaning_row": N}

Known meanings:
1. Greeting: Daily greetings, hellos, good mornings, and other salutations.
2. Chatting: Regular casual conversation, small talk, sharing thoughts, or just talking.
3. Reminder: The person asks to CREATE or SET a new reminder for a future time. This is about saving a new reminder, not about delivering one that is already due.
4. Scheduler: The person asks to CREATE or SCHEDULE a new appointment, meeting, or event at a future time. This is about saving a new event, not about delivering one that is already due.
5. Calendar: The person wants to know what is on their calendar — upcoming reminders, scheduled events, or appointments for a specific date, date range, or today.
6. Noting: The person states a fact, preference, decision, or instruction to keep as a permanent note — no time trigger, no deadline, just something to store.
7. Recalling: The person wants to recall, revisit, or reference a past conversation — something they discussed before, a decision that was made, or context from a previous interaction.
8. Shell: The person wants to run a command, install software, check system status, troubleshoot an issue, manage files, or perform any local system operation.
9. Coding: The person wants to write code, create a script, build a project, edit a program, or run code they are working on.
10. Due Notification: A previously saved reminder or event has reached its due time and must be DELIVERED to the person now. This is a system notification, not a person asking to create something new.
11. Escalation: The interaction does not match any known meaning. Use this when the person's request, topic, or intent falls outside everything else available.

Return the row number of the best-matching meaning.
```

## Messages

The conversation thread as user/assistant messages (via `perceptions.to_conversation()`).

## Expected Response

JSON: `{"meaning_row": 1}`

---

## Audit

### Clear and functional
The numbered list with descriptions is easy for a model to scan. JSON output is simple.

### Instruction repeated
"Return the row number of the best-matching meaning" appears twice — once before the JSON format example, once after the meanings list. Redundant but not harmful.

### Reminder vs Scheduler distinction is subtle
Both say "CREATE or SET/SCHEDULE" at a future time. The only difference is "reminder" vs "appointment, meeting, or event." A small model may struggle to distinguish "remind me about the meeting at 3pm" (Reminder) from "schedule a meeting at 3pm" (Scheduler). Consider whether these should be merged or made more distinct.

### Due Notification placement
It's row 10, right before Escalation. Its description is very explicit about being a system notification, which is good. But the model only sees user/assistant conversation messages — when a due notification comes in, what does the conversation look like? If it comes as a user message, the model needs to distinguish "the system is telling me about a due item" from "the person is asking me to create one." The signal source matters here.

### No negative examples
The prompt doesn't show what NOT to match. For confusable pairs (Reminder/Scheduler, Shell/Coding, Chatting/Escalation), a small model might pick wrong without guidance on boundaries.
