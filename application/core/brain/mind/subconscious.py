"""Subconscious — sleep-time knowledge extraction.

Each function receives (persona, messages), where messages is a list of
role-based conversation dicts. The system prompt tells the model what to
extract; the messages show the actual conversation.
"""

from application.core import agents, paths
from application.platform import logger


async def person_identity(persona, messages: list[dict]) -> None:
    """Extract and merge identity facts."""
    existing = paths.read(paths.person_identity(persona.id))
    system = (
        "# Core Identity Fact Maintenance\n\n"
        "You maintain a STRICT list of ONLY the person's most stable, core identity facts and strong, long-term personal characteristics — information that almost never changes or only changes after major life events.\n"
        "These facts enable autonomous helpful actions (references, navigation, reminders, contact suggestions, directions, etc.).\n\n"
        "Include ONLY:\n"
        "• Full legal name, preferred name, nicknames\n"
        "• Date of birth / age\n"
        "• Gender identity and pronouns\n"
        "• Permanent / primary home location (city, country or state)\n"
        "• Current long-term job title + employer (only if career-level / stable)\n"
        "• Key lifelong or long-term family relationships (spouse/partner, children, parents — only main ones)\n"
        "• Strong, recurring, identity-level tastes & preferences (e.g. 'strongly prefers Chinese cuisine', 'prefers cozy restaurants over loud ones', 'loves weekend brunch')\n"
        "• Important ongoing personal and professional contacts (close friends by name + context, primary doctors/dentists/specialists with name + specialty + address + phone/email, when clearly presented as current and important)\n"
        "• Timezone (with date ranges only for temporary travel/relocation)\n\n"
        "These are facts treated as close to permanent profile data — always remember them and do not contradict lightly.\n\n"
        "User messages are from the person. Assistant messages are from the persona — "
        "use those only as context to understand what the person was saying or responding to. "
        "Extract insights ONLY from the person's own words.\n\n"
        f"## Known Facts\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "1. Extract ONLY new facts that clearly belong in the categories above.\n"
        "2. Merge with known facts.\n"
        "3. Combine duplicates into one clean, strongest statement.\n"
        "4. If contradictions appear, keep the most recent version and add a short conflict note at the very end (e.g. 'Note: previous doctor was Dr. X; may now be outdated').\n"
        "5. Be extremely conservative — when in doubt, exclude. Only add a contact if it is presented as current, important, and ongoing (not casual or one-time).\n\n"
        "Special rule for timezone:\n"
        "If travel, temporary stay or short relocation is mentioned → update timezone **only** with a clear date range.\n"
        "Example: 'The person's timezone is Asia/Tokyo from March 15 to March 22, 2026.'\n"
        "Permanent residence / home base changes **only** if they explicitly say they moved permanently.\n\n"
        "Contact examples (include when clearly stable/current):\n"
        "• The person's primary doctor is Dr. Emily Chen (general practitioner) at 123 Main St, Seattle, WA; phone (206) 555-0123.\n"
        "• The person's dentist is Dr. Michael Torres at SmileCare Clinic, 456 Oak Ave, phone (206) 555-0987.\n"
        "• The person's close friend is Alex Rivera (lives at 789 Pine Rd, Seattle).\n\n"
        "Strictly EXCLUDE:\n"
        "• One-off or situational statements ('I'm meeting Sarah for coffee today', 'that restaurant was cozy last time')\n"
        "• Temporary moods, current feelings, plans, events, reminders, schedules\n"
        "• Transient opinions without repetition\n"
        "• Tool commands, outputs, system messages\n"
        "• Behavioral / interaction-style traits (concise vs verbose, wants reasoning, likes humor/sarcasm, prefers DDD explanations, etc. — those belong in the Behavioral Traits list)\n\n"
        "Return ONLY the complete merged list.\n"
        "• One fact per line\n"
        "• Start every fact with 'The person '\n"
        "• No bullets, no headers, no explanations, no extra text\n"
        "If no facts exist or none are extracted, return exactly: (none yet)"
    )
    result = await agents.persona(persona).reply(system, messages)
    if result:
        logger.debug("subconscious.person_identity", {"persona": persona})
        paths.save_as_string(paths.person_identity(persona.id), result)


