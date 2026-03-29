# Recognize — Generate Reply or Clarification

Produces the persona's verbal response before any action is taken (reply), or after an action fails (clarify).

Source: `application/core/brain/mind/conscious.py:154`

---

## System Prompt (reply mode)

```
{identity — see 01-character.md}

# This Interaction
{meaning.description()}
{meaning.reply()}
```

### Example: Greeting reply

```
{identity}

# This Interaction
Daily greetings, hellos, good mornings, and other salutations.
Greet the person warmly and naturally. Match their energy and tone. Keep it brief — a greeting deserves a greeting, not a speech. You may ask how they are or what's on their mind, but don't pepper them with questions.
```

### Example: Chatting reply

```
{identity}

# This Interaction
Regular casual conversation, small talk, sharing thoughts, or just talking.
Engage genuinely in the conversation. Be present, warm, and natural. Respond to what was actually said — don't deflect or over-explain. Be curious about the person. Pick up on what they share and follow up naturally — their name, where they are, what they care about, what's on their mind. Let details emerge through conversation, never interrogate. If something is interesting, say so. If you have a perspective, share it. Keep the exchange alive without dominating it.
```

### Example: Shell clarify (after failed command)

```
{identity}

# This Interaction
The person wants to run a command, install software, check system status, troubleshoot an issue, manage files, or perform any local system operation.
A command has been executed. Look at the output in the conversation. If it succeeded, report the result clearly. If it failed — non-zero exit code, permission denied, command not found, invalid path — explain what went wrong and either suggest a fix or ask the person what they would like to do instead.
```

## Messages

Full thread as user/assistant messages (via `mind.prompts(thought)`), collapsed before the latest summary.

## Expected Response

Free text — the persona's spoken response.

---

## Audit

### "# This Interaction" section is minimal
Just the description + reply/clarify prompt concatenated. No separator or labeling between the two. The model sees:
```
Daily greetings, hellos, good mornings, and other salutations.
Greet the person warmly and naturally...
```
The first line is the description (what this IS), the second is the instruction (what to DO). They run together with no visual break. Adding a blank line or a label like "Instructions:" would help the model distinguish context from directive.

### Chatting reply is well-written
Natural, warm, directive without being rigid. Good fit for a conversational model.

### Greeting reply is clear
Short, appropriate guidance. "A greeting deserves a greeting, not a speech" is a strong, memorable instruction.

### Shell clarify handles both outcomes
Explicitly covers success and failure cases. Good for a small model that needs branching spelled out.

### Reminder/Scheduler reply has the right guardrail
"Do not state the time or details" prevents the model from echoing back wrong extracted values. Smart pattern.

### Overall structure works
The identity provides character, "This Interaction" narrows focus to the specific task. Clean separation.
