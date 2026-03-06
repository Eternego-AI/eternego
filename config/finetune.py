"""Fine-tuning config — LoRA and SFT training settings.

Defaults are tuned for a Mac Mini M4 (24 GB unified memory, MPS device).
Override via environment variables in .env to match your machine.

Quick reference:
  Mac Mini M4 24 GB  — defaults below
  Mac Mini M4 16 GB  — FINETUNE_BATCH_SIZE=1, FINETUNE_MAX_LENGTH=512
  CPU-only 24 GB     — FINETUNE_MAX_LENGTH=256, FINETUNE_BATCH_SIZE=1, FINETUNE_GRAD_ACCUM=2
  CUDA 8 GB          — FINETUNE_GRADIENT_CHECKPOINTING=true, FINETUNE_MAX_LENGTH=256, FINETUNE_BATCH_SIZE=1
"""

import os

import config  # ensures .env is loaded

# ── LoRA adapter settings ─────────────────────────────────────────────────────

# Rank of the LoRA decomposition — higher = more capacity, more memory.
LORA_R: int = int(os.environ.get("LORA_R", "8"))

# LoRA scaling factor — typically 2× rank.
LORA_ALPHA: int = int(os.environ.get("LORA_ALPHA", "16"))

# Dropout applied to LoRA layers during training.
LORA_DROPOUT: float = float(os.environ.get("LORA_DROPOUT", "0.05"))

# Comma-separated list of module names to attach LoRA to.
# "q_proj,k_proj,v_proj,o_proj" targets only attention projections (faster, less memory).
# "all-linear" targets every linear layer (slower, more expressive).
_target_env = os.environ.get("LORA_TARGET_MODULES", "q_proj,k_proj,v_proj,o_proj")
LORA_TARGET_MODULES: list[str] | str = (
    "all-linear" if _target_env == "all-linear"
    else [m.strip() for m in _target_env.split(",") if m.strip()]
)

# ── SFT training settings ─────────────────────────────────────────────────────

# Maximum token length per training example — longer sequences cost more memory and time.
FINETUNE_MAX_LENGTH: int = int(os.environ.get("FINETUNE_MAX_LENGTH", "512"))

# Samples per gradient step per device.
FINETUNE_BATCH_SIZE: int = int(os.environ.get("FINETUNE_BATCH_SIZE", "2"))

# Gradient accumulation steps — effective batch = BATCH_SIZE × GRAD_ACCUM.
FINETUNE_GRAD_ACCUM: int = int(os.environ.get("FINETUNE_GRAD_ACCUM", "4"))

# Number of full passes over the training set.
FINETUNE_EPOCHS: int = int(os.environ.get("FINETUNE_EPOCHS", "1"))

# Learning rate for the AdamW optimizer.
FINETUNE_LEARNING_RATE: float = float(os.environ.get("FINETUNE_LEARNING_RATE", "2e-4"))

# Recompute activations during backprop instead of storing them.
# Saves ~4 GB memory at the cost of ~30-40% extra compute.
# Enable on CUDA with limited VRAM; disable when memory is ample.
FINETUNE_GRADIENT_CHECKPOINTING: bool = (
    os.environ.get("FINETUNE_GRADIENT_CHECKPOINTING", "false").lower() == "true"
)