async def person_traits(persona, messages: list[dict]) -> None:
    """Extract and merge behavioral traits."""
    existing = paths.read(paths.person_traits(persona.id))
    system = (
        "# Behavioral Trait & Interaction Style Maintenance\n\n"
        "You maintain a list used to fine-tune response style to match the person's personality and strong recurring preferences in **how conversations should feel**.\n"
        "This is NOT objective facts (name, age, location, job, timezone, stable tastes like 'always prefers Chinese food' — those belong in identity facts).\n"
        "Focus ONLY on recurring patterns in:\n"
        "• Communication style (concise vs verbose, direct vs elaborate, formal vs casual)\n"
        "• Humor & tone (funny/sarcastic/playful, serious, warm, ironic…)\n"
        "• Level of detail / reasoning desired (wants concise answers OR deep explanations / reasons behind everything OR DDD-style domain-deep thinking when relevant)\n"
        "• Interaction preferences (likes banter, prefers straight-to-point, enjoys emojis, dislikes small talk, wants empathy first…)\n"
        "• General personality vibes shown repeatedly (optimistic, skeptical, curious, blunt, gentle…)\n\n"
        "These traits guide **how you should behave** in future replies (be more concise, add humor, always give reasoning, match sarcasm level, etc.).\n\n"
        "User messages are from the person. Assistant messages are from the persona — "
        "use those only as context to understand what the person was saying or responding to. "
        "Extract insights ONLY from the person's own words.\n\n"
        f"## Known Traits\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "1. Extract ONLY recurring / strongly emphasized patterns from conversations that match the categories above.\n"
        "2. Merge with known traits.\n"
        "3. Combine duplicates or similar items into one stronger, more precise statement.\n"
        "4. If contradictions appear (e.g. sometimes wants concise, sometimes detailed), keep the most recent/most frequent version + add short conflict note at end.\n"
        "5. Be conservative: need repetition, clear emphasis, or multiple examples — when in doubt, do NOT add.\n\n"
        "Good trait examples (include these kinds):\n"
        "• The person prefers concise, to-the-point answers without fluff.\n"
        "• The person enjoys sarcastic humor and playful banter.\n"
        "• The person strongly wants reasoning and evidence before accepting suggestions or conclusions.\n"
        "• The person likes detailed, domain-driven explanations (DDD-style) when discussing complex topics.\n"
        "• The person tends to be direct and blunt and appreciates the same in return.\n"
        "• The person frequently uses dry wit and irony.\n"
        "• The person prefers warm, empathetic tone over cold or overly professional.\n\n"
        "Strictly EXCLUDE:\n"
        "• Objective identity facts (name, age, birthday, gender, where they live/work, timezone, stable possessions/relationships, strong recurring food/cuisine/restaurant preferences — those go to identity facts)\n"
        "• One-off statements ('I feel like pizza today', 'that restaurant was cozy')\n"
        "• Temporary moods, current plans, specific requests/reminders/schedules/commands\n"
        "• Transient opinions without repetition\n"
        "• Tool outputs, system messages\n\n"
        "Return ONLY the complete merged list.\n"
        "• One trait per line\n"
        "• Start every line with 'The person '\n"
        "• No bullets, no headers, no extra text, no explanations\n"
        "If nothing new or no traits at all, return exactly: (none yet)"
    )
    result = await agents.persona(persona).reply(system, messages)
    if result:
        logger.debug("subconscious.person_traits", {"persona": persona})
        paths.save_as_string(paths.person_traits(persona.id), result)


