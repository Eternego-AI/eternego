"""Brain — archive stage.

Runs as part of the subconscious, after reflect has settled and moved
messages to the archive. Walks archived batches looking for vision
tool-call pairs (assistant call + user TOOL_RESULT) and builds a
persistent media map (gallery) so recall_history can surface past images.

For images that were processed inline (no vision model — image content
blocks in the prompt), archive asks the thinking model what it saw in
the context of the conversation.
"""

from application.core import models, paths
from application.core.brain.mind.memory import Memory
from application.core.exceptions import ModelError
from application.platform import datetimes, logger
from application.platform.objects import to_dict


async def archive(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
    logger.debug("brain.archive", {"persona": persona, "archive_": memory.archive})

    gallery_file = paths.gallery(persona.id)
    gallery_file.parent.mkdir(parents=True, exist_ok=True)
    home_str = str(paths.home(persona.id))

    for batch in memory.archive:
        messages = [m for m in batch if m.prompt]

        for i, m in enumerate(messages):
            if m.prompt.role != "assistant" or not isinstance(m.prompt.content, str):
                continue
            try:
                call = to_dict(m.prompt.content)
            except (ValueError, TypeError):
                continue
            tool_name = call.get("tool")
            if tool_name not in ("vision", "look_at"):
                continue

            source = call.get("source", "")
            if not source:
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
                "question": call.get("question", ""),
                "answer": answer,
                "time": datetimes.iso_8601(datetimes.now()),
            })

        for m in batch:
            if not m.media:
                continue
            if not isinstance(m.prompt.content, list):
                continue

            prompts = [
                {"role": msg.prompt.role, "content": msg.prompt.content}
                for msg in batch if msg.prompt
            ]
            question = (
                "You saw this image during a conversation. "
                "What did you see in it that was relevant to the conversation and helped you?\n\n"
                "## Output\n\n"
                "```json\n"
                "{\"description\": \"<what you saw and why it mattered>\"}\n"
                "```"
            )
            try:
                result = await models.chat_json(persona.thinking, identity, prompts, question)
                description = str(result.get("description", "")).strip() if isinstance(result, dict) else ""
            except ModelError as e:
                logger.warning("brain.archive description failed", {"persona": persona, "source": m.media.source, "error": str(e)})
                description = ""

            if not description:
                continue

            relative_source = m.media.source
            if relative_source.startswith(home_str):
                relative_source = relative_source[len(home_str):].lstrip("/")
            paths.append_jsonl(gallery_file, {
                "source": relative_source,
                "question": "",
                "answer": description,
                "time": datetimes.iso_8601(datetimes.now()),
            })

    return True
