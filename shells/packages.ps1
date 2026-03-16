# Install Eternego and all Python dependencies.
. "$PSScriptRoot\lib.ps1"

Print "Installing eternego... estimation 3-5 minutes"
Run python -m pip install -e $ScriptDir

# Find the eternego script — add Python's Scripts dir to PATH if needed
$PyScripts = & python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
if ($PyScripts -and ($env:Path -notlike "*$PyScripts*")) {
    $env:Path = "$PyScripts;$env:Path"
}
# Also refresh system/user PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path

$EternegoBin = (Get-Command eternego -ErrorAction Stop).Source
