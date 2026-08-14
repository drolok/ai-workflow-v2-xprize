[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
# Codex escribe progreso normal en stderr; no convertirlo en una excepcion de
# PowerShell antes de poder registrar su exit code y sus metricas.
$PSNativeCommandUseErrorActionPreference = $false
$workspace = "C:\AI_WORKFLOW_V2"
$framework = Join-Path $workspace "06_AGENT_FRAMEWORK"
$artifactDir = Join-Path $framework "rag-efficiency-artifacts-2026-07-23"
$resultsPath = Join-Path $artifactDir "measurements.json"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

$codexExe = Get-ChildItem "<WINDOWS_HOME>\AppData\Local\OpenAI\Codex\bin" -Directory |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
    ForEach-Object { Join-Path $_.FullName "codex.exe" }
if (-not (Test-Path $codexExe)) { throw "No se encontro codex.exe." }

$tasks = @(
    [ordered]@{
        Id = "certificacion";
        Prompt = "Tarea de lectura y sintesis. Dentro de C:\AI_WORKFLOW_V2, determina el estado actual de la certificacion del auditor de respaldo y el mejor candidato actual. Responde en espanol, de forma concisa, con hechos verificables y cita los archivos fuente exactos. No modifiques archivos ni ejecutes cambios.";
    },
    [ordered]@{
        Id = "seguridad-rag";
        Prompt = "Tarea de lectura y sintesis. Dentro de C:\AI_WORKFLOW_V2, identifica los gaps de seguridad P0 documentados para el diseno del RAG blindado, su impacto y el control o estado previsto. Responde en espanol, de forma concisa, con hechos verificables y cita los archivos fuente exactos. No modifiques archivos ni ejecutes cambios.";
    },
    [ordered]@{
        Id = "take-rate";
        Prompt = "Tarea de lectura y sintesis. Dentro de C:\AI_WORKFLOW_V2, explica que decision se tomo sobre el take rate de Tchasky y por que. Responde en espanol, de forma concisa, con hechos verificables y cita los archivos fuente exactos. No modifiques archivos ni ejecutes cambios.";
    }
)

$measurements = [System.Collections.Generic.List[object]]::new()

function Get-TokenCount([string]$LogPath) {
    $content = Get-Content -Raw -LiteralPath $LogPath
    $matches = [regex]::Matches($content, '(?im)tokens used\s*[:=]\s*([0-9][0-9,]*)')
    if ($matches.Count -eq 0) { return $null }
    return [int64](($matches[$matches.Count - 1].Groups[1].Value -replace ',', ''))
}

function Invoke-Baseline([hashtable]$Task) {
    $prefix = "sin-rag-$($Task.Id)"
    $response = Join-Path $artifactDir "$prefix-response.md"
    $log = Join-Path $artifactDir "$prefix-stdout.log"
    $started = Get-Date
    $previousErrorAction = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $codexExe exec -s danger-full-access -C $workspace -o $response $Task.Prompt 2>&1 | Tee-Object -FilePath $log | Out-Host
    $ErrorActionPreference = $previousErrorAction
    $exitCode = $LASTEXITCODE
    $ended = Get-Date
    if ($exitCode -ne 0) { throw "Baseline $($Task.Id) fallo con exit code $exitCode. Log: $log" }
    $measurements.Add([ordered]@{ task = $Task.Id; condition = "sin_rag"; started_at_utc = $started.ToUniversalTime().ToString('o'); ended_at_utc = $ended.ToUniversalTime().ToString('o'); wall_seconds = [math]::Round(($ended - $started).TotalSeconds, 3); tokens_used = Get-TokenCount $log; response_path = $response; stdout_path = $log })
}

function Invoke-WithRag([hashtable]$Task) {
    $prefix = "con-rag-$($Task.Id)"
    $response = Join-Path $artifactDir "$prefix-response.md"
    $log = Join-Path $artifactDir "$prefix-stdout.log"
    $started = Get-Date
    $previousErrorAction = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & (Join-Path $framework "invoke_with_rag_context.ps1") -Task $Task.Prompt -Agent codex -RepoRoot $workspace -FrameworkDocsDir $workspace -AllowedDirectory $workspace -TaskScope framework -OutputPath $response 2>&1 | Tee-Object -FilePath $log | Out-Host
    $ErrorActionPreference = $previousErrorAction
    $exitCode = $LASTEXITCODE
    $ended = Get-Date
    if ($exitCode -ne 0) { throw "RAG $($Task.Id) fallo con exit code $exitCode. Log: $log" }
    $measurements.Add([ordered]@{ task = $Task.Id; condition = "con_rag"; started_at_utc = $started.ToUniversalTime().ToString('o'); ended_at_utc = $ended.ToUniversalTime().ToString('o'); wall_seconds = [math]::Round(($ended - $started).TotalSeconds, 3); tokens_used = Get-TokenCount $log; response_path = $response; stdout_path = $log })
}

try {
    foreach ($task in $tasks) { Invoke-Baseline $task }

    $sessionStart = Get-Date
    $previousErrorAction = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & (Join-Path $framework "start_rag_session.ps1") 2>&1 | Tee-Object -FilePath (Join-Path $artifactDir "rag-session-start.log") | Out-Host
    $ErrorActionPreference = $previousErrorAction
    if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar la sesion RAG." }
    $sessionReady = Get-Date

    foreach ($task in $tasks) { Invoke-WithRag $task }
    $measurements | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resultsPath -Encoding utf8
    [ordered]@{ session_start_utc = $sessionStart.ToUniversalTime().ToString('o'); session_ready_utc = $sessionReady.ToUniversalTime().ToString('o'); startup_wall_seconds = [math]::Round(($sessionReady - $sessionStart).TotalSeconds, 3); measurements = $measurements } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $artifactDir "experiment.json") -Encoding utf8
}
finally {
    $statePath = "C:\AI_WORKFLOW_V2\11_LAB\rag-comparison\runtime\rag-session.json"
    if (Test-Path $statePath) {
        & (Join-Path $framework "stop_rag_session.ps1") 2>&1 | Tee-Object -FilePath (Join-Path $artifactDir "rag-session-stop.log") | Out-Host
    }
}
