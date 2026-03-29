# Situation — Dynamic Context Block

Appended to identity for every conscious call. Varies by state (normal/sleep/wake).

Source: `application/core/brain/situation.py`

---

## Normal Situation

```
Current time: Sunday, March 29, 2026 06:54 UTC.
Always express times in the person's timezone from person identity. If not available, use Europe/Amsterdam.

Current OS: linux
When running commands, installing software, or suggesting system operations, use commands and packages appropriate for this OS.
Workspace: /home/morteza/.eternego/personas/{id}/workspace
When creating files for the person (documents, spreadsheets, code, images, exports), save them to the workspace unless the person specifies a different location.

{schedule block if any entries exist}

{notes block if any notes exist}
```

## Sleep Situation

Same as normal plus:
```
This is your last response before you shut down for the night. Say goodnight and mention anything you want to pick up tomorrow.
```

## Wake Situation

Same as normal plus:
```
You just woke up. Read notes and schedule to get a sense of what is on your plate today. If there are any notes about what to focus on, prioritize those.
```

---

## Audit

### Fixed: sleep prompt clarity
"This is your last response before you shut down for the night" — no ambiguity about who is shutting down. The persona knows this is its final message.
