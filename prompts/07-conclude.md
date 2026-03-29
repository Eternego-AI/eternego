# Conclude — Summarize Result

Final message to the person after an action completes. Only runs if `meaning.summarize()` returns a prompt.

Source: `application/core/brain/mind/conscious.py:262`

---

## System Prompt

```
{identity — see 01-character.md}

# This Interaction
{meaning.description()}
{meaning.summarize()}
```

### Example: Reminder conclude

```
{identity}

# This Interaction
The person asks to CREATE or SET a new reminder for a future time. This is about saving a new reminder, not about delivering one that is already due.
The reminder has been set. Confirm briefly — state the time and what it is about. Mention how many upcoming reminders are scheduled, only counting ones that have not yet passed based on the current time.
```

### Example: Scheduler conclude

```
{identity}

# This Interaction
The person asks to CREATE or SCHEDULE a new appointment, meeting, or event at a future time. This is about saving a new event, not about delivering one that is already due.
The event has been scheduled. Confirm briefly — state when it is and what it is about. Mention how many upcoming events are scheduled, only counting ones that have not yet passed based on the current time.
```

### Example: Coding conclude

```
{identity}

# This Interaction
The person wants to write code, create a script, build a project, edit a program, or run code they are working on.
Summarize what was created or changed and where the files are.
```

## Messages

Full thread including tool execution results.

## Expected Response

Free text — the persona's spoken summary.

---

## Audit

### Reminder/Scheduler summarize: "count upcoming" is unreliable
The model is told to "mention how many upcoming reminders are scheduled, only counting ones that have not yet passed." But the model has NO access to the full list of destiny entries. It only sees the conversation thread. It will either hallucinate a count or say "1" because that's all it knows about. This instruction is impossible to follow without the data.

**Fix**: Either inject the count into the prompt, or remove the counting instruction.

### Same "# This Interaction" structure as recognize
Consistent, which is good. Model sees the same pattern across stages.

### Meanings without summarize()
Greeting, Chatting, Shell, Due Notification, Escalation, Query, Noting, Recalling all return `None` for summarize. These skip the conclude stage entirely (the code falls through to using the recap text). This is correct — no unnecessary final message.

### Coding summarize is clean
"Summarize what was created or changed and where the files are." — Direct, actionable.
