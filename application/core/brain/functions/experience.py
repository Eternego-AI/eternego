"""Brain — experience stage."""

from application.core import paths, tools
from application.core.brain import meanings
from application.core.brain.mind.memory import Memory
from application.core.data import Media, Message, Persona, Prompt
from application.platform import datetimes, logger
from application.platform.observer import Command, dispatch, send as send_signal


async def experience(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
    logger.debug("brain.experience", {"persona": persona, "plan": memory.plan})
    try:
        plan = memory.plan
        memory.plan = None
        if not plan:
            return True

        tool = plan.get("tool")

        text = plan.get("text") if tool == "say" else plan.get("say")
        if text:
            memory.remember(Message(
                content=text,
                prompt=Prompt(role="assistant", content=text),
            ))
            paths.append_jsonl(paths.conversation(persona.id), {
                "role": "persona",
                "content": text,
                "channel": "",
                "time": datetimes.iso_8601(datetimes.now()),
            })
            dispatch(Command("Persona wants to say", {"persona": persona, "text": text}))

        if not tool or tool == "say":
            logger.debug("brain.experience result", {"persona": persona, "tool": tool or "say", "text_sent": text})
            return True

        if tool == "save_notes":
            content = plan.get("content", "")
            if not content:
                memory.remember(Message(content="Error: content is required."))
            else:
                paths.save_as_string(paths.notes(persona.id), content.strip())
                memory.remember(Message(content="Notes updated."))

        elif tool == "save_destiny":
            trigger = plan.get("trigger", "")
            content = plan.get("content", "")
            if not trigger or not content:
                memory.remember(Message(content="Error: trigger and content are required."))
            else:
                body = content
                recurrence = plan.get("recurrence", "")
                if recurrence:
                    body += f"\nrecurrence: {recurrence}"
                paths.save_destiny_entry(persona.id, plan.get("type", "reminder"), trigger, body)
                memory.remember(Message(content=f"Saved {plan.get('type', 'reminder')}: {content} at {trigger}"))

        elif tool == "check_calendar":
            date = plan.get("date", "")
            if not date:
                memory.remember(Message(content="Error: date is required."))
            else:
                entries = paths.destinies_in(persona.id, date)
                memory.remember(Message(content="\n".join(entries) if entries else "No events found for that date."))

        elif tool == "recall_history":
            date = plan.get("date", "")
            if not date:
                memory.remember(Message(content="Error: date is required."))
            else:
                entries = paths.read_files_matching(persona.id, paths.history(persona.id), f"*{date}*")
                live = paths.read_jsonl(paths.conversation(persona.id))
                live_lines = [
                    f"[{e.get('time', '')}] {e['role']}: {e['content']}"
                    for e in live if date in e.get("time", "")
                ]
                if live_lines:
                    entries.append("Today's conversation:\n" + "\n".join(live_lines))
                import json
                gallery_file = paths.media(persona.id) / "gallery.json"
                if gallery_file.exists():
                    gallery = json.loads(gallery_file.read_text())
                    media_lines = []
                    for source, looks in gallery.items():
                        for look in looks:
                            if date in look.get("time", ""):
                                media_lines.append(f"[{look['time']}] Image: {source} — {look['answer']}")
                    if media_lines:
                        entries.append("Media from that date:\n" + "\n".join(media_lines))
                memory.remember(Message(content="\n\n".join(entries) if entries else "No conversations found for that date."))

        elif tool == "remove_meaning":
            name = plan.get("name", "")
            if not name:
                memory.remember(Message(content="Error: name is required."))
            else:
                meaning_path = paths.meanings(persona.id) / f"{name}.py"
                if meaning_path.exists():
                    meaning_path.unlink()
                    memory.unlearn(name)
                    memory.remember(Message(content=f"Removed meaning: {name}"))
                else:
                    memory.remember(Message(content=f"Meaning not found: {name}"))

        elif tool == "clear_memory":
            memory.forget()
            memory.remember(Message(content="Memory cleared."))

        elif tool == "look_at":
            source = plan.get("source", "")
            question = plan.get("question", "")
            if not source:
                memory.remember(Message(content="Error: source is required."))
            else:
                memory.remember(Message(
                    content=question,
                    media=Media(source=source, caption=question),
                ))

        elif tool == "stop":
            await send_signal(Command(
                "Persona requested stop",
                {"persona": persona},
            ))
            memory.remember(Message(content="Stop requested."))

        else:
            params = {k: v for k, v in plan.items() if k not in ("tool", "say", "reason")}
            result_message = await tools.call(tool, **params)
            memory.remember(result_message)


        return False

    except Exception as e:
        logger.warning("brain.experience failed", {"persona": persona, "error": str(e)})
        error_msg = f"[tool_error] {e}"
        memory.remember(Message(
            content=error_msg,
            prompt=Prompt(role="user", content=error_msg),
        ))
        return False
