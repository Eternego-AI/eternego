# Eternego installer for Windows — sets up the CLI and a persistent scheduled task.
# Usage: pwsh install.ps1
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile   = "$env:TEMP\eternego-install.log"

. "$ScriptDir\shells\lib.ps1"

try {
    . "$ScriptDir\shells\banner.ps1"
    . "$ScriptDir\shells\copy.ps1"
    . "$ScriptDir\shells\python.ps1"
    . "$ScriptDir\shells\packages.ps1"
    . "$ScriptDir\shells\gguf.ps1"
    . "$ScriptDir\shells\env.ps1"
    . "$ScriptDir\shells\service.ps1"
    . "$ScriptDir\shells\start.ps1"
} catch {
    Write-Host ""
    Write-Host "Installation failed or was interrupted. Log: $LogFile"
    exit 1
}

Clear-Host
Print "Dashboard is accessible at http://${WEB_HOST}:${WEB_PORT}"
