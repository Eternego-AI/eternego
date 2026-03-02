"""LoRA — fine-tuning via HuggingFace peft/trl and GGUF export for Ollama.

Dependencies (install before fine-tuning):
  pip install torch transformers peft trl datasets accelerate
  pip install bitsandbytes          # CUDA only — enables 4-bit QLoRA

The pipeline:
  1. Load the HuggingFace base model (4-bit on CUDA, fp16 on MPS, fp32 on CPU)
  2. Attach a LoRA adapter and fine-tune with SFTTrainer
  3. Merge the adapter back into the base weights
  4. Convert the merged model to GGUF (Q4_K_M) via convert_hf_to_gguf.py
  5. Return the path to the GGUF file — caller registers it with Ollama
"""

import os

from application.platform import hugging_face

CHATML_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n{assistant}<|im_end|>"
)


def train(hf_model_id: str, training_pairs: list[dict], output_gguf: str) -> None:
    """Fine-tune hf_model_id on training_pairs and write a GGUF to output_gguf.

    Automatically selects the best available device:
      CUDA  — 4-bit QLoRA via bitsandbytes (most NVIDIA GPUs with ≥8 GB VRAM)
      MPS   — fp16, full weights (Apple Silicon with ≥32 GB unified memory)
      CPU   — fp32, full weights (very slow, last resort)
    """
    import tempfile

    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from trl import SFTTrainer

    # ── Device selection ─────────────────────────────────────────────────────
    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    use_4bit = device == "cuda"
    torch_dtype = torch.float32 if device == "cpu" else torch.float16

    # ── Load tokeniser ────────────────────────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(hf_model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Load model ────────────────────────────────────────────────────────────
    model_kwargs: dict = {"torch_dtype": torch_dtype}
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
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules="all-linear",
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
    with tempfile.TemporaryDirectory() as tmp_dir:
        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            dataset_text_field="text",
            args=TrainingArguments(
                output_dir=tmp_dir,
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                num_train_epochs=3,
                learning_rate=2e-4,
                fp16=(device == "cuda"),
                bf16=False,
                logging_steps=10,
                save_strategy="no",
                report_to="none",
            ),
        )
        trainer.train()

        # ── Merge adapter into base weights ───────────────────────────────────
        merged = model.merge_and_unload()
        merged_dir = os.path.join(tmp_dir, "merged")
        merged.save_pretrained(merged_dir, safe_serialization=True)
        tokenizer.save_pretrained(merged_dir)

        # ── Convert to GGUF ───────────────────────────────────────────────────
        hugging_face.convert_to_gguf(merged_dir, output_gguf)
