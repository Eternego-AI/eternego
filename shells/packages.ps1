# Install Eternego and all Python dependencies.
. "$PSScriptRoot\lib.ps1"

Print "Installing eternego... estimation 3-5 minutes"
Run python -m pip install -e $ScriptDir

# Locate the installed eternego script via Python
$PyScripts = & python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
$EternegoBin = Join-Path $PyScripts "eternego.exe"
if (-not (Test-Path $EternegoBin)) {
    throw "eternego not found at $EternegoBin"
}
# Ensure Scripts dir is on PATH for this session
if ($env:Path -notlike "*$PyScripts*") {
    $env:Path = "$PyScripts;$env:Path"
}
