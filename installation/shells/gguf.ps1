# Download GGUF conversion scripts from llama.cpp.
. "$PSScriptRoot\lib.ps1"

Print "Downloading GGUF tools... estimation 1 minute"
New-Item -ItemType Directory -Force -Path "$ScriptDir\tools" | Out-Null

$base = "https://raw.githubusercontent.com/ggerganov/llama.cpp/master"
try {
    Invoke-WebRequest -Uri "$base/convert_hf_to_gguf.py" -OutFile "$ScriptDir\tools\convert_hf_to_gguf.py" -UseBasicParsing
} catch {
    Print "Warning: could not download convert_hf_to_gguf.py — fine-tuning unavailable until present in tools/"
}
try {
    Invoke-WebRequest -Uri "$base/convert_lora_to_gguf.py" -OutFile "$ScriptDir\tools\convert_lora_to_gguf.py" -UseBasicParsing
} catch {
    Print "Warning: could not download convert_lora_to_gguf.py — fine-tuning unavailable until present in tools/"
}
