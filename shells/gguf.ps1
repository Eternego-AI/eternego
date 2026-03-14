# Download GGUF conversion scripts from llama.cpp.
. "$PSScriptRoot\lib.ps1"

Print "Downloading GGUF tools... estimation 1 minute"
try {
    Run curl -fsSL `
        "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_hf_to_gguf.py" `
        -o "$ScriptDir\tools\convert_hf_to_gguf.py"
} catch {
    Print "Warning: could not download convert_hf_to_gguf.py — fine-tuning unavailable until present in tools/"
}
try {
    Run curl -fsSL `
        "https://raw.githubusercontent.com/ggerganov/llama.cpp/master/convert_lora_to_gguf.py" `
        -o "$ScriptDir\tools\convert_lora_to_gguf.py"
} catch {
    Print "Warning: could not download convert_lora_to_gguf.py — fine-tuning unavailable until present in tools/"
}
