# Copy .env.example to .env if not already present.
. "$PSScriptRoot\lib.ps1"

if (-not (Test-Path "$ScriptDir\.env")) {
    Print "Creating .env from .env.example"
    Copy-Item "$ScriptDir\.env.example" "$ScriptDir\.env"
}

$envLines = Get-Content "$ScriptDir\.env"
$WEB_HOST = ($envLines | Where-Object { $_ -match "^WEB_HOST=" }) -replace "^WEB_HOST=", ""
$WEB_PORT = ($envLines | Where-Object { $_ -match "^WEB_PORT=" }) -replace "^WEB_PORT=", ""
