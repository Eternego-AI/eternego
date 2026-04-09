"""Models — generate fine-tuning training pairs from persona DNA."""

import json

from application.core.data import Model
from application.core.exceptions import ModelError, EngineConnectionError
from application.platform import logger, ollama, anthropic, openai, strings
import config.inference as cfg

from .is_local import is_local


async def generate_training_set(model: Model, dna: str) -> list[dict]:
    """Generate fine-tuning training pairs from persona DNA."""
    logger.info("models.generate_training_set", {"model": model.name})
    prompt = (
        "# Training Data Generation\n\n"
        "You are generating fine-tuning examples that teach a language model to be a specific person's personal AI —\n"
        "to converse, reason, and respond in the way that person would expect from someone who truly knows them.\n\n"
        "## Person Profile\n\n"
        f"{dna}\n\n"
        "**Bolded** patterns are recurring and core to this person's identity — weight these most heavily.\n\n"
        "## What to Generate\n\n"
        "Each pair must teach one of the following:\n\n"
        "- **Conversational style** — tone, word choice, pacing, level of formality, use of humour or warmth\n"
        "- **Response patterns** — how to handle requests, pushback, uncertainty, or emotionally loaded moments\n"
        "- **Decision-making** — how to reason and recommend based on this person's known preferences and values\n"
        "- **Relational attunement** — how to bring in what is known about the person naturally, without being mechanical or intrusive\n\n"
        "## What NOT to Generate\n\n"
        "Do not generate pairs involving any of the following — these are handled by the runtime system, not the model:\n\n"
        "- Permission requests, permission grants, or asking before acting\n"
        "- System commands, shell operations, or software installation\n"
        "- Scheduling, calendar entries, or reminder creation\n"
        "- Any invocation of tools or abilities\n"
        "- Generic AI assistant scenarios that could apply to any person\n\n"
        "## Rules\n\n"
        "- Every pair must trace directly to something specific in the profile. A pair that could belong to any persona is useless.\n"
        "- Train the natural default, not the correction. If the person values brevity, responses are brief — not \"I'll keep this short.\"\n"
        "- Write genuine exchanges, not demonstrations. These should feel like real conversations, not constructed examples.\n"
        "- A single pair may combine multiple traits when they arise naturally together.\n"
        "- The \"system\" field should state what the persona knows about this person that shapes the response — not generic capability claims.\n"
        "- Fewer high-quality pairs beat many generic ones. Aim for 500 maximum.\n\n"
        "## Privacy\n\n"
        "- Never use real names, addresses, phone numbers, emails, or other identifiable information.\n"
        "- Use placeholders: \"my person\", \"their project\", \"a colleague\", \"the team\".\n"
        "- Teach patterns, not personal facts.\n\n"
        "## Output\n\n"
        "Return ONLY valid JSON:\n\n"
        "{\n"
        '  "training_pairs": [\n'
        "    {\n"
        '      "trait_source": "the DNA trait this pair teaches",\n'
        '      "system": "You are this person\'s personal AI. You know they...",\n'
        '      "user": "...",\n'
        '      "assistant": "..."\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    if is_local(model):
        try:
            body = {"model": model.name, "prompt": prompt, "stream": False, "format": "json"}
            response = await ollama.post(model.url, "/api/generate", body)
            response_text = response["response"].strip()
        except ollama.OllamaError as e:
            raise ModelError(f"Model returned an error: {e}") from e
        except ConnectionError as e:
            raise EngineConnectionError("Could not connect to the local inference engine") from e
        except KeyError as e:
            raise EngineConnectionError("Model returned an invalid response") from e
    else:
        api_key = (model.credentials or {}).get("api_key", "")
        try:
            if model.provider == "anthropic":
                response_text = await anthropic.async_chat(model.url, api_key, model.name, [{"role": "user", "content": prompt}])
            else:
                response_text = await openai.async_chat(model.url, api_key, model.name, [{"role": "user", "content": prompt}])
        except OSError as e:
            raise ModelError(f"Model returned an error: {e}") from e

    try:
        parsed = strings.extract_json(response_text)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed.get("training_pairs", [])
