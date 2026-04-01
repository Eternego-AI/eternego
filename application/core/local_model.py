"""Local model — communicating with the local model."""

import json

from application.platform import logger, ollama, strings
from application.core.exceptions import EngineConnectionError, ModelError


async def chat(model: str, messages: list[dict]) -> str:
    """Send messages, wait for full response."""
    logger.debug("local_model.chat", {"model": model, "messages": messages})
    try:
        async with ollama.connect() as client:
            response = await ollama.post(client, "/api/chat", {"model": model, "messages": messages, "stream": False})
        content = response["message"]["content"]
        logger.debug("local_model.chat response", {"model": model, "content": content or "(empty)"})
        return content
    except ollama.OllamaError as e:
        raise ModelError(f"Model returned an error: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        logger.warning("local_model.chat invalid response", {"model": model, "response": str(response)})
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_json(model: str, messages: list[dict]) -> dict:
    """Send messages, wait for full JSON response."""
    logger.debug("local_model.chat_json", {"model": model, "messages": messages})
    try:
        async with ollama.connect() as client:
            response = await ollama.post(client, "/api/chat", {"model": model, "messages": messages, "stream": False, "format": "json"})
        logger.debug("local_model.chat_json response", {"model": model, "response": response})
        return strings.extract_json(response["message"]["content"])
    except ollama.OllamaError as e:
        raise ModelError(f"Model returned an error: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (KeyError, json.JSONDecodeError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_json_stream(model: str, messages: list[dict]) -> dict:
    """Stream response, collect and return parsed JSON."""
    logger.debug("local_model.chat_json_stream", {"model": model, "messages": messages})
    try:
        async with ollama.connect() as client:
            body = {"model": model, "messages": messages, "format": "json"}
            parts = []
            async for chunk in ollama.stream(client, "/api/chat", body):
                parts.append(chunk.get("message", {}).get("content", ""))
        logger.debug("local_model.chat_json_stream full response", {"model": model, "response": "".join(parts)})
        return strings.extract_json("".join(parts))
    except ollama.OllamaError as e:
        raise ModelError(f"Model returned an error: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e


async def generate(model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the local model and return the response text."""
    logger.debug("Sending generate request to model", {"model": model, "prompt": prompt, "json_mode": json_mode})
    try:
        body = {"model": model, "prompt": prompt, "stream": False}
        if json_mode:
            body["format"] = "json"
        async with ollama.connect() as client:
            response = await ollama.post(client, "/api/generate", body)
        logger.debug("Received generate response from model", {"model": model, "response": response})
        return response["response"].strip()
    except ollama.OllamaError as e:
        raise ModelError(f"Model returned an error: {e}") from e
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def generate_json(model: str, prompt: str) -> dict:
    """Send a prompt to the local model and return the parsed JSON response."""
    logger.debug("Sending JSON generate request to model", {"model": model, "prompt": prompt})
    response = await generate(model, prompt, json_mode=True)
    try:
        response = strings.extract_json(response)
        logger.debug("Parsed JSON from model response", {"model": model, "response": response})
        return response
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e


async def generate_training_set(model: str, dna: str) -> list[dict]:
    """Generate fine-tuning training pairs from persona DNA."""
    logger.info("local_model.generate_training_set", {"model": model})
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
    response = await generate(model, prompt, json_mode=True)
    try:
        parsed = strings.extract_json(response)
    except json.JSONDecodeError:
        return []
    return parsed.get("training_pairs", [])
