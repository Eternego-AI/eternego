"""Brain — archive into living.

Runs as part of the subconscious, after reflect has settled and moved
messages to the archive. Walks archived batches looking for vision
tool-call pairs (assistant call + user TOOL_RESULT) and builds a
persistent media map (gallery) so recall_history can surface past images.

No model call — every image arrived at realize, was turned into text via
the eye, and left a `tools.vision` (or `tools.look_at`) pair in memory.
Archive's job is just to file those pairs into the gallery.
"""

from application.core import paths
from application.core.brain.signals import Tick, Tock
from application.platform import datetimes, logger
from application.platform.objects import to_dict
from application.platform.observer import dispatch


async def archive(memory, ego) -> list:
    """archive INTO living — file the residue into deeper storage."""
    dispatch(Tick("archive", {"persona": ego.persona}))

    persona = ego.persona
    logger.debug("brain.archive", {"persona": persona, "archive_": memory.archive})

    gallery_file = paths.gallery(persona.id)
    gallery_file.parent.mkdir(parents=True, exist_ok=True)
    home_str = str(paths.home(persona.id))
    screenshots_dir = str(paths.screenshots(persona.id))

    for batch in memory.archive:
        messages = [m for m in batch if m.prompt]

        for i, m in enumerate(messages):
            if m.prompt.role != "assistant" or not isinstance(m.prompt.content, str):
                continue
            try:
                call = to_dict(m.prompt.content)
            except (ValueError, TypeError):
                continue
            if not isinstance(call, dict) or len(call) != 1:
                continue
            selector, args = next(iter(call.items()))
            if selector not in ("tools.vision", "tools.look_at"):
                continue
            tool_name = selector.split(".", 1)[-1]
            args = args if isinstance(args, dict) else {}

            source = args.get("source", "")
            if not source:
                continue
            # Skip self-taken UI screenshots — those are working memory for
            # the screen-control loop, not material the persona needs to
            # remember as part of her gallery.
            if source.startswith(screenshots_dir):
                continue

            answer = ""
            if i + 1 < len(messages):
                next_msg = messages[i + 1]
                if next_msg.prompt.role == "user" and isinstance(next_msg.prompt.content, str):
                    content = next_msg.prompt.content
                    if content.startswith("TOOL_RESULT") and f"tool: {tool_name}" in content:
                        for line in content.split("\n"):
                            if line.startswith("result: "):
                                answer = line[len("result: "):]
                                break

            if not answer:
                continue

            relative_source = source
            if relative_source.startswith(home_str):
                relative_source = relative_source[len(home_str):].lstrip("/")
            paths.append_jsonl(gallery_file, {
                "source": relative_source,
                "question": args.get("question", ""),
                "answer": answer,
                "time": datetimes.iso_8601(datetimes.now()),
            })

    dispatch(Tock("archive", {"persona": persona}))
    return []
