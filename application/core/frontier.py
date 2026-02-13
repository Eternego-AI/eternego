"""Frontier — escalation to a more powerful external model."""

from collections.abc import AsyncIterator
from urllib.error import URLError

from application.platform import logger, anthropic, openai
from application.core import prompts
from application.core.data import Model, Persona, Thinking, Thought
from application.core import agent
from application.core.exceptions import FrontierError


async def allow_escalation(persona: Persona) -> None:
    """Enable escalation to the frontier model for this persona."""
    logger.info("Allowing escalation", {"persona_id": persona.id, "frontier": persona.frontier.name})
    await agent.add_instruction(persona, "escalation", prompts.ESCALATION)


def consulting(model: Model, prompt: str) -> Thinking:
    """Consult a frontier model about a prompt."""
    logger.info("Consulting", {"model": model.name, "provider": model.provider})

    async def _reason() -> AsyncIterator[Thought]:
        messages = [{"role": "user", "content": prompt}]
        api_key = (model.credentials or {}).get("api_key", "")

        try:
            if model.provider == "anthropic":
                raw_stream = anthropic.stream(api_key, model.name, messages)
            elif model.provider == "openai":
                raw_stream = openai.stream(api_key, model.name, messages)
            else:
                raise FrontierError(f"Unsupported frontier provider: {model.provider}")

            said = ""
            reasoning = False
            for raw in raw_stream:
                content = raw.get("message", {}).get("content", "")
                tool_calls = raw.get("message", {}).get("tool_calls")
                done = raw.get("done", False)

                if tool_calls:
                    yield Thought(intent="doing", content=content, tool_calls=tool_calls)
                elif not done:
                    if "<think>" in content:
                        reasoning = True
                        content = content.replace("<think>", "")
                    if "</think>" in content:
                        reasoning = False
                        content = content.replace("</think>", "")
                        continue

                    if reasoning:
                        yield Thought(intent="reasoning", content=content)
                    else:
                        said += content
                        yield Thought(intent="saying", content=content)

            if said:
                agent.memory().append({"type": "say", "content": said})

        except URLError as e:
            raise FrontierError(f"Could not connect to {model.provider}") from e
        except (KeyError, ValueError) as e:
            raise FrontierError(f"Invalid response from {model.provider}") from e

    return Thinking(_reason)
