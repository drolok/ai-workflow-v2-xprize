param(
    [string]$RepoRoot = "<HOME>\\<PRIVATE_PROJECT>",
    [string]$OutputRoot = "C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\GRAPHIFY",
    [string]$GraphifyExe = "<WINDOWS_HOME>\.local\bin\graphify.exe",
    [string]$Backend = "ollama",
    [string]$Model = "qwen2.5-coder:7b"
)

$ErrorActionPreference = "Stop"

# Rebuild manual solamente.
# Evidencia observada en la corrida certificada del 2026-07-20:
# - extract: ~547.66s (~9.1 min)
# - cluster-only: ~35.39s
# - RAM libre minima observada: 10.12 GB
# Politica: correr bajo demanda cuando el repo cambie mucho; no activar watch ni hooks.

if (-not (Test-Path $GraphifyExe)) {
    throw "Graphify executable not found at $GraphifyExe"
}

if (-not (Test-Path $RepoRoot)) {
    throw "Repo root not found: $RepoRoot"
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$existingGraph = Join-Path $OutputRoot "graphify-out"
$backupRoot = Join-Path $OutputRoot "backups"

if (Test-Path $existingGraph) {
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    $backupPath = Join-Path $backupRoot "graphify-out_$timestamp"
    Move-Item -LiteralPath $existingGraph -Destination $backupPath
    Write-Host "Backed up previous graphify-out to $backupPath"
}

Write-Host "Rebuilding Graphify graph..."
Write-Host "Repo: $RepoRoot"
Write-Host "Output: $OutputRoot"
Write-Host "Backend: $Backend"
Write-Host "Model: $Model"

& $GraphifyExe extract $RepoRoot --backend $Backend --model $Model --max-concurrency 1 --out $OutputRoot
if ($LASTEXITCODE -ne 0) {
    throw "graphify extract failed with exit code $LASTEXITCODE"
}

& $GraphifyExe cluster-only $OutputRoot "--backend=$Backend" "--model=$Model" "--max-concurrency=1"
if ($LASTEXITCODE -ne 0) {
    throw "graphify cluster-only failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Graphify rebuild complete."
Write-Host "Graph: $OutputRoot\\graphify-out\\graph.json"
Write-Host "HTML:  $OutputRoot\\graphify-out\\graph.html"
Write-Host "Report: $OutputRoot\\graphify-out\\GRAPH_REPORT.md"
