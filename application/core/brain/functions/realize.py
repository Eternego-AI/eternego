"""Brain — realize over living.

Surveys what just landed in living.ego.memory and brings it in. Text messages get a
simple string prompt. Image messages take one of two paths:

- **living.eye has a vision model**: the living.consultant formulates questions based on
  the conversation, the living.eye sees the image and answers, and the result
  becomes a vision tool-call + TOOL_RESULT pair in living.ego.memory. The original
  message gets the caption as its prompt. No image data persisted in living.ego.memory.

- **No vision model**: encode the image as base64 content blocks directly
  in the prompt. The thinking model sees the image inline in subsequent
  stages.

Realize is the entry point of every tick — what the living.ego.persona perceives from
outside (person words, images, system notifications) becomes part of its
inner conversation here.
"""

from pathlib import Path

from application.core import models
from application.core.agents import Living
from application.core.brain.signals import Tick, Tock
from application.core.data import Prompt
from application.core.exceptions import ModelError
from application.platform import filesystem, logger
from application.platform.observer import dispatch


async def realize(living: Living) -> list:
    """realize OVER living — survey what just landed, take it in."""
    dispatch(Tick("realize", {"persona": living.ego.persona}))

    for m in living.ego.memory.messages:
        if m.prompt is not None:
            continue

        if not m.media:
            m.prompt = Prompt(role="user", content=m.content)
            continue

        image_path = Path(m.media.source)
        if not image_path.exists():
            m.prompt = Prompt(role="user", content=m.media.caption or "")
            living.ego.memory.add_tool_result(
                "tools.vision",
                {"source": m.media.source},
                "error",
                f"image not found at {m.media.source}",
            )
            continue

        image_data = filesystem.read_base64(image_path)
        media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        image_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
        ]
        if m.media.caption:
            image_content.append({"type": "text", "text": m.media.caption})

        if not living.eye.model:
            m.prompt = Prompt(role="user", content=image_content)
            continue

        m.prompt = Prompt(role="user", content=m.media.caption or "")
        image_prompt = Prompt(role="user", content=image_content)
        reality = living.ego.memory.prompts + [image_prompt]
        question_prompt = (
            "The living.ego.persona just received an image. A vision model will look at it next. "
            "Based on the conversation, what observable things in the image would best "
            "serve the living.ego.persona? Produce questions that can be answered by looking at "
            "the image itself.\n\n"
            "## Output\n\n"
            "```json\n"
            "{\"questions\": [\"<question>\", \"<question>\"]}\n"
            "```"
        )
        try:
            question_result = await models.chat_json(living.consultant.model, living.consultant.identity + reality, question_prompt)
            questions = question_result.get("questions", []) if isinstance(question_result, dict) else []
        except ModelError as formulation_error:
            logger.warning("brain.realize question formulation failed, defaulting", {"persona": living.ego.persona, "error": str(formulation_error)})
            questions = []
        if questions:
            question = "\n".join(f"- {q}" for q in questions)
        else:
            question = "Describe what you see."

        answer = await models.chat(living.eye.model, living.eye.identity + [image_prompt], question)
        living.ego.memory.add_tool_result(
            "tools.vision",
            {"question": question, "source": m.media.source},
            "ok",
            answer,
        )

    dispatch(Tock("realize", {"persona": living.ego.persona}))
    return []
