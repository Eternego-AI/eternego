"""Persona — generating training pairs and fine-tuning."""

import json

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, models, paths
from application.core.brain import character
from application.core.data import Persona
from application.core.exceptions import EngineConnectionError
from application.platform import OS, hugging_face


@dataclass
class GrowData:
    trained: bool
    finetune: bool


async def grow(persona: Persona) -> Outcome[GrowData]:
    """Generate training pairs from persona traits and fine-tune the persona's model."""
    bus.propose("Growing", {"persona": persona})
    try:
        if not models.is_local(persona.thinking):
            bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="Fine-tuning skipped — not a local model.", data=GrowData(trained=False, finetune=False))

        traits = paths.read(paths.persona_trait(persona.id)).strip()
        if not traits:
            bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="No traits to grow from.", data=GrowData(trained=False, finetune=False))

        persona_character = character.shape(persona)
        if persona.frontier:
            try:
                all_pairs = await models.generate_training_set(persona.frontier, persona_character, traits)
            except Exception:
                all_pairs = await models.generate_training_set(persona.thinking, persona_character, traits)
        else:
            all_pairs = await models.generate_training_set(persona.thinking, persona_character, traits)

        training_set = json.dumps({"training_pairs": all_pairs}, indent=2)
        paths.add_training_set(persona.id, training_set)

        hf_model_id = hugging_face.id_for(persona.base_model)
        if hf_model_id is None:
            bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=False, message=f"'{persona.base_model}' is not supported for fine-tuning.", data=GrowData(trained=True, finetune=False))

        vram = OS.gpu_vram_gb()
        if vram is None:
            bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="Fine-tuning skipped — no GPU detected.", data=GrowData(trained=True, finetune=False))

        await local_inference_engine.fine_tune(hf_model_id, training_set, persona.thinking.url, persona.base_model, persona.thinking.name, persona.id)

        if not await local_inference_engine.check(persona.thinking.url, persona.thinking.name):
            raise EngineConnectionError("Fine-tuned model failed verification — previous model is still active")

        bus.broadcast("Grown", {"persona": persona})
        return Outcome(success=True, message="Grow complete.")

    except EngineConnectionError as e:
        bus.broadcast("Grow failed", {"reason": "fine_tune", "persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
