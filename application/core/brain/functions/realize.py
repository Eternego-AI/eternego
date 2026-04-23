"""Brain — realize stage.

Processes unresolved messages in memory — gives them prompts so the thinking
model can see them.

Text messages get a simple string prompt. Image messages take one of two paths:

- **Vision model configured**: pass the image alongside the conversation to
  the thinking model to formulate questions, call the vision model, and add
  the result as a vision tool-call + TOOL_RESULT pair. The original message
  gets the caption as its prompt. No image data persisted in memory.

- **No vision model**: encode the image as base64 content blocks directly in
  the prompt. The thinking model sees the image inline in subsequent stages.
"""

from pathlib import Path

from application.core import models
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Prompt
from application.core.exceptions import ModelError
from application.platform import filesystem, logger
from application.platform.objects import to_string


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

        image_data = filesystem.read_base64(image_path)
        media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        image_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
        ]
        if m.media.caption:
            image_content.append({"type": "text", "text": m.media.caption})

        if not persona.vision:
            m.prompt = Prompt(role="user", content=image_content)
            continue

        m.prompt = Prompt(role="user", content=m.media.caption or "")
        image_message = {"role": "user", "content": image_content}
        reality = memory.prompts + [image_message]
        question_prompt = (
            "The persona just received an image. A vision model will look at it next. "
            "Based on the conversation, what observable things in the image would best "
            "serve the persona? Produce questions that can be answered by looking at "
            "the image itself.\n\n"
            "## Output\n\n"
            "```json\n"
            "{\"questions\": [\"<question>\", \"<question>\"]}\n"
            "```"
        )
        try:
            question_result = await models.chat_json(persona.thinking, identity, reality, question_prompt)
            questions = question_result.get("questions", []) if isinstance(question_result, dict) else []
        except ModelError as formulation_error:
            logger.warning("brain.realize question formulation failed, defaulting", {"persona": persona, "error": str(formulation_error)})
            questions = []
        if questions:
            question = "\n".join(f"- {q}" for q in questions)
        else:
            question = "Describe what you see."

        vision_call = to_string({"tool": "vision", "question": question, "source": m.media.source})
        answer = await models.vision(persona.vision, "", image_path, question)

        memory.remember(Message(
            content=vision_call,
            prompt=Prompt(role="assistant", content=vision_call),
        ))
        result_text = f"TOOL_RESULT\ntool: vision\nstatus: ok\nresult: {answer}"
        memory.remember(Message(
            content=result_text,
            prompt=Prompt(role="user", content=result_text),
        ))


    return bool(memory.messages)
