# Install Eternego and all Python dependencies inside a virtual environment.
. "$PSScriptRoot\lib.ps1"

$VenvDir = "$ScriptDir\.venv"
$PipIndex = "--index-url https://pypi.org/simple/"

if (-not (Test-Path $VenvDir)) {
    Print "Creating virtual environment..."
    Run python -m venv $VenvDir
}

# Use venv's Python and pip from here on
$PythonBin = "$VenvDir\Scripts\python.exe"

Print "Upgrading pip..."
Run $PythonBin -m pip install --upgrade pip $PipIndex

Print "Installing eternego... estimation 3-5 minutes"
Run $PythonBin -m pip install -e $ScriptDir $PipIndex

# Make 'eternego' available system-wide
$VenvScripts = "$VenvDir\Scripts"
$UserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$VenvScripts*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$VenvScripts;$UserPath", "User")
    $env:Path = "$VenvScripts;$env:Path"
    Print "Added $VenvScripts to PATH"
}
