# Copy .env.example to .env if not already present.
. "$PSScriptRoot\lib.ps1"

$EternegoLogsDir = "$env:USERPROFILE\.eternego\logs"

if (-not (Test-Path "$ScriptDir\.env")) {
    Print "Creating .env from .env.example"
    Copy-Item "$ScriptDir\.env.example" "$ScriptDir\.env"
}

# Point logs to ~/.eternego/logs so they survive source updates.
$envContent = Get-Content "$ScriptDir\.env" -Raw
if ($envContent -match "(?m)^LOGS_DIR=$") {
    $envContent = $envContent -replace "(?m)^LOGS_DIR=$", "LOGS_DIR=$EternegoLogsDir"
    Set-Content "$ScriptDir\.env" $envContent -NoNewline
}

$envLines = Get-Content "$ScriptDir\.env"
$WEB_HOST = ($envLines | Where-Object { $_ -match "^WEB_HOST=" }) -replace "^WEB_HOST=", ""
$WEB_PORT = ($envLines | Where-Object { $_ -match "^WEB_PORT=" }) -replace "^WEB_PORT=", ""
