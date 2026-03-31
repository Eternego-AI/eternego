#!/usr/bin/env bash
# Download GGUF conversion scripts from llama.cpp.
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

print "Downloading GGUF tools... estimation 1 minute"
mkdir -p "$SCRIPT_DIR/tools"

if ! curl -fsSL \
    "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_hf_to_gguf.py" \
    -o "$SCRIPT_DIR/tools/convert_hf_to_gguf.py" >> "$LOG_FILE" 2>&1; then
    print "Warning: could not download convert_hf_to_gguf.py — fine-tuning unavailable until present in tools/"
fi

if ! curl -fsSL \
    "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_lora_to_gguf.py" \
    -o "$SCRIPT_DIR/tools/convert_lora_to_gguf.py" >> "$LOG_FILE" 2>&1; then
    print "Warning: could not download convert_lora_to_gguf.py — fine-tuning unavailable until present in tools/"
fi
