"""Local model — communicating with the local model."""

import json

from application.platform import logger, ollama, strings, OS
from application.core.exceptions import EngineConnectionError


async def chat(model: str, messages: list[dict]) -> str:
    """Send messages, wait for full response."""
    logger.info("local_model.chat", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages
        response = await ollama.post("/api/chat", {"model": model, "messages": messages, "stream": False})
        return response["message"]["content"]
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_json(model: str, messages: list[dict]) -> dict:
    """Send messages, wait for full JSON response."""
    logger.info("local_model.chat_json", {"model": model})
    try:
        current_os = OS.get_supported()
        if current_os:
            messages = [{"role": "system", "content": f"When running tools, commands must be for {current_os}."}] + messages
        response = await ollama.post("/api/chat", {"model": model, "messages": messages, "stream": False, "format": "json"})
        return strings.extract_json(response["message"]["content"])
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except (KeyError, json.JSONDecodeError) as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def chat_stream(model: str, messages: list[dict]):
    """Stream response, yielding one token at a time."""
    logger.info("local_model.chat_stream", {"model": model})
    try:
        async for chunk in ollama.stream_post("/api/chat", {"model": model, "messages": messages}):
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e


async def chat_json_stream(model: str, messages: list[dict]) -> dict:
    """Stream response, collect and return parsed JSON."""
    logger.info("local_model.chat_json_stream", {"model": model})
    try:
        body = {"model": model, "messages": messages, "format": "json"}
        parts = []
        async for chunk in ollama.stream_post("/api/chat", body):
            parts.append(chunk.get("message", {}).get("content", ""))
        return strings.extract_json("".join(parts))
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except json.JSONDecodeError as e:
        raise EngineConnectionError("Model returned an invalid JSON response") from e


async def chat_stream_paragraph(model: str, messages: list[dict]):
    """Stream response, yielding one complete paragraph at a time.

    Paragraphs are separated by blank lines (double newline).
    """
    logger.info("local_model.chat_stream_paragraph", {"model": model})
    buffer = ""
    async for token in chat_stream(model, messages):
        buffer += token
        while "\n\n" in buffer:
            paragraph, buffer = buffer.split("\n\n", 1)
            if paragraph.strip():
                yield paragraph.strip()
    if buffer.strip():
        yield buffer.strip()


async def generate(model: str, prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the local model and return the response text."""
    logger.info("Sending generate request to model", {"model": model, "prompt": prompt})
    try:
        body = {"model": model, "prompt": prompt, "stream": False}
        if json_mode:
            body["format"] = "json"
        response = await ollama.post("/api/generate", body)
        return response["response"].strip()
    except ConnectionError as e:
        raise EngineConnectionError("Could not connect to the local inference engine") from e
    except KeyError as e:
        raise EngineConnectionError("Model returned an invalid response") from e


async def generate_json(model: str, prompt: str) -> dict:
    """Send a prompt to the local model and return the parsed JSON response."""
    logger.info("Sending JSON generate request to model", {"model": model, "prompt": prompt})
    response = await generate(model, prompt, json_mode=True)
    try:
        return strings.extract_json(response)
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


async def generate_recovery_phrase(model: str) -> str:
    prompt = """Generate a recovery phrase consisting of exactly 24 random English words.

Requirements:
- Use 24 common, distinct English words
- Each word from a standard BIP-39 wordlist or similar well-known word list
- All lowercase
- Words must not form a meaningful sentence or phrase
- No repeated words

Return ONLY the 24 words separated by spaces. No other text."""

    return await generate(model, prompt)