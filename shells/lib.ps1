# Shared functions — dot-sourced by sub-scripts.
# Requires: $LogFile to be set by the caller.

function Print($msg) {
    Write-Host $msg
}

function Run {
    $cmdStr = $args -join " "
    Write-Host "  `Running $cmdStr"
    Add-Content -Path $LogFile -Value "  `$ $cmdStr"
    & $args[0] $args[1..($args.Length - 1)] 2>&1 | Add-Content -Path $LogFile
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $cmdStr" }
}
