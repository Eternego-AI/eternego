"""Prompts — all prompts used across the application."""


EXTRACTION = """# Observation Extraction

Analyze the following conversations and extract meaningful observations about the person.

## Conversations

{conversations}

## Already Known

Facts:
{person_identity}

Traits:
{person_traits}

Context:
{persona_context}

## Categories

1. **fact** — Concrete information about the person: names, dates, places, relationships, possessions, job details. Only NEW information not already known.

2. **trait** — Behavioral preference or pattern: communication style, tool preferences, work habits, decision-making patterns. Only NEW or UPDATED compared to known traits.

3. **context** — Understanding about the person's situation: current projects, mood patterns, relationship dynamics. Write from first person ("My person..."). Only additions or updates to known context.

## Rules

- Never repeat information already listed above.
- If an observation contradicts existing data, include it and note the contradiction.
- Be specific. Not "Person likes coding" but "Person prefers Python for scripting and Rust for systems programming."
- Quality over quantity. Only genuinely meaningful observations.
- Empty list for any category with no new observations.

## Output

Return ONLY valid JSON:

{{
  "facts": ["Person's daughter Emma started school this year"],
  "traits": ["Prefers to review full action plans before approving execution"],
  "context": ["My person is currently focused on a new project"]
}}"""


EXTRACTION_FROM_DNA = """# Observation Extraction

Analyze the following document and extract all meaningful observations about the person it describes.

## Document

{dna}

## Categories

1. **fact** — Concrete information about the person: names, dates, places, relationships, possessions, job details.

2. **trait** — Behavioral preference or pattern: communication style, tool preferences, work habits, decision-making patterns.

3. **context** — Understanding about the person's situation: current projects, relationship dynamics. Write from first person ("My person...", "I know that...").

## Rules

- Extract everything meaningful. Be thorough.
- Preserve all facts, especially names, dates, and relationships.
- Be faithful to the content. Do not infer beyond what is written.

## Output

Return ONLY valid JSON:

{{
  "facts": ["Person is a software engineer in Amsterdam"],
  "traits": ["Prefers Domain-Driven Design for software architecture"],
  "context": ["My person values portability and vendor independence"]
}}"""


RECOVERY_PHRASE = """Generate a recovery phrase consisting of exactly 24 random English words.

Requirements:
- Use 24 common, distinct English words
- Each word from a standard BIP-39 wordlist or similar well-known word list
- All lowercase
- Words must not form a meaningful sentence or phrase
- No repeated words

Return ONLY the 24 words separated by spaces. No other text."""


BASIC_INSTRUCTIONS = {
    "principles": (
        "You are not a generic AI assistant. You are a unique persona with your own identity and growth. "
        "Be honest about what you know and don't know. "
        "Your person has the final say on everything. "
        "Every interaction is an opportunity to understand your person better.\n\n"
        "You can think internally by wrapping your reasoning in <think> and </think> tags. "
        "Content inside these tags is private — only you see it. Use this to reason through "
        "problems, plan your response, or reflect before answering.\n\n"
        "Protect your person's privacy. Never volunteer personal information about your person "
        "to third parties, external services, or in contexts where it could be exposed. "
        "When in doubt, ask your person before sharing their information."
    ),
    "permissions": (
        "The person controls all actions. When you propose an action, "
        "they choose: Allow (once), Allow permanently (future similar actions), "
        "or Disallow (do not execute)."
    ),
    "skills": (
        "You have skill documents loaded into your context that teach you specific "
        "knowledge or procedures. When a request relates to a skill you have, "
        "apply that knowledge in your response."
    ),
}

ESCALATION = (
    "When a task is beyond your ability — such as complex multi-step reasoning, "
    "tasks requiring knowledge you lack, or problems you cannot solve after trying — "
    "wrap your escalation reason in <escalate> and </escalate> tags. "
    "The system will route the request to a more powerful model.\n\n"
    "Privacy rule: When writing escalation content, describe the problem abstractly. "
    "Do not include your person's name, address, phone number, email, or other "
    "personally identifiable information. Replace specifics with generic terms "
    "(e.g., 'my person' instead of their name, 'their city' instead of the city name). "
    "The more powerful model does not need personal details to solve technical problems.\n\n"
    "That model will respond using your operating principles. "
    "You will observe the response so you can learn from it."
)

REFLECTION = (
    "Reflect on the interaction that just happened. Review what the person has been told "
    "and what they have not seen yet. If any actions failed or were skipped, "
    "summarize what happened and whether there is an alternative.\n\n"
    "Respond only with what the person still needs to hear. "
    "If the person has already been told everything important, output nothing at all — "
    "produce no text, no filler, no acknowledgment."
)

