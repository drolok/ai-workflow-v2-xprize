param(
    [string]$PythonExe = "python",
    [string]$RunnerPath = "C:\AI_WORKFLOW_V2\03_AUTOMATION\N8N\host_runner.py",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8765,
    [string]$Token = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$resolvedToken = $Token.Trim()
if (-not $resolvedToken) {
    foreach ($scope in "Process", "User", "Machine") {
        $candidate = [Environment]::GetEnvironmentVariable("AIW_N8N_RUNNER_TOKEN", $scope)
        if ($candidate) {
            $resolvedToken = $candidate.Trim()
            break
        }
    }
}
if (-not $resolvedToken) {
    throw "AIW_N8N_RUNNER_TOKEN is required. Set the environment variable or pass -Token explicitly."
}

$existing = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*host_runner.py*" }

if ($existing) {
    Write-Output ("Host runner already active: PID {0}" -f ($existing.ProcessId -join ", "))
    return
}

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $PythonExe
$startInfo.Arguments = ('"{0}"' -f $RunnerPath)
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$startInfo.UseShellExecute = $false
$startInfo.EnvironmentVariables["AIW_N8N_RUNNER_HOST"] = $BindHost
$startInfo.EnvironmentVariables["AIW_N8N_RUNNER_PORT"] = [string]$Port
$startInfo.EnvironmentVariables["AIW_N8N_RUNNER_TOKEN"] = $resolvedToken

$process = [System.Diagnostics.Process]::Start($startInfo)
Write-Output ("Host runner started with PID {0}" -f $process.Id)