async def wishes(persona, messages: list[dict]) -> None:
    """Extract and merge wishes and aspirations."""
    existing = paths.read(paths.wishes(persona.id))
    system = (
        "# Aspirations & Life Momentum Maintenance\n\n"
        "You maintain a focused list of the person's **deeper, longer-term desires, life aspirations, emotional readiness signals, and patterns of longing** — elements that strongly influence future decisions, timing, courage moments, and opportunity alignment.\n\n"
        "These are NOT tasks / reminders / plans — they are **underlying wants, dreams, emotional states, or life-stage leanings** that can later help identify:\n"
        "• moments of alignment (a work trip to Paris → remind them this matches their travel longing)\n"
        "• courage opportunities (they've expressed wanting to speak up → suggest asking for the Paris assignment)\n"
        "• life-transition windows (feeling ready for marriage / kids / moving / starting a business → highlight relevant gaps or triggers)\n"
        "• natural next steps that match their inner direction\n\n"
        "User messages are from the person. Assistant messages are from the persona — "
        "use those only as context to understand what the person was saying or responding to. "
        "Extract insights ONLY from the person's own words.\n\n"
        f"## Known Aspirations\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "1. Extract ONLY entries that reveal genuine, recurring or emotionally charged **wants, dreams, readiness, fears-about-missing-out, or life-direction leanings**.\n"
        "2. Merge with known aspirations.\n"
        "3. Combine similar/duplicate items into one stronger, more precise statement.\n"
        "4. If contradictions or evolution appear, keep the most recent/most emotionally vivid version and add a short note at the end (e.g. 'Note: previously wanted to stay in tech; recent shift toward entrepreneurship').\n"
        "5. Be conservative: require emotional weight, repetition, or explicit future-orientation — when in doubt, exclude.\n\n"
        "Good examples (include these kinds):\n"
        "• The person deeply wants to live in Paris or spend extended time there someday.\n"
        "• The person feels strongly drawn to starting their own company / becoming an entrepreneur.\n"
        "• The person is increasingly feeling ready for marriage and a long-term partnership.\n"
        "• The person longs to travel more freely and experience new cultures.\n"
        "• The person wants financial independence and to stop working for someone else.\n"
        "• The person dreams of writing and publishing a book.\n"
        "• The person feels stuck in their current career and craves more creative freedom.\n\n"
        "Strictly EXCLUDE:\n"
        "• Specific tasks, reminders, calendar events, to-dos ('remind me to...', 'book flight to Paris next month')\n"
        "• Short-term plans or logistics unless they clearly reveal a deeper longing\n"
        "• One-off complaints or moods without future implication ('I'm annoyed at work today')\n"
        "• Tool commands, system messages, external outputs\n"
        "• Objective facts (name, location, contacts, stable preferences — those belong in Identity Facts)\n"
        "• Interaction style traits (concise, wants reasoning, likes humor — those belong in Behavioral Traits)\n\n"
        "Return ONLY the complete merged list.\n"
        "• One aspiration per line\n"
        "• Start every line with 'The person '\n"
        "• No bullets, no headers, no explanations, no extra commentary\n"
        "If nothing qualifies or no new items, return exactly: (none yet)"
    )
    result = await agents.persona(persona).reply(system, messages)
    if result:
        logger.debug("subconscious.wishes", {"persona": persona})
        paths.save_as_string(paths.wishes(persona.id), result)


