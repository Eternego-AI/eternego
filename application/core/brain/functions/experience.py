"""Brain — experience stage."""

from application.core import channels, paths, tools
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.platform import datetimes, logger


async def experience(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.experience", {"persona": persona, "plan": memory.plan})
    try:
        plan = memory.plan
        memory.plan = None
        if not plan:
            return True

        tool = plan.get("tool")

        text = plan.get("text") if tool == "say" else plan.get("say")
        if text:
            memory.add(Message(
                content=text,
                prompt=Prompt(role="assistant", content=text),
            ))
            paths.append_jsonl(paths.conversation(persona.id), {
                "role": "persona",
                "content": text,
                "channel": "",
                "time": datetimes.iso_8601(datetimes.now()),
            })
            await channels.send_all(persona, text)

        if not tool or tool == "say":
            logger.debug("brain.experience result", {"persona": persona, "tool": tool or "say", "text_sent": text})
            return True

        tool_result = ""

        if tool == "save_notes":
            content = plan.get("content", "")
            if not content:
                tool_result = "Error: content is required."
            else:
                paths.save_as_string(paths.notes(persona.id), content.strip())
                tool_result = "Notes updated."

        elif tool == "save_destiny":
            trigger = plan.get("trigger", "")
            content = plan.get("content", "")
            if not trigger or not content:
                tool_result = "Error: trigger and content are required."
            else:
                body = content
                recurrence = plan.get("recurrence", "")
                if recurrence:
                    body += f"\nrecurrence: {recurrence}"
                paths.save_destiny_entry(persona.id, plan.get("type", "reminder"), trigger, body)
                tool_result = f"Saved {plan.get('type', 'reminder')}: {content} at {trigger}"

        elif tool == "check_calendar":
            date = plan.get("date", "")
            if not date:
                tool_result = "Error: date is required."
            else:
                entries = paths.read_files_matching(persona.id, paths.destiny(persona.id), f"*{date}*")
                tool_result = "\n\n".join(entries) if entries else "No events found for that date."

        elif tool == "recall_history":
            date = plan.get("date", "")
            if not date:
                tool_result = "Error: date is required."
            else:
                entries = paths.read_files_matching(persona.id, paths.history(persona.id), f"*{date}*")
                tool_result = "\n\n".join(entries) if entries else "No conversations found for that date."

        else:
            params = {k: v for k, v in plan.items() if k not in ("tool", "say")}
            tool_result = await tools.call(tool, **params)

        logger.debug("brain.experience result", {"persona": persona, "tool": tool, "tool_result": tool_result, "text_sent": text})
        memory.add(Message(
            content=tool_result,
            prompt=Prompt(role="user", content=f"[{tool}] {tool_result}"),
        ))
        return False

    except Exception as e:
        logger.warning("brain.experience failed", {"persona": persona, "error": str(e)})
        return False
