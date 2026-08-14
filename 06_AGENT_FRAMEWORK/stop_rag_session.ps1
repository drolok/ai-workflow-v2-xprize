[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$ragRoot = Join-Path $workspaceRoot "11_LAB\rag-comparison"
$ragManager = Join-Path $ragRoot "manage_tchasky_rag.ps1"
$statePath = Join-Path $ragRoot "runtime\rag-session.json"

if (-not (Test-Path $statePath)) { throw "No existe una sesion RAG administrada en $statePath." }
$session = Get-Content -Raw $statePath | ConvertFrom-Json
try {
    $process = Get-Process -Id $session.server_pid -ErrorAction SilentlyContinue
    if ($process) { & "$env:SystemRoot\System32\taskkill.exe" /PID $session.server_pid /T /F | Out-Null }
    & $ragManager -Action stop
} finally {
    Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
}
Write-Output "RAG session stopped. PID: $($session.server_pid)"
