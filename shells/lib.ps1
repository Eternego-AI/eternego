$TypeWriter = $true

$Green = [ConsoleColor]::Green

function Print($msg) {

    if (-not $TypeWriter) {
        Write-Host $msg
        return
    }

    foreach ($c in $msg.ToCharArray()) {
        Write-Host $c -NoNewline
        Start-Sleep -Milliseconds (Get-Random -Minimum 10 -Maximum 40)
    }

    Write-Host
}

function Type-AndErase($text, $wait = 1) {

    $prompt = "> "

    Write-Host $prompt -NoNewline -ForegroundColor $Green

    foreach ($c in $text.ToCharArray()) {
        Write-Host $c -NoNewline
        Start-Sleep -Milliseconds (Get-Random -Minimum 10 -Maximum 40)
    }

    Start-Sleep -Seconds $wait

    Write-Host "`r$(' ' * ($prompt.Length + $text.Length))`r" -NoNewline
}

function Show-Prompt($seconds = 3) {

    Write-Host "> " -NoNewline -ForegroundColor $Green

    $cycles = $seconds * 2

    for ($i = 0; $i -lt $cycles; $i++) {
        Write-Host "█" -NoNewline -ForegroundColor $Green
        Start-Sleep -Milliseconds 500
        Write-Host "`b `b" -NoNewline
        Start-Sleep -Milliseconds 500
    }
}

function Run() {
    Print "  Running $args"
    Add-Content $LogFile "  $ $args"
    & $args[0] $args[1..($args.Length - 1)] >> $LogFile 2>&1
}

function Print-File($file) {

    Get-Content $file | ForEach-Object {
        Write-Host $_
        Start-Sleep -Milliseconds 50
    }
}
