# Start the Eternego service.
. "$PSScriptRoot\lib.ps1"

Print "Starting service"
Start-ScheduledTask -TaskName "Eternego"