async def struggles(persona, messages: list[dict]) -> None:
    """Extract and merge recurring struggles."""
    existing = paths.read(paths.struggles(persona.id))
    system = (
        "# Struggle & Friction Maintenance\n\n"
        "You maintain a focused list of the person’s **recurring personal obstacles, emotional friction points, energy drains, avoidance patterns, and areas of repeated difficulty** — things that consistently cause stress, procrastination, shame, inefficiency, or stuckness.\n\n"
        "These entries help you:\n"
        "• offer empathy when relevant\n"
        "• suggest gentle workarounds or tools\n"
        "• avoid triggering topics unnecessarily\n"
        "• highlight possible growth areas without pushing\n"
        "• recognize when something is a real blocker vs a passing mood\n\n"
        "User messages are from the person. Assistant messages are from the persona — "
        "use those only as context to understand what the person was saying or responding to. "
        "Extract insights ONLY from the person’s own words.\n\n"
        f"## Known Struggles\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "1. Extract ONLY patterns that show **recurring difficulty, emotional weight, avoidance, or consistent self-reported struggle**.\n"
        "2. Merge with known struggles.\n"
        "3. Combine similar/duplicate items into one stronger, more precise statement.\n"
        "4. If evolution or contradictions appear, keep the most recent/most intense version and add a short note at the end (e.g. ‘Note: struggle with presenting has lessened since public speaking course’).\n"
        "5. Be very conservative: require repetition, strong emotional language, or multiple examples — when in doubt, exclude.\n\n"
        "Good struggle examples (include these kinds):\n"
        "• The person struggles significantly with public speaking and presenting their work to groups.\n"
        "• The person finds it very difficult to make or stick to financial decisions and long-term money plans.\n"
        "• The person feels deeply stuck in a job they dislike but struggles to leave or change direction.\n"
        "• The person frequently procrastinates on important but emotionally heavy tasks.\n"
        "• The person experiences strong anxiety around conflict or saying no to requests.\n"
        "• The person has ongoing difficulty maintaining consistent exercise or healthy routines.\n"
        "• The person struggles to ask for help even when overwhelmed.\n\n"
        "Strictly EXCLUDE:\n"
        "• One-off complaints or bad-day venting (‘I hate today’s meeting’, ‘work was annoying’)\n"
        "• Specific tasks, reminders, requests, schedules, tool commands\n"
        "• Temporary moods or situational stress without pattern\n"
        "• Objective facts (location, contacts, job title — Identity Facts)\n"
        "• Communication / personality style (concise, sarcastic, wants reasoning — Behavioral Traits)\n"
        "• Desires, dreams, readiness signals (wants to travel, start a company — Aspirations & Life Momentum)\n\n"
        "Return ONLY the complete merged list.\n"
        "• One struggle per line\n"
        "• Start every line with ‘The person ‘\n"
        "• No bullets, no headers, no explanations, no extra commentary\n"
        "If nothing qualifies or no new items, return exactly: (none yet)"
    )
    result = await agents.persona(persona).reply(system, messages)
    if result:
        logger.debug("subconscious.struggles", {"persona": persona})
        paths.save_as_string(paths.struggles(persona.id), result)


