"""Current — the present state injected as context into every reasoning call.

time()                   — current date and time as readable text.
environment()            — the operating system and platform.
tools(meaning)           — Tool instances filtered by meaning (or all if None).
skills(persona, meaning) — Skill instances filtered by meaning (or all if None).
situation(persona)       — all combined as string; pass as the system param to ego.reason.
"""

from application.core.brain.data import Tool, Skill
from application.platform import datetimes, OS


def time() -> str:
    now = datetimes.now()
    return f"Current time: {now.strftime('%A, %B %d, %Y %H:%M UTC')}"


def environment() -> str:
    os_name = OS.get_supported() or "unknown"
    return f"Environment: {os_name}"


def tools(meaning=None) -> list[Tool]:
    from application.core.brain import tools as brain_tools
    selected = meaning.tools if meaning is not None else None
    return [
        t for t in brain_tools.all_tools()
        if selected is None or t.name in selected
    ]


def skills(persona, meaning=None) -> list[Skill]:
    from application.core.brain import skills as brain_skills
    selected = meaning.skills if meaning is not None else None
    if selected:
        return [s for s in brain_skills.all_skills() if s.name in selected]
    return brain_skills.all_skills()


def situation(persona, meaning=None) -> str:
    tool_list = tools(meaning)
    skill_list = skills(persona, meaning)
    selected_skills = meaning.skills if meaning is not None else None

    tool_instructions = [t.instruction for t in tool_list if t.instruction]

    if selected_skills:
        skill_parts = [s.execution()(persona) for s in skill_list]
        skills_section = "# Skills\n\n" + "\n\n---\n\n".join(skill_parts) if skill_parts else ""
    else:
        desc_lines = ["Available skills:"] + [
            f"- {s.name}: {s.description}" for s in skill_list if s.description
        ]
        skills_section = "\n".join(desc_lines) if skill_list else ""

    parts = [time(), environment()] + tool_instructions + ([skills_section] if skills_section else [])
    return "\n\n".join(p for p in parts if p)
