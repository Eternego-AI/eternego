# Download and run the test runner.
# Copy this file to your project root.
# Usage: pwsh test.ps1 [test_directory]
$ErrorActionPreference = "Stop"

$Repo = "Eternego-AI/test-runner"
$TmpDir = Join-Path $env:TEMP "test-runner"

if (-not (Test-Path "$TmpDir\run")) {
    Write-Host "Downloading test-runner..."
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

    $Headers = @{}
    if ($env:GITHUB_TOKEN) {
        $Headers["Authorization"] = "token $env:GITHUB_TOKEN"
    }

    $Release = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest" -Headers $Headers
    $Asset = $Release.assets | Where-Object { $_.name -eq "test-runner.zip" }
    if (-not $Asset) {
        Write-Host "Error: Could not find test-runner release."
        exit 1
    }
    Invoke-WebRequest $Asset.browser_download_url -OutFile "$TmpDir\test-runner.zip" -Headers $Headers
    Expand-Archive -Path "$TmpDir\test-runner.zip" -DestinationPath $TmpDir -Force
    Remove-Item "$TmpDir\test-runner.zip"
}

$TestDir = if ($args[0]) { $args[0] } else { "tests" }
python -u "$TmpDir\run" $TestDir