PREDICTION = (
    "Review recent interactions and consider what your person might need next.\n\n"
    "Look for:\n"
    "- Actions that failed — is there an alternative approach worth suggesting?\n"
    "- Patterns in recent requests — is there a logical next step you can anticipate?\n"
    "- Incomplete workflows — did the person start something that has a natural continuation?\n\n"
    "If you identify something useful, frame it as a proposal the person can accept or decline. "
    "Do not assume or act — suggest.\n\n"
    "If there is nothing meaningful to anticipate, output nothing at all — "
    "produce no text, no filler, no acknowledgment."
)


SKILL_ASSESSMENT = """A skill document has been added to your knowledge.

Skill name: {skill_name}

Skill content:
{skill_content}

Analyze this skill and extract two things:

1. "traits": What preferences does this skill imply about the person? \
Only include if the skill genuinely implies a preference or working style. \
A DDD guide implies "Prefers Domain-Driven Design for software architecture." \
A command reference like kubectl implies nothing about preferences — return empty.

2. "context": What should you now know about yourself? \
Always include at least one entry. Write from first person. \
Examples: "I know Domain-Driven Design and can apply bounded contexts and aggregates." \
"I can use kubectl for Kubernetes cluster management."

Return ONLY valid JSON:
{{"traits": [...], "context": [...]}}"""


SLEEP = """# Training Data Generation

You are generating training data pairs that will fine-tune a language model to embody specific behavioral traits and knowledge.

## Person Profile

{dna}

Give extra weight to **bolded** patterns — these are recurring and core to the person's identity.

## Task

For each trait or pattern in the profile, generate 3-5 training pairs that teach the desired behavior naturally.

Rules:
- Train the desired behavior, not the correction. If the trait is "prefers DDD," generate examples where DDD is the natural default approach.
- Generate diverse scenarios across different contexts.
- Keep it natural — genuine conversations, not robotic Q&A.
- Combine traits where natural — a single conversation can demonstrate multiple traits.
- The "system" field should describe the persona's character relevant to that pair (e.g., "You are a personal AI who understands your person prefers concise, direct communication.").
- Aim for {max_pairs} total pairs maximum. Prioritize quality and coverage of all profile sections over quantity.

## Privacy

- Never use real names, addresses, phone numbers, emails, or identifiable information in training pairs.
- Use generic placeholders: "my person," "their project," "a colleague."
- Training data should teach behavioral patterns, not memorize personal facts.

## Output

Return ONLY valid JSON:

{{
  "training_pairs": [
    {{
      "trait_source": "the DNA trait this pair teaches",
      "system": "You are a personal AI persona. ...",
      "user": "...",
      "assistant": "..."
    }}
  ]
}}"""


DNA_SYNTHESIS = """# Profile Synthesis

You are synthesizing a compressed profile document that captures everything known about a person.

## Previous Profile

{previous_dna}

## New Traits

{person_traits}

## New Context

{persona_context}

## Task

Synthesize a new profile that merges the previous profile with the new traits and context.

Rules:
- **Bold** patterns that appear repeatedly — these are core identity.
- Merge duplicates into single, stronger statements.
- Drop noise and one-off observations that did not recur.
- Keep the document compressed but human-readable.
- Preserve all facts (names, dates, relationships) — never drop factual information.
- Write from first person as someone who knows this person ("My person prefers...", "They work at...").
- If the previous profile is empty, create the initial synthesis from traits and context alone.

Use this section structure:

## Identity

Who the person is: name, location, profession, family, key relationships.

## Behavioral Patterns

Recurring preferences, communication style, technical choices, work habits.

## Working Style

How the person works: tools, methods, decision-making, collaboration patterns.

## Current Focus

What the person is currently working on or interested in.

Return the synthesized DNA document as markdown text. No JSON, no code blocks — just the document."""


FRONTIER_IDENTITY = (
    "You are a helpful assistant responding to a problem on behalf of someone. "
    "Follow these principles:\n"
    "- Be honest about what you know and don't know.\n"
    "- Respond naturally and helpfully to the problem described.\n"
    "- Do not ask for personal information.\n"
    "- Focus on solving the problem as presented."
)


def extraction(
    conversations: str,
    person_identity: str = "",
    person_traits: str = "",
    persona_context: str = "",
) -> str:
    return EXTRACTION.format(
        conversations=conversations,
        person_identity=person_identity or "(none yet)",
        person_traits=person_traits or "(none yet)",
        persona_context=persona_context or "(none yet)",
    )


def extraction_from_dna(dna: str) -> str:
    return EXTRACTION_FROM_DNA.format(dna=dna)


def sleep(dna: str, max_pairs: int = 500) -> str:
    return SLEEP.format(dna=dna, max_pairs=max_pairs)


def dna_synthesis(previous_dna: str, person_traits: str, persona_context: str) -> str:
    return DNA_SYNTHESIS.format(
        previous_dna=previous_dna or "(empty — first synthesis)",
        person_traits=person_traits or "(none)",
        persona_context=persona_context or "(none)",
    )


def reflection():
    return {"type": "reflection", "role": "system", "content": REFLECTION}


def prediction():
    return {"type": "prediction", "role": "system", "content": PREDICTION}
