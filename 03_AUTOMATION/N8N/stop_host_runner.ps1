Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$existing = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*host_runner.py*" }

if (-not $existing) {
    Write-Output "Host runner is not active."
    return
}

$existing | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
    Write-Output ("Stopped host runner PID {0}" -f $_.ProcessId)
}
