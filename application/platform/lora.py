"""LoRA — fine-tuning and training data formatting using Unsloth."""

import json


CHATML_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n{assistant}<|im_end|>"
)


def format(training_pairs: list[dict]) -> list[str]:
    """Convert neutral training pairs to LoRA-compatible formatted strings."""
    return [
        CHATML_TEMPLATE.format(
            system=pair.get("system", ""),
            user=pair.get("user", ""),
            assistant=pair.get("assistant", ""),
        )
        for pair in training_pairs
    ]


def train(base_model: str, dataset_path: str, output_dir: str) -> str:
    """Run LoRA fine-tuning on a base model with the given dataset."""
    from datasets import Dataset
    from transformers import TrainingArguments
    from trl import SFTTrainer
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=16,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
    )

    with open(dataset_path) as f:
        texts = json.load(f)
    dataset = Dataset.from_dict({"text": texts})

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            num_train_epochs=3,
            learning_rate=2e-4,
            output_dir=output_dir,
        ),
    )
    trainer.train()

    model.save_pretrained(output_dir)
    return output_dir
