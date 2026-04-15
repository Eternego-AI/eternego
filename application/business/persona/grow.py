"""Persona — generating training pairs and fine-tuning."""

import json

from dataclasses import dataclass

from application.business.outcome import Outcome
from application.core import bus, local_inference_engine, models, paths
from application.core.data import Persona
from application.core.exceptions import DNAError, EngineConnectionError
from application.platform import OS, hugging_face


@dataclass
class GrowData:
    dna: bool
    finetune: bool


async def grow(persona: Persona) -> Outcome[GrowData]:
    """Generate training pairs from existing DNA and fine-tune the persona's model."""
    await bus.propose("Growing", {"persona": persona})
    try:
        if not models.is_local(persona.thinking):
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="Fine-tuning skipped — not a local model.", data=GrowData(dna=False, finetune=False))

        dna = paths.read(paths.dna(persona.id))
        if not dna:
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="No DNA to grow from.", data=GrowData(dna=False, finetune=False))

        if persona.frontier:
            try:
                all_pairs = await models.generate_training_set(persona.frontier, dna)
            except Exception:
                all_pairs = await models.generate_training_set(persona.thinking, dna)
        else:
            all_pairs = await models.generate_training_set(persona.thinking, dna)

        training_set = json.dumps({"training_pairs": all_pairs}, indent=2)
        paths.add_training_set(persona.id, training_set)

        hf_model_id = hugging_face.id_for(persona.base_model)
        if hf_model_id is None:
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=False, message=f"'{persona.base_model}' is not supported for fine-tuning.", data=GrowData(dna=True, finetune=False))

        vram = OS.gpu_vram_gb()
        if vram is None:
            await bus.broadcast("Grown", {"persona": persona})
            return Outcome(success=True, message="Fine-tuning skipped — no GPU detected.", data=GrowData(dna=True, finetune=False))

        await local_inference_engine.fine_tune(hf_model_id, training_set, persona.thinking.url, persona.base_model, persona.thinking.name, persona.id)

        if not await local_inference_engine.check(persona.thinking.url, persona.thinking.name):
            raise DNAError("Fine-tuned model failed verification — previous model is still active")

        await bus.broadcast("Grown", {"persona": persona})
        return Outcome(success=True, message="Grow complete.")

    except (DNAError, EngineConnectionError) as e:
        await bus.broadcast("Grow failed", {"reason": "fine_tune", "persona": persona, "error": str(e)})
        return Outcome(success=False, message=str(e))
