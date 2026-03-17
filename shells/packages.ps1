# Install Eternego and all Python dependencies.
. "$PSScriptRoot\lib.ps1"

$PipIndex = "--index-url https://pypi.org/simple/"

Print "Upgrading pip..."
Run python -m pip install --upgrade pip $PipIndex

Print "Installing eternego... estimation 3-5 minutes"
Run python -m pip install -e $ScriptDir $PipIndex

# Locate Python executable for service registration
$PythonBin = (Get-Command python -ErrorAction Stop).Source
