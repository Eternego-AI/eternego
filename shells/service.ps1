# Register Eternego as a Windows scheduled task.
. "$PSScriptRoot\lib.ps1"

Print "Registering service... estimation 1 minute"

$EternegoBin = "$ScriptDir\.venv\Scripts\eternego.exe"

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
