"""Brain — realize stage.

When an image arrives in memory, realize processes it by formulating
vision questions (via thinking model, observer identity) and calling the
vision model with the image. The resulting observation lands in memory as
a synthetic assistant+TOOL_RESULT pair — as if the persona itself had
called a `vision` tool. Subsequent stages see a normal tool-call sequence.
"""

import base64
import json
from pathlib import Path

from application.core import models, paths
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Prompt
from application.core.exceptions import ModelError
from application.platform import datetimes, logger


async def realize(ego, identity: str, memory: Memory) -> bool:
    persona = ego.persona
    logger.debug("brain.realize", {"persona": persona, "messages": memory.messages})
    for m in memory.messages:
        if m.prompt is not None:
            continue

        if not m.media:
            m.prompt = Prompt(role="user", content=m.content)
            continue

        image_path = Path(m.media.source)
        if not image_path.exists():
            m.prompt = Prompt(role="user", content=m.media.caption or "")
            missing = f"TOOL_RESULT\ntool: vision\nstatus: error\nresult: image not found at {m.media.source}"
            memory.remember(Message(content=missing, prompt=Prompt(role="user", content=missing)))
            continue

        # The caption (if any) becomes the person-role user message attached to the image.
        m.prompt = Prompt(role="user", content=m.media.caption or "")

        if m.media.caption and not m.channel:
            question = m.media.caption
        else:
            context = "\n".join(p["content"] for p in memory.prompts)
            question_prompt = (
                "The persona just received an image. A vision model will look at it next. "
                "Based on the conversation, what observable things in the image would best "
                "serve the persona? Produce questions that can be answered by looking at "
                "the image itself.\n\n"
                f"## Conversation\n\n{context}\n\n"
                "## Output\n\n"
                "```json\n"
                "{\"questions\": [\"<question>\", \"<question>\"]}\n"
                "```"
            )
            try:
                question_result = await models.chat_json(persona.thinking, identity, [], question_prompt)
                questions = question_result.get("questions", []) if isinstance(question_result, dict) else []
            except ModelError as formulation_error:
                logger.warning("brain.realize question formulation failed, defaulting", {"persona": persona, "error": str(formulation_error)})
                questions = []
            if questions:
                question = "\n".join(f"- {q}" for q in questions)
            else:
                question = "Describe what you see."

        vision_call = json.dumps({"tool": "vision", "question": question, "source": m.media.source})

        try:
            vision_model = persona.vision or persona.thinking
            image_data = base64.b64encode(image_path.read_bytes()).decode()
            media_type = "image/png" if image_path.suffix == ".png" else "image/jpeg"
            image_reality = [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            ]}]
            answer = await models.chat(vision_model, "", image_reality, question)

            memory.remember(Message(
                content=vision_call,
                prompt=Prompt(role="assistant", content=vision_call),
            ))
            result_text = f"TOOL_RESULT\ntool: vision\nstatus: ok\nresult: {answer}"
            memory.remember(Message(
                content=result_text,
                prompt=Prompt(role="user", content=result_text),
            ))

            gallery_file = paths.media(persona.id) / "gallery.json"
            gallery_file.parent.mkdir(parents=True, exist_ok=True)
            home_str = str(paths.home(persona.id))
            relative_source = m.media.source
            if relative_source.startswith(home_str):
                relative_source = relative_source[len(home_str):].lstrip("/")
            gallery = json.loads(gallery_file.read_text()) if gallery_file.exists() else {}
            if relative_source not in gallery:
                gallery[relative_source] = []
            gallery[relative_source].append({
                "caption": m.media.caption,
                "question": question,
                "answer": answer,
                "time": datetimes.iso_8601(datetimes.now()),
            })
            gallery_file.write_text(json.dumps(gallery, indent=2))

        except (ModelError, OSError, json.JSONDecodeError) as e:
            logger.warning("brain.realize vision failed", {"persona": persona, "error": str(e)})
            memory.remember(Message(
                content=vision_call,
                prompt=Prompt(role="assistant", content=vision_call),
            ))
            error_text = f"TOOL_RESULT\ntool: vision\nstatus: error\nresult: {e}"
            memory.remember(Message(
                content=error_text,
                prompt=Prompt(role="user", content=error_text),
            ))

    return bool(memory.messages)
