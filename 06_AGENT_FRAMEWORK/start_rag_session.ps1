[CmdletBinding()]
param(
    [int]$RagPort = 8787
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$ragRoot = Join-Path $workspaceRoot "11_LAB\rag-comparison"
$ragManager = Join-Path $ragRoot "manage_tchasky_rag.ps1"
$statePath = Join-Path $ragRoot "runtime\rag-session.json"
$healthUrl = "http://127.0.0.1:$RagPort/health"

function Test-RagHealth {
    try { return (Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3).status -eq "ok" } catch { return $false }
}

if (Test-RagHealth) { throw "El RAG ya esta corriendo en $healthUrl; no se creo una sesion nueva." }
if (Test-Path $statePath) { throw "Existe estado de sesion en $statePath; ejecuta stop_rag_session.ps1 antes de iniciar otra." }
if (-not (Test-Path $ragManager)) { throw "No existe el gestor RAG: $ragManager" }

$server = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ragManager, "-Action", "serve", "-Port", "$RagPort") -WorkingDirectory $ragRoot -PassThru -WindowStyle Hidden
$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    if (Test-RagHealth) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $statePath) | Out-Null
        [ordered]@{ server_pid = $server.Id; started_at = (Get-Date).ToUniversalTime().ToString("o"); rag_port = $RagPort } |
            ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
        Write-Output "RAG session started. PID: $($server.Id); state: $statePath"
        exit 0
    }
    Start-Sleep -Seconds 2
}
if (-not $server.HasExited) { & "$env:SystemRoot\System32\taskkill.exe" /PID $server.Id /T /F | Out-Null }
& $ragManager -Action stop
throw "El endpoint RAG no respondio en $healthUrl dentro de 90 segundos."
