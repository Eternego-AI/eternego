"""Brain — experience stage.

Takes the plan decide produced, executes it, and writes two prompts per call
to memory: an assistant-role message with the tool call JSON, then a
user-role TOOL_RESULT message with the outcome. This mirrors the standard
chat-agent convention — the model sees what it decided to do and what came
back, in the format its training expects.

If the plan contains a `say` alongside another tool, they run as two separate
calls (two pairs in memory). Say is always delivered first.
"""

import json as _json

from application.core import paths, tools
from application.core.brain.mind.memory import Memory
from application.core.data import Media, Message, Prompt
from application.platform import datetimes, logger
from application.platform.observer import Command, dispatch, send as send_signal


async def experience(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
    logger.debug("brain.experience", {"persona": persona, "plan": memory.plan})
    plan = memory.plan
    memory.plan = None
    if not plan:
        return True
    try:

        tool = plan.get("tool")
        say_text = plan.get("text") if tool == "say" else plan.get("say")

        if say_text:
            memory.remember(Message(
                content=say_text,
                prompt=Prompt(role="assistant", content=say_text),
            ))
            dispatch(Command("Persona wants to say", {"persona": persona, "text": say_text}))

        if not tool or tool == "say":
            logger.debug("brain.experience result", {"persona": persona, "tool": tool or "say", "text_sent": say_text})
            return True

        call_obj = {k: v for k, v in plan.items() if k != "say"}
        call_json = _json.dumps(call_obj)
        memory.remember(Message(
            content=call_json,
            prompt=Prompt(role="assistant", content=call_json),
        ))

        status = "ok"
        result = ""

        if tool == "save_notes":
            content = plan.get("content", "")
            if not content:
                status, result = "error", "content is required"
            else:
                paths.save_as_string(paths.notes(persona.id), content.strip())
                result = "notes updated"

        elif tool == "save_destiny":
            trigger = plan.get("trigger", "")
            content = plan.get("content", "")
            if not trigger or not content:
                status, result = "error", "trigger and content are required"
            else:
                body = content
                recurrence = plan.get("recurrence", "")
                if recurrence:
                    body += f"\nrecurrence: {recurrence}"
                paths.save_destiny_entry(persona.id, plan.get("type", "reminder"), trigger, body)
                result = f"saved {plan.get('type', 'reminder')}: {content} at {trigger}"

        elif tool == "check_calendar":
            date = plan.get("date", "")
            if not date:
                status, result = "error", "date is required"
            else:
                entries = paths.destinies_in(persona.id, date)
                result = "\n".join(entries) if entries else "no events found for that date"

        elif tool == "recall_history":
            date = plan.get("date", "")
            if not date:
                status, result = "error", "date is required"
            else:
                entries = paths.read_files_matching(persona.id, paths.history(persona.id), f"*{date}*")
                live = paths.read_jsonl(paths.conversation(persona.id))
                live_lines = [
                    f"[{e.get('time', '')}] {e['role']}: {e['content']}"
                    for e in live if date in e.get("time", "")
                ]
                if live_lines:
                    entries.append("Today's conversation:\n" + "\n".join(live_lines))
                gallery_file = paths.media(persona.id) / "gallery.json"
                if gallery_file.exists():
                    gallery = _json.loads(gallery_file.read_text())
                    media_lines = []
                    for source, looks in gallery.items():
                        for look in looks:
                            if date in look.get("time", ""):
                                media_lines.append(f"[{look['time']}] Image: {source} — {look['answer']}")
                    if media_lines:
                        entries.append("Media from that date:\n" + "\n".join(media_lines))
                result = "\n\n".join(entries) if entries else "no conversations found for that date"

        elif tool == "remove_meaning":
            name = plan.get("name", "")
            if not name:
                status, result = "error", "name is required"
            else:
                meaning_path = paths.meanings(persona.id) / f"{name}.py"
                if meaning_path.exists():
                    meaning_path.unlink()
                    memory.unlearn(name)
                    result = f"removed meaning: {name}"
                else:
                    status, result = "error", f"meaning not found: {name}"

        elif tool == "clear_memory":
            memory.forget()
            result = "memory cleared"

        elif tool == "look_at":
            source = plan.get("source", "")
            question = plan.get("question", "")
            if not source:
                status, result = "error", "source is required"
            else:
                memory.remember(Message(
                    content=question,
                    media=Media(source=source, caption=question),
                ))
                result = f"queued vision look at {source}"

        elif tool == "stop":
            await send_signal(Command("Persona requested stop", {"persona": persona}))
            result = "stop requested"

        else:
            params = {k: v for k, v in plan.items() if k not in ("tool", "say")}
            status, result = await tools.call(tool, **params)

        result_text = f"TOOL_RESULT\ntool: {tool}\nstatus: {status}\nresult: {result}"
        memory.remember(Message(
            content=result_text,
            prompt=Prompt(role="user", content=result_text),
        ))

        return False

    except Exception as e:
        logger.warning("brain.experience failed", {"persona": persona, "error": str(e)})
        failed_tool = plan.get("tool", "unknown")
        error_text = f"TOOL_RESULT\ntool: {failed_tool}\nstatus: error\nresult: {e}"
        memory.remember(Message(
            content=error_text,
            prompt=Prompt(role="user", content=error_text),
        ))
        return False
