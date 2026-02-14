"""Models — model naming and identification."""

from application.platform import datetimes


def generate_name(base_model: str, persona_id: str) -> str:
    """Generate a timestamped model name for a persona."""
    return f"{base_model}-{persona_id}-{datetimes.stamp(datetimes.now())}"
