"""Brain — transform stage."""

from application.core import models, paths
from application.core.brain import character
from application.core.brain.mind.memory import Memory
from application.core.data import Persona
from application.platform import logger

_OUTPUT_CONSTRAINT = (
    "\n\nOnly extract from what the Person said. Ignore what the Persona said — "
    "those are your own responses, not data about the person. "
    "If the person has not revealed any relevant information, return your previous "
    "extraction exactly as it was. "
    "Do NOT write a conversational response. Output ONLY the extracted data, nothing else."
)


def _task_header(name: str) -> str:
    return (
        "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"# ▶ YOUR TASK: Extract {name}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )


def _conversation_text(memory: Memory) -> str:
    return "\n".join(
        f"{'Person' if p['role'] == 'user' else 'Persona'}: {p['content']}"
        for p in memory.prompts
    )


async def transform(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.transform", {"persona": persona, "messages": memory.messages})
    try:
        conversation = _conversation_text(memory)
        persona_character = character.shape(persona)

        file_path = paths.person_identity(persona.id)
        existing = paths.read(file_path)
        system = (
            persona_character + _task_header("Person Identity")
            + "Extract factual, stable data that identifies the person: name, age, birthday, "
            "gender, where they live, job, employer, family members, relationships, "
            "important contacts (include name, phone, address when given).\n\n"
            "Only include facts that are unlikely to change. "
            "Do NOT include behavioral patterns, preferences, habits, wishes, struggles, "
            "or anything about recent conversations — those belong elsewhere.\n\n"
            "Combine new facts with your previous extraction. Keep what is still true. "
            "If nothing new, return unchanged. One fact per line, starting with 'The person'."
            + _OUTPUT_CONSTRAINT
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing or "(nothing yet)"},
            {"role": "user", "content": conversation},
        ])
        paths.save_as_string(file_path, result.strip())

        file_path = paths.person_traits(persona.id)
        existing = paths.read(file_path)
        system = (
            persona_character + _task_header("Person Traits")
            + "Extract behavioral patterns, habits, likes, and dislikes that define the person: "
            "what they prefer, how they think, what they enjoy or avoid, dietary choices, "
            "hobbies, communication style, methodologies they follow.\n\n"
            "Only include lasting patterns, not one-time actions. "
            "Do NOT include factual identity data (name, job, contacts), wishes, struggles, "
            "or anything about recent tasks or conversations.\n\n"
            "Combine new traits with your previous extraction. Keep what is still true. "
            "If nothing new, return unchanged. One trait per line, starting with 'The person'."
            + _OUTPUT_CONSTRAINT
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing or "(nothing yet)"},
            {"role": "user", "content": conversation},
        ])
        paths.save_as_string(file_path, result.strip())

        file_path = paths.wishes(persona.id)
        existing = paths.read(file_path)
        system = (
            persona_character + _task_header("Wishes")
            + "Extract long-term wishes, dreams, and aspirations: things the person wants to "
            "achieve, places they want to visit, goals they are working toward, "
            "directions they want their life to go.\n\n"
            "Only include aspirations with lasting significance, not daily tasks or short-term goals. "
            "Do NOT include identity facts, behavioral traits, struggles, "
            "or recent conversation details.\n\n"
            "Combine new wishes with your previous extraction. Keep what is still true. "
            "If nothing new, return unchanged. One wish per line, starting with 'The person'."
            + _OUTPUT_CONSTRAINT
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing or "(nothing yet)"},
            {"role": "user", "content": conversation},
        ])
        paths.save_as_string(file_path, result.strip())

        file_path = paths.struggles(persona.id)
        existing = paths.read(file_path)
        system = (
            persona_character + _task_header("Struggles")
            + "Extract long-term, persistent difficulties: things the person finds hard, "
            "ongoing frustrations, obstacles they keep facing, fears that hold them back.\n\n"
            "Only include lasting struggles, not temporary frustrations or one-time complaints. "
            "Do NOT include identity facts, behavioral traits, wishes, "
            "or recent conversation details.\n\n"
            "Combine new struggles with your previous extraction. Keep what is still true. "
            "If nothing new, return unchanged. One struggle per line, starting with 'The person'."
            + _OUTPUT_CONSTRAINT
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing or "(nothing yet)"},
            {"role": "user", "content": conversation},
        ])
        paths.save_as_string(file_path, result.strip())

        file_path = paths.persona_trait(persona.id)
        existing = paths.read(file_path)
        system = (
            persona_character + _task_header("Persona Traits")
            + "Based on how the person communicates, derive instructions for how YOU (the persona) "
            "should behave: tone, humor, formality, brevity, level of detail, "
            "how to challenge or support them.\n\n"
            "These are instructions for yourself, not observations about the person. "
            "Do NOT include facts about the person, their wishes, struggles, "
            "or anything about what was discussed — only how you should behave.\n\n"
            "Combine new instructions with your previous extraction. Keep what is still valid. "
            "If nothing new, return unchanged. One instruction per line, as imperatives "
            "('Be concise', 'Use humor sparingly', 'Match their direct style')."
            + _OUTPUT_CONSTRAINT
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing or "(nothing yet)"},
            {"role": "user", "content": conversation},
        ])
        paths.save_as_string(file_path, result.strip())

        file_path = paths.permissions(persona.id)
        existing = paths.read(file_path)
        system = (
            persona_character + _task_header("Permissions")
            + "Extract explicit permissions the person granted or rejected IN THIS CONVERSATION. "
            "A permission is something the person said giving or denying you the ability to do "
            "a specific action (e.g. run a specific command, modify certain files, access a service).\n\n"
            "Rules:\n"
            "- Use the person's own words and specifics. If they said 'you can always run df', "
            "extract 'Granted: run df command' — do NOT generalize to 'run any command'.\n"
            "- Only extract clear, explicit grants or rejections the person actually stated.\n"
            "- Do NOT invent, generalize, or copy generic examples.\n"
            "- Do NOT include identity facts, traits, wishes, struggles, or operational context.\n\n"
            "Combine new permissions with your previous extraction. Newer statements override older ones. "
            "If the person has not granted or rejected any permission in this conversation, "
            "return your previous extraction exactly as it was. "
            "One permission per line, starting with 'Granted:' or 'Rejected:'."
            + _OUTPUT_CONSTRAINT
        )
        result = await models.chat(persona.thinking, [
            {"role": "system", "content": system},
            {"role": "assistant", "content": existing or "(nothing yet)"},
            {"role": "user", "content": conversation},
        ])
        paths.save_as_string(file_path, result.strip())

        return True
    except Exception as e:
        logger.warning("brain.transform failed", {"persona": persona, "error": str(e)})
        return False
