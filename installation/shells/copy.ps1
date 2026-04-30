# Copy the project to ~/.eternego/source/ so the service runs from a stable location.
. "$PSScriptRoot\lib.ps1"

$InstallDir = "$env:USERPROFILE\.eternego\source"

Print "Installing to $InstallDir"

if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

robocopy $ScriptDir $InstallDir /E /XD .git .venv __pycache__ /XF .env *.pyc /NFL /NDL /NJH /NJS /NC /NS /NP | Out-Null

# Expose the installed location; install.ps1 switches $ScriptDir explicitly.
$EternegoInstallDir = $InstallDir
