# Ensure Python 3.11+ is available.
. "$PSScriptRoot\lib.ps1"

$PythonOk = $false
try {
    $PyVer = & python --version 2>&1
    if ($PyVer -match "Python 3\.(1[1-9]|[2-9]\d)") { $PythonOk = $true }
} catch {}

if ($PythonOk) {
    Print "Python $PyVer already installed"
} else {
    Print "Installing python... estimation 1-2 minutes"
    Run winget install --id Python.Python.3.11 --source winget --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}