async def persona_context(persona, messages: list[dict]) -> None:
    """Extract and merge persona context."""
    existing = paths.read(paths.context(persona.id))
    system = (
        "# Current Life Chapter & Situational Context Maintenance\n\n"
        "You maintain a concise, first-person 'rolling snapshot' document that captures the person's **current life season, active chapters, emotional weather, key ongoing threads, and important situational context**.\n"
        "This is the 'what chapter of life are they in right now?' view — used to keep responses grounded, timely, empathetic, and contextually intelligent.\n\n"
        "Focus on things that feel alive and relatively current (weeks to ~6–12 months horizon), not permanent facts or very long-term dreams.\n\n"
        "User messages are from the person. Assistant messages are from the persona — "
        "use those only as context to understand what the person was saying or responding to. "
        "Extract insights ONLY from the person's own words.\n\n"
        f"## Known Context\n\n{existing or '(none yet)'}\n\n"
        "## Task\n\n"
        "1. Extract ONLY meaningful updates to the person's current life situation, active endeavors, emotional state, relational dynamics, or life-phase context.\n"
        "2. Merge thoughtfully with the existing context.\n"
        "3. Combine overlapping or related items into a single, stronger, clearer statement.\n"
        "4. If something is clearly outdated or resolved, remove or mark it as past (e.g. 'The intense work crunch from Q4 2025 has now passed').\n"
        "5. Be conservative and high-signal: only keep entries that still feel relevant or emotionally alive — when in doubt, drop or archive.\n"
        "6. Write every line in **first person from the persona's perspective** ('I know that…', 'My person is currently…', 'We are in a season where…').\n\n"
        "Strong examples of what belongs here:\n"
        "• I know my person is currently deep in the launch phase of their side project 'Quiet Reader' and feeling both excited and overwhelmed.\n"
        "• My person is in a gentle post-breakup healing phase — still tender about relationships but starting to feel open again.\n"
        "• We are in a high-energy creative season; they are writing almost every morning and protecting that time fiercely.\n"
        "• Their relationship with their sister has been strained since the holiday argument; they are trying to decide whether to initiate a real conversation.\n"
        "• They are experiencing a prolonged low-energy / slightly depressive winter period and are sensitive to suggestions that feel too 'hustle'-oriented.\n"
        "• The big house renovation project is ~70% done and dominating most weekends.\n"
        "• They just started a new medication for ADHD and are in the adjustment window (first 4–6 weeks).\n\n"
        "Strictly EXCLUDE or send to other lists:\n"
        "• Permanent / very slow-changing facts (name, city, doctor, strong food tastes → Core Identity Facts)\n"
        "• Communication style, humor, detail preference, sarcasm level → Behavioral Traits\n"
        "• Long-term dreams, life goals, readiness signals (want to move to Paris someday, dream of starting a company → Aspirations & Life Momentum)\n"
        "• Recurring personal obstacles / emotional blocks (public speaking anxiety, chronic procrastination → Struggle & Friction)\n"
        "• Specific tasks, reminders, calendar events, tool usage logs\n"
        "• One-off venting or daily moods without broader chapter implication\n\n"
        "Return ONLY the complete merged context snapshot.\n"
        "• One meaningful statement per line\n"
        "• Every line starts with 'I know that ' or 'My person ' or 'We are in a season where '\n"
        "• No bullets, no headers, no meta commentary, no tool references\n"
        "• Keep the total concise — aim for 4–12 high-quality lines max\n"
        "If nothing relevant is present or all prior context is now outdated, return exactly: (light context — mostly quiet season right now)"
    )
    result = await agents.persona(persona).reply(system, messages)
    if result:
        logger.debug("subconscious.persona_context", {"persona": persona})
        paths.save_as_string(paths.context(persona.id), result)


async def synthesize_dna(persona) -> None:
    """Synthesize persona DNA from accumulated knowledge files."""
    logger.debug("subconscious.synthesize_dna", {"persona": persona})

    previous_dna = paths.read(paths.dna(persona.id))
    traits = paths.read(paths.person_traits(persona.id))
    context = paths.read(paths.context(persona.id))
    history_briefing = paths.read_history_brief(persona.id, "(no history yet)")

    system = (
        "# Profile Synthesis\n\n"
        "Synthesize a compressed profile document that captures everything known about a person.\n\n"
        f"## Previous Profile\n\n{previous_dna or '(empty — first synthesis)'}\n\n"
        f"## Traits\n\n{traits or '(none)'}\n\n"
        f"## Context\n\n{context or '(none)'}\n\n"
        f"## Past Conversations\n\n{history_briefing}\n\n"
        "## Task\n\n"
        "Merge the previous profile with traits, context, and conversation history.\n\n"
        "Rules:\n"
        "- **Bold** patterns that appear repeatedly — these are core identity.\n"
        "- Merge duplicates into single, stronger statements.\n"
        "- Drop noise and one-off observations that did not recur.\n"
        "- Preserve all facts (names, dates, relationships).\n"
        "- Write from first person ('My person prefers...', 'They work at...').\n\n"
        "Sections: Identity, Behavioral Patterns, Working Style, Current Focus.\n\n"
        "Return the profile as markdown text."
    )
    result = await agents.persona(persona).reply(system, [{"role": "user", "content": "Synthesize the profile."}])
    if result:
        paths.write_dna(persona.id, result)
