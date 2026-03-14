# Install Eternego and all Python dependencies.
. "$PSScriptRoot\lib.ps1"

Print "Installing eternego... estimation 3-5 minutes"
Run python -m pip install -e $ScriptDir

$EternegoBin = (Get-Command eternego -ErrorAction Stop).Source
