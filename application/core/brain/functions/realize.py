"""Brain — realize stage."""

import base64
import json
from pathlib import Path

from application.core import models, paths
from application.core.brain.mind.memory import Memory
from application.core.data import Message, Persona, Prompt
from application.core.exceptions import EngineConnectionError, ModelError
from application.platform import datetimes, logger


async def realize(persona: Persona, identity: str, memory: Memory) -> bool:
    logger.debug("brain.realize", {"persona": persona, "messages": memory.messages})
    for m in memory.messages:
        if m.prompt is not None:
            continue

        if not m.media:
            m.prompt = Prompt(role="user", content=m.content)
            continue

        image_path = Path(m.media.source)
        if not image_path.exists():
            m.prompt = Prompt(role="user", content=f"An image was expected at {m.media.source} but the file was not found.")
            continue

        if m.media.caption:
            memory.remember(Message(
                content=m.media.caption,
                prompt=Prompt(role="user", content=f"The person said: {m.media.caption}"),
            ))

        try:
            if m.media.caption and not m.channel:
                question = m.media.caption
            else:
                context = "\n".join(p["content"] for p in memory.prompts)
                question_prompt = (
                    "You received an image. A vision model will describe what is in it. "
                    "What should the vision model look for, considering the conversation?\n\n"
                    f"Conversation:\n{context}\n\n"
                    "```json\n"
                    "{\"questions\": [\"<question>\", \"<question>\"]}\n"
                    "```"
                )
                question_result = await models.chat_json(persona.thinking, identity, [], question_prompt)
                questions = question_result.get("questions", []) if isinstance(question_result, dict) else []
                if questions:
                    question = "\n".join(f"- {q}" for q in questions)
                else:
                    question = "Describe what you see."

            vision_model = persona.vision or persona.thinking
            image_data = base64.b64encode(image_path.read_bytes()).decode()
            media_type = "image/png" if image_path.suffix == ".png" else "image/jpeg"
            image_reality = [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            ]}]
            answer = await models.chat(vision_model, "", image_reality, question)

            m.prompt = Prompt(
                role="user",
                content=f"[vision] You received an image at {m.media.source}. You looked for: {question} You saw: {answer}",
            )

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
            m.prompt = Prompt(role="user", content=m.content or "An image was received but could not be processed.")

    return bool(memory.messages)
