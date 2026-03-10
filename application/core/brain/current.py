"""Current — the present state injected as context into every reasoning call.

time()                                  — current date and time as readable text.
environment()                           — the operating system and platform.
tools(selected)                         — Tool instances filtered by name list (or all if None).
skills(persona, selected)               — Skill instances filtered by name list (or all if None).
situation(persona, tool_names, skill_names) — all combined as string; pass as system param to ego.reason.
"""

from application.core.brain.data import Tool, Skill
from application.platform import datetimes, OS


def time() -> str:
    now = datetimes.now()
    return (
        f"Current time: {now.strftime('%A, %B %d, %Y %H:%M UTC')}\n"
    )


def environment() -> str:
    os_name = OS.get_supported() or "is unknown, consider a unix based os"
    return f"Environment: {os_name}"


def tools(selected: list[str] | None = None) -> list[Tool]:
    from application.core.brain import tools as brain_tools
    if selected is None:
        return [brain_tools.all_tools()]

    result = []
    for name in selected:
        t = brain_tools.for_name(name)
        if t is not None:
            result.append(t)
    return result


def skills(persona, selected: list[str] | None = None) -> list[Skill]:
    from application.core.brain import skills as brain_skills
    # TODO: Add persona-specific skills

    if selected is None:
        selected = []

    return [s for s in brain_skills.built_in(persona) if s.name in selected]


def situation(persona, tool_names: list[str] | None = None, skill_names: list[str] | None = None) -> str:
    tool_list = tools(tool_names)
    skill_list = skills(persona, skill_names)

    tool_instructions = [t.instruction for t in tool_list if t.instruction]

    if skill_names:
        skill_parts = [s.document() for s in skill_list]
        skills_section = "# Skills\n\n" + "\n\n---\n\n".join(skill_parts) if skill_parts else ""
    else:
        desc_lines = ["Available skills:"] + [
            f"- {s.name}: {s.description}" for s in skill_list if s.description
        ]
        skills_section = "\n".join(desc_lines) if skill_list else ""

    parts = [time(), environment()] + tool_instructions + ([skills_section] if skills_section else [])
    return "\n\n".join(p for p in parts if p)
