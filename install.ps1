# Eternego installer for Windows — sets up the CLI and a persistent scheduled task.
#
# Run from a clone:
#     pwsh install.ps1            # light install (no fine-tuning deps)
#     pwsh install.ps1 -Full      # full install (includes training extras)
#
# Run remotely (Invoke-WebRequest pipe):
#     iwr -useb https://eternego.ai/install.ps1 | iex
#     $env:INSTALL_FULL=1; iwr -useb https://eternego.ai/install.ps1 | iex
#
# Override the version (default: latest GitHub release):
#     $env:ETERNEGO_VERSION="v0.1.0-rc1"; pwsh install.ps1
param([switch]$Full)

$ErrorActionPreference = "Stop"

if ($Full) { $env:INSTALL_FULL = "1" }

$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
$LogFile   = "$env:TEMP\eternego-install.log"

# If the install script was downloaded standalone (no shells\ next to it),
# fetch the source tarball from GitHub and continue from the extracted copy.
if (-not (Test-Path "$ScriptDir\shells")) {
    Write-Host "Downloading Eternego..."
    $Version = $env:ETERNEGO_VERSION
    if (-not $Version) {
        $latest = Invoke-RestMethod "https://api.github.com/repos/Eternego-AI/eternego/releases/latest"
        $Version = $latest.tag_name
    }
    if (-not $Version) {
        Write-Host "Could not determine Eternego version. Set ETERNEGO_VERSION explicitly."
        exit 1
    }
    $TmpDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "eternego-$Version-$(Get-Random)")
    $TarUrl = "https://github.com/Eternego-AI/eternego/archive/refs/tags/$Version.tar.gz"
    $TarPath = Join-Path $TmpDir "source.tar.gz"
    Invoke-WebRequest -Uri $TarUrl -OutFile $TarPath -UseBasicParsing
    tar -xzf $TarPath -C $TmpDir --strip-components=1
    Remove-Item $TarPath
    $ScriptDir = $TmpDir.FullName
    Write-Host "Eternego $Version downloaded to $ScriptDir"
}

. "$ScriptDir\shells\lib.ps1"

try {
    . "$ScriptDir\shells\banner.ps1"
    . "$ScriptDir\shells\copy.ps1"
    # From here on, operate on the installed copy
    $ScriptDir = $EternegoInstallDir
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
