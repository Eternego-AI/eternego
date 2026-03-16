# Install Eternego and all Python dependencies.
. "$PSScriptRoot\lib.ps1"

Print "Installing eternego... estimation 3-5 minutes"
Run python -m pip install -e $ScriptDir

# Refresh PATH so the newly installed script is visible
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

$EternegoBin = (Get-Command eternego -ErrorAction Stop).Source
