[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$workspace = "C:\AI_WORKFLOW_V2"
$framework = Join-Path $workspace "06_AGENT_FRAMEWORK"
$artifactDir = Join-Path $framework "rag-efficiency-artifacts-2026-07-23"
$tasks = @(
    @{ Id = "certificacion"; Prompt = "Tarea de lectura y sintesis. Dentro de C:\AI_WORKFLOW_V2, determina el estado actual de la certificacion del auditor de respaldo y el mejor candidato actual. Responde en espanol, de forma concisa, con hechos verificables y cita los archivos fuente exactos. No modifiques archivos ni ejecutes cambios." },
    @{ Id = "seguridad-rag"; Prompt = "Tarea de lectura y sintesis. Dentro de C:\AI_WORKFLOW_V2, identifica los gaps de seguridad P0 documentados para el diseno del RAG blindado, su impacto y el control o estado previsto. Responde en espanol, de forma concisa, con hechos verificables y cita los archivos fuente exactos. No modifiques archivos ni ejecutes cambios." },
    @{ Id = "take-rate"; Prompt = "Tarea de lectura y sintesis. Dentro de C:\AI_WORKFLOW_V2, explica que decision se tomo sobre el take rate de Tchasky y por que. Responde en espanol, de forma concisa, con hechos verificables y cita los archivos fuente exactos. No modifiques archivos ni ejecutes cambios." }
)
$measures = [System.Collections.Generic.List[object]]::new()
try {
    $sessionStarted = Get-Date
    $prior = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & (Join-Path $framework "start_rag_session.ps1") 2>&1 | Tee-Object -FilePath (Join-Path $artifactDir "rag-session-start-final.log") | Out-Host
    $ErrorActionPreference = $prior
    if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar la sesion RAG." }
    $sessionReady = Get-Date
    foreach ($task in $tasks) {
        $response = Join-Path $artifactDir "con-rag-$($task.Id)-response.md"
        $log = Join-Path $artifactDir "con-rag-$($task.Id)-stdout.log"
        $started = Get-Date
        $prior = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        & (Join-Path $framework "invoke_with_rag_context.ps1") -Task $task.Prompt -Agent codex -RepoRoot $workspace -FrameworkDocsDir $workspace -AllowedDirectory $workspace -TaskScope framework -OutputPath $response 2>&1 | Tee-Object -FilePath $log | Out-Host
        $ErrorActionPreference = $prior
        if ($LASTEXITCODE -ne 0) { throw "La corrida RAG $($task.Id) fallo." }
        $ended = Get-Date
        $measures.Add([ordered]@{ task=$task.Id; condition="con_rag"; wall_seconds=[math]::Round(($ended-$started).TotalSeconds,3); response_path=$response; stdout_path=$log })
    }
    [ordered]@{ startup_wall_seconds=[math]::Round(($sessionReady-$sessionStarted).TotalSeconds,3); measurements=$measures } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $artifactDir "rag-only-experiment.json") -Encoding utf8
}
finally {
    if (Test-Path "C:\AI_WORKFLOW_V2\11_LAB\rag-comparison\runtime\rag-session.json") { & (Join-Path $framework "stop_rag_session.ps1") 2>&1 | Tee-Object -FilePath (Join-Path $artifactDir "rag-session-stop-final.log") | Out-Host }
}
