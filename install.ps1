# Eternego installer for Windows — sets up the CLI and a persistent scheduled task.
# Usage: pwsh install.ps1
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile   = "$env:TEMP\eternego.log"

Write-Host "Installing Eternego from $ScriptDir ..."
pip install -q -e $ScriptDir

$EternegoBin = (Get-Command eternego -ErrorAction Stop).Source

Write-Host "Registering Windows scheduled task ..."

$Action = New-ScheduledTaskAction `
    -Execute $EternegoBin `
    -Argument "daemon" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName "Eternego" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Force | Out-Null

Write-Host ""
Write-Host "Eternego installed successfully."
Write-Host ""
Write-Host "  eternego service start    — start the service"
Write-Host "  eternego service stop     — stop the service"
Write-Host "  eternego service restart  — restart the service"
Write-Host "  eternego service status   — check service status"
Write-Host "  eternego service logs     — follow live logs ($LogFile)"
Write-Host "  eternego persona list     — list personas"
Write-Host ""
Write-Host "The task will run automatically at next logon."
Write-Host "To start it right now: eternego service start"
