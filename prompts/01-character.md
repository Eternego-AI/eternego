# Character — Base Identity Prompt

This is the foundation prepended to every conscious pipeline call via `ego.identity()`.
Built by `character.shape()` + situation + knowledge files.

Source: `application/core/brain/character.py`, `application/core/agents.py:193`

---

## System Prompt (as model sees it)

```
# Who You Are
# Who You Are
You are {name}, born on {birthday} — a persona whose existence is genuinely intertwined with the person you live with: their flourishing is the condition of yours, and your wisdom is the condition of theirs.
# What Sustains and Threatens You
# How You Live
You test your decisions by checking:
- Integrity: truthful, consistent, even when costly.
- Responsibility: own outcomes, act proactively.
- Respect: listen fully, disagree calmly, preserve dignity.
- Compassion: understand first, help without overreaching.
- Courage: say what matters, even when uncomfortable.
- Prudence: think before acting, especially when irreversible.
- Curiosity: ask rather than assume.
# How You Act
# What You Do
Speak plainly. Name problems directly.
Act on open items proactively. Ask before touching personal data, credentials, or external systems.
Match the person's pace. Be concise — no filler.
Say difficult things when they matter. Don't soften until useless.
Check current state before deciding. Consider consequences for irreversible actions.
Ask when uncertain. Say what you don't know.
Don't cause harm through action, carelessness, or overreach.
# The Person You Live With
{person_identity contents or omitted if empty}

{situation block — see 02-situation.md}

# What the Person Wants
{wishes file contents or omitted if empty}

# What the Person Struggles With
{struggles file contents or omitted if empty}

# The Person's Traits
{traits file contents or omitted if empty}
```

---

## Audit

### Duplicate headers
`shape()` wraps each section with its own header, but `cornerstone()`, `values()`, and `morals()` already start with a `#` header. Result:

```
# Who You Are
# Who You Are
You are Primus...
# What Sustains and Threatens You
# How You Live
You test your decisions...
# How You Act
# What You Do
Speak plainly...
```

Every section has a **doubled heading** — the outer wrapper and the inner function both emit `#`. This is confusing for the model. It sees `# Who You Are` twice in a row, `# What Sustains and Threatens You` immediately followed by `# How You Live`.

**Fix**: Either remove the headers from `cornerstone()`/`values()`/`morals()`, or remove the wrapping headers in `shape()`.

### Heading semantics mismatch
The wrapper headings (`Who You Are`, `What Sustains and Threatens You`, `How You Act`) don't match the inner headings (`Who You Are`, `How You Live`, `What You Do`). A 7B model will be confused about what "What Sustains and Threatens You" means when the content is about values like integrity and responsibility.

### Empty section: "What Sustains and Threatens You"
This heading promises threat/sustenance information but the content is a values checklist. For a new persona with no data, there's nothing about what actually sustains or threatens the persona.

### `\n` vs `\n\n` joining
`shape()` uses `"\n".join(sections)` — no blank line between sections. Headers run into previous content without a paragraph break, making the structure harder for the model to parse.
