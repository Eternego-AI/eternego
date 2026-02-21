"""Paths — application directory layout."""

from pathlib import Path


def agents_home() -> Path:
    """Root directory for all persona storage."""
    return Path.home() / ".eternego" / "personas"


def agent_identity(agent_id: str) -> Path:
    """Path to the config.json file for that agent."""
    return agents_home() / agent_id / "config.json"


def struggles(agent_id: str) -> Path:
    """Path to the person-struggles.md file for that agent."""
    return agents_home() / agent_id / "person-struggles.md"


def memory(agent_id: str) -> Path:
    """Path to the memory.json file for that agent."""
    return agents_home() / agent_id / "memory.json"
