"""Models — model naming and identification."""

from application.core.data import Model
from application.platform import datetimes


def generate(base_model: str, persona_id: str) -> Model:
    """Generate a timestamped model name for a persona."""
    name = f"{base_model}-{persona_id}-{datetimes.stamp(datetimes.now())}"
    return Model(name=name)
