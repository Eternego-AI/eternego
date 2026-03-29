# Escalation — Generate New Meaning

Runs when no existing meaning matches. Generates Python code for a new Meaning class.

Source: `application/core/agents.py:225`

---

## System Prompt

(Sent to frontier model, not local. Included for completeness.)

```
# Meaning Generation

A persona has a cognitive pipeline that processes interactions in five stages:
  realize → understand → recognize → decide → conclude

A **Meaning** is a Python class that defines how the persona handles a specific type of interaction. When no existing Meaning matches, a new one must be created.

## How Meanings Work in the Pipeline

Each Meaning method maps to a pipeline stage. A small local model executes these — prompts must be explicit, unambiguous, and structured.

### `name` (class attribute)
A specific, descriptive identifier. This appears in the recognition list alongside existing meanings, so it must be **narrower and more specific** than built-in names. The local model picks meanings by name + description, so specificity avoids collisions.
Good: 'Weather Forecast Lookup', 'Email Draft Composition'
Bad: 'Helper', 'Task', 'Utility'

### `description() → str`
One sentence defining exactly what interactions this meaning covers. Used by the understand stage to match a conversation to this meaning. Must be distinct from every existing meaning — if it overlaps, the local model will pick the wrong one.

### `reply() → str | None`
Prompt for the **recognize** stage — how to respond to the person on first contact. This runs BEFORE any action is taken.
CRITICAL: The reply output is appended to the conversation thread and becomes visible to the decide stage. Never ask the model to state specific extracted values (times, dates, names, quantities) in the reply — if it gets them wrong, the error propagates into the extraction. Keep it to a brief acknowledgment.
Return None if no verbal response is needed before acting.

### `clarify() → str | None`
Prompt for retry after an error. Only runs when an action has failed and the conversation already contains an error message. Tell the model to look at the error, explain what went wrong, and ask the person to confirm or correct.
Return None if retries should be silent.

### `path() → str | None`
Prompt for the **decide** stage — tells the local model what structured data to extract or what action to take. The model sees the full conversation thread and must return JSON.
CRITICAL: Tell the model to extract information from what the **person** said, not from assistant messages in the thread.
For tool-using meanings, reference tools by their exact name and define the exact JSON schema the model must return.
Return None for conversational-only meanings (no action needed).

### `summarize() → str | None`
Prompt for the **conclude** stage — the final message to the person after the action completes. Should confirm what was done. Return None to skip.

### `run(persona_response: dict)` — do NOT implement unless needed
The default `run()` dispatches tool calls from the JSON that `path()` produced. Do not override it unless the meaning needs custom logic (like file I/O).
`run()` returns an async callable or None. The callable is executed by the pipeline, which handles all errors. The callable returns a string (execution output fed back to the conversation) or None (success, nothing to report).
Raise exceptions for validation failures — do not catch them.
Example override:
    async def run(self, persona_response: dict):
        value = persona_response.get('key', '')
        if not value:
            raise ValueError('key is missing')
        async def action():
            return do_something(value)
        return action

## Conversation That Triggered Escalation

{thread_text}

## Available Tools

{tools_text or "(no tools available)"}

## Existing Meanings (do not duplicate or overlap)

{meanings_text}

## Output

Return ONLY valid Python source code. No markdown fences, no explanation.
Only import: `from application.core.brain.data import Meaning`

from application.core.brain.data import Meaning


class SpecificDescriptiveName(Meaning):
    name = "Specific Descriptive Name"

    def description(self):
        return "Narrow, specific description of what this covers."

    def clarify(self):
        return "Look at the error. Explain what went wrong and ask the person to correct."

    def reply(self):
        return "Acknowledge briefly. Do not restate extracted details."

    def summarize(self):
        return "Confirm what was done."

    def path(self):
        return (
            "Extract X from what the person said (ignore assistant messages).\n"
            'Return JSON: {"tool": "name", "param": "value"}\n'
        )
```

---

## Audit

### Well-structured and thorough
This is the most detailed prompt in the system. Each method is explained with its pipeline stage, purpose, and critical constraints. The CRITICAL warnings about reply contaminating decide are important.

### Code template at the end is helpful
Giving the model a skeleton to fill in reduces structural errors.

### "Return ONLY valid Python source code" + trailing code
The prompt ends with an actual code skeleton after saying "no markdown fences, no explanation." This is effective — the model sees the format it should produce.

### Risk: generated meanings may not work with small models
The frontier model generates prompts that a small local model must follow. If the frontier writes sophisticated prompts (as large models tend to), the small model may fail to execute them properly. No guardrail for this.

### "Only import: `from application.core.brain.data import Meaning`"
This prevents the generated meaning from importing anything dangerous. But it also prevents it from importing `paths`, `datetimes`, or tools that built-in meanings use. If the meaning needs file I/O, it's stuck.
