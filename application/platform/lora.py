"""LoRA — fine-tuning via HuggingFace peft/trl and GGUF adapter export for Ollama.

Dependencies (install before fine-tuning):
  pip install torch transformers peft trl datasets accelerate
  pip install bitsandbytes          # CUDA only — enables 4-bit QLoRA

The pipeline:
  1. Load the HuggingFace base model (4-bit on CUDA, bf16 on CPU/MPS)
  2. Attach a LoRA adapter and fine-tune with SFTTrainer
  3. Save only the adapter weights (~100–300 MB) — no merge, no memory spike
  4. Convert the adapter to GGUF via convert_lora_to_gguf.py (config files only, no weights reload)
  5. Caller registers it with Ollama as FROM <base> + ADAPTER <gguf>
"""

import os

from application.platform import hugging_face
from config.finetune import (
    LORA_R, LORA_ALPHA, LORA_DROPOUT, LORA_TARGET_MODULES,
    FINETUNE_MAX_LENGTH, FINETUNE_BATCH_SIZE, FINETUNE_GRAD_ACCUM,
    FINETUNE_EPOCHS, FINETUNE_LEARNING_RATE, FINETUNE_GRADIENT_CHECKPOINTING,
)

CHATML_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n{assistant}<|im_end|>"
)


def train(hf_model_id: str, training_pairs: list[dict], output_gguf: str, save_adapter_to: str) -> None:
    """Fine-tune hf_model_id on training_pairs and write a GGUF adapter to output_gguf.

    hf_model_id is always the HuggingFace base model ID (e.g. "Qwen/Qwen2.5-7B-Instruct").
    HuggingFace's cache handles re-use across nights — no persistent copy needed.

    save_adapter_to is a permanent directory where the PEFT adapter weights are saved
    (~100–300 MB). The GGUF at output_gguf is temporary — caller deletes it after
    registering with Ollama.

    No merge step — peak memory stays at model load size throughout:
      CUDA  — 4-bit QLoRA via bitsandbytes (most NVIDIA GPUs with ≥8 GB VRAM)
      MPS   — bf16, full weights (Apple Silicon, ≤14 GB for 7B)
      CPU   — bf16, full weights (≤14 GB for 7B — no 30 GB merge spike)
    """
    import tempfile

    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTTrainer, SFTConfig

    # ── Device selection ─────────────────────────────────────────────────────
    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    use_4bit = device == "cuda"
    # bfloat16 on CPU halves weight memory (28 GB → 14 GB for a 7B model)
    # compared to float32; bfloat16 has better range than float16 for training.
    torch_dtype = torch.float16 if device == "cuda" else torch.bfloat16

    # ── Load tokeniser ────────────────────────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(hf_model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Load model ────────────────────────────────────────────────────────────
    model_kwargs: dict = {"dtype": torch_dtype}
    if use_4bit:
        from transformers import BitsAndBytesConfig
        try:
            import bitsandbytes  # noqa: F401 — presence check
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )
        except ImportError:
            use_4bit = False
            model_kwargs.pop("quantization_config", None)
            model_kwargs["device_map"] = device
    else:
        model_kwargs["device_map"] = device

    model = AutoModelForCausalLM.from_pretrained(hf_model_id, **model_kwargs)

    # ── Attach LoRA adapter ───────────────────────────────────────────────────
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES,
    )
    model = get_peft_model(model, lora_config)

    # ── Build dataset ─────────────────────────────────────────────────────────
    texts = [
        CHATML_TEMPLATE.format(
            system=p.get("system", ""),
            user=p.get("user", ""),
            assistant=p.get("assistant", ""),
        )
        for p in training_pairs
    ]
    dataset = Dataset.from_dict({"text": texts})

    # ── Train ─────────────────────────────────────────────────────────────────
    import gc
    from pathlib import Path

    Path(save_adapter_to).mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            args=SFTConfig(
                output_dir=tmp_dir,
                dataset_text_field="text",
                max_length=FINETUNE_MAX_LENGTH,
                per_device_train_batch_size=FINETUNE_BATCH_SIZE,
                gradient_accumulation_steps=FINETUNE_GRAD_ACCUM,
                num_train_epochs=FINETUNE_EPOCHS,
                learning_rate=FINETUNE_LEARNING_RATE,
                fp16=(device == "cuda"),
                bf16=False,
                use_cpu=(device == "cpu"),
                gradient_checkpointing=FINETUNE_GRADIENT_CHECKPOINTING,
                logging_steps=10,
                save_strategy="no",
                report_to="none",
            ),
        )
        trainer.train()
        del trainer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ── Save adapter only (no merge) ──────────────────────────────────────
        # Saves adapter_config.json + adapter_model.safetensors (~100–300 MB).
        # Base model weights are not written — no memory spike.
        model.save_pretrained(save_adapter_to)
        tokenizer.save_pretrained(save_adapter_to)
        del model
        gc.collect()

        # ── Convert adapter to GGUF ───────────────────────────────────────────
        # Resolve the base model config from HF cache (config files only, no weights).
        try:
            from huggingface_hub import snapshot_download
            base_config_path = snapshot_download(hf_model_id, local_files_only=True)
        except Exception:
            base_config_path = None  # script will fetch config from HF hub
        hugging_face.convert_adapter_to_gguf(save_adapter_to, output_gguf, base_config_path)
