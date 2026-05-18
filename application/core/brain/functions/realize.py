"""Brain — realize over living.

Surveys what just landed in memory and brings it in. Text messages get a
simple string prompt. Image messages always become text here: realize is
the only place that calls the eye.

The flow per media message:
- If the media already carries a question (set by `take_screenshot`,
  `screen`, `look_at`, or `locate`), use it directly — the producer
  already knew what to ask.
- Otherwise (an image the person sent in from outside), the consultant
  formulates questions text-only — it doesn't see the image, just the
  conversation around it.

Either path ends with the eye answering, which becomes a `tools.vision`
tool-call + TOOL_RESULT pair in memory. The original message's prompt
is just the caption — no image data ever sits inside the message's own
prompt, so recognize / decide / reflect / archive only ever process
text. The image rides in its own Prompt that we hand to chat alongside
the eye's identity; chat translates the canonical image block into each
provider's shape.

If the persona has a dedicated vision model, that's the eye. Otherwise
the thinking model stands in. Either way, the eye's identity (system
prompt) flows in through chat's system-message handling, so the eye
reports facts in its character's framing.

Realize is the entry point of every tick — what the persona perceives
from outside (person words, images, system notifications) becomes part
of its inner conversation here.
"""

from pathlib import Path

from application.core import models
from application.core.brain.signals import Tick, Tock
from application.core.data import Action
from application.core.data import Prompt
from application.core.exceptions import ModelError
from application.platform import filesystem, logger
from application.platform.observer import dispatch


CONSULTING = Action(
    name="consulting",
    description="Questions the consultant would ask to see this moment more clearly.",
    fields=[
        Action(
            name="questions",
            type="array",
            required=True,
            items=Action(name="question", type="string"),
        ),
    ],
)


async def realize(memory, ego, eye, consultant) -> list:
    """realize OVER living — survey what just landed, take it in."""
    dispatch(Tick("realize", {"persona": ego.persona}))

    for m in memory.messages:
        if m.prompt is not None:
            continue

        if not m.media:
            m.prompt = Prompt(role="user", content=m.content)
            continue

        image_path = Path(m.media.source)
        if not image_path.exists():
            m.prompt = Prompt(role="user", content=m.media.caption or "")
            memory.add_tool_result(
                "tools.vision",
                {"source": m.media.source},
                "error",
                f"image not found at {m.media.source}",
            )
            continue

        # If the producer of this media already knows what to ask, use it.
        # Otherwise the consultant formulates questions — text-only, the
        # consultant never sees the image itself.
        if m.media.question:
            question = m.media.question
        else:
            question_prompt = (
                f"The persona {ego.persona.name} just received an image. A vision model "
                "will look at it next. Based on the conversation, what observable things in the "
                "image would best serve the persona? Produce questions that can be answered by "
                "looking at the image itself.\n\n"
                "## Output\n\n"
                "```json\n"
                "{\"questions\": [\"<question>\", \"<question>\"]}\n"
                "```"
            )
            try:
                question_result = await models.tool(consultant.model, consultant.identity + memory.prompts, question_prompt, CONSULTING)
                questions = question_result.get("questions", []) if isinstance(question_result, dict) else []
            except ModelError as formulation_error:
                logger.warning("brain.realize question formulation failed, defaulting", {"persona": ego.persona, "error": str(formulation_error)})
                questions = []
            if questions:
                question = "\n".join(f"- {q}" for q in questions)
            else:
                question = "Describe what you see."

        m.prompt = Prompt(role="user", content=m.media.caption or "")

        # Build the image-bearing user prompt in the Anthropic-canonical
        # block shape — chat translates it per provider. The eye sees the
        # persona's identity (system messages) then the image, and answers
        # the appended question.
        image_data = filesystem.read_base64(image_path)
        media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        image_prompt = Prompt(role="user", content=[
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
        ])

        # Use the dedicated vision model when configured; otherwise the
        # thinking model stands in.
        eye_model = eye.model or ego.model
        try:
            answer = await models.chat(eye_model, eye.identity + [image_prompt], question)
            memory.add_tool_result(
                "tools.vision",
                {"question": question, "source": m.media.source},
                "ok",
                answer,
            )
        except ModelError as vision_error:
            logger.warning("brain.realize eye failed", {"persona": ego.persona, "error": str(vision_error)})
            memory.add_tool_result(
                "tools.vision",
                {"question": question, "source": m.media.source},
                "error",
                str(vision_error),
            )

    dispatch(Tock("realize", {"persona": ego.persona}))
    return []
