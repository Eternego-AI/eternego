"""HuggingFace — model ID registry and GGUF conversion."""

import subprocess

from config.application import GGUF_CONVERT_SCRIPT, LORA_CONVERT_SCRIPT

_HF_IDS: dict[str, str] = {
    # Qwen 2.5
    "qwen2.5:0.5b":    "Qwen/Qwen2.5-0.5B-Instruct",
    "qwen2.5:1.5b":    "Qwen/Qwen2.5-1.5B-Instruct",
    "qwen2.5:3b":      "Qwen/Qwen2.5-3B-Instruct",
    "qwen2.5:7b":      "Qwen/Qwen2.5-7B-Instruct",
    "qwen2.5:14b":     "Qwen/Qwen2.5-14B-Instruct",
    "qwen2.5:32b":     "Qwen/Qwen2.5-32B-Instruct",
    "qwen2.5:72b":     "Qwen/Qwen2.5-72B-Instruct",
    # Llama 3.x
    "llama3.2:1b":     "meta-llama/Llama-3.2-1B-Instruct",
    "llama3.2:3b":     "meta-llama/Llama-3.2-3B-Instruct",
    "llama3.1:8b":     "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "llama3.1:70b":    "meta-llama/Meta-Llama-3.1-70B-Instruct",
    "llama3.3:70b":    "meta-llama/Llama-3.3-70B-Instruct",
    # Mistral
    "mistral:7b":      "mistralai/Mistral-7B-Instruct-v0.3",
    "mistral-nemo":    "mistralai/Mistral-Nemo-Instruct-2407",
    # Phi
    "phi4:14b":        "microsoft/phi-4",
    "phi3.5:3.8b":     "microsoft/Phi-3.5-mini-instruct",
    # Gemma 2
    "gemma2:2b":       "google/gemma-2-2b-it",
    "gemma2:9b":       "google/gemma-2-9b-it",
    "gemma2:27b":      "google/gemma-2-27b-it",
    # DeepSeek R1
    "deepseek-r1:7b":  "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "deepseek-r1:14b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "deepseek-r1:32b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "deepseek-r1:70b": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
}


def ids() -> dict[str, str]:
    """Return the full map of Ollama base model names to HuggingFace model IDs."""
    return _HF_IDS


def id_for(model_name: str) -> str | None:
    """Return the HuggingFace model ID for a given Ollama model name, or None if unknown.

    Strips quantization suffixes so that qwen2.5:7b-q4_k_m resolves the same
    as qwen2.5:7b.
    """
    if model_name in _HF_IDS:
        return _HF_IDS[model_name]
    if "-" in model_name:
        base = model_name.rsplit("-", 1)[0]
        if base in _HF_IDS:
            return _HF_IDS[base]
    return None


def convert_to_gguf(model_dir: str, output_gguf: str) -> None:
    """Convert a merged HuggingFace model directory to a Q4_K_M GGUF file."""
    result = subprocess.run(
        ["python3", GGUF_CONVERT_SCRIPT, model_dir, "--outtype", "q4_k_m", "--outfile", output_gguf],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"GGUF conversion failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )


def convert_adapter_to_gguf(adapter_dir: str, output_gguf: str, base_model_path: str | None = None) -> None:
    """Convert a PEFT LoRA adapter directory to a GGUF adapter file.

    base_model_path is a local directory with the base model config files (config.json,
    tokenizer.json). If omitted, the script resolves the base model from the adapter
    config and downloads only the config from HuggingFace — no model weights needed.
    """
    cmd = ["python3", LORA_CONVERT_SCRIPT, adapter_dir, "--outfile", output_gguf, "--outtype", "f16"]
    if base_model_path:
        cmd.extend(["--base", base_model_path])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"LoRA adapter conversion failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )
