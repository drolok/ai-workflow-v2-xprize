param(
    [ValidateSet("core", "rag-qdrant", "rag-weaviate", "graph-rag", "observability", "management", "all")]
    [string[]]$Profiles = @(),
    [switch]$IncludeOllama
)

$ErrorActionPreference = "Stop"

function Test-DockerReady {
    try {
        $null = docker version --format '{{.Server.Version}}' 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-PatternsForProfile {
    param([string]$Profile)

    switch ($Profile) {
        "core" { return @("lifeos_postgres", "lifeos_redis") }
        "rag-qdrant" { return @("qdrant-toolstack") }
        "rag-weaviate" { return @("weaviate-lab") }
        "graph-rag" { return @("graphiti-neo4j") }
        "observability" { return @("seaweedfs-main", "posthog-hobby-*", "sentry-self-hosted-*") }
        "management" {
            return @(
                "metabase-lab",
                "pghero-lab",
                "pghero-lab-db",
                "unleash-lab",
                "unleash-lab-db",
                "plane-app-*",
                "n8n-local-automation",
                "open-webui-localai",
                "anythingllm-localai"
            )
        }
        "all" {
            return @(
                "lifeos_postgres",
                "lifeos_redis",
                "qdrant-toolstack",
                "weaviate-lab",
                "graphiti-neo4j",
                "seaweedfs-main",
                "posthog-hobby-*",
                "sentry-self-hosted-*",
                "metabase-lab",
                "pghero-lab",
                "pghero-lab-db",
                "unleash-lab",
                "unleash-lab-db",
                "plane-app-*",
                "n8n-local-automation",
                "open-webui-localai",
                "anythingllm-localai"
            )
        }
        default { return @() }
    }
}

function Resolve-ContainerNames {
    param([string[]]$Patterns)

    $allContainers = docker ps -a --format '{{.Names}}'
    $resolved = foreach ($pattern in ($Patterns | Select-Object -Unique)) {
        $allContainers | Where-Object { $_ -like $pattern }
    }

    return $resolved | Sort-Object -Unique
}

if (-not (Test-DockerReady)) {
    Write-Error "Docker Desktop no responde. Repara Docker antes de iniciar laboratorios."
    exit 1
}

if (-not $Profiles -or $Profiles.Count -eq 0) {
    Write-Output "No profile selected. Available profiles: core, rag-qdrant, rag-weaviate, graph-rag, observability, management, all."
    Write-Output "Example: .\start_lab_stack.ps1 -Profiles core,rag-qdrant -IncludeOllama"
    exit 0
}

$patterns = foreach ($profile in $Profiles) {
    Get-PatternsForProfile -Profile $profile
}

$targets = Resolve-ContainerNames -Patterns $patterns

if ($targets) {
    if ($targets -contains "lifeos_postgres" -or $targets -contains "lifeos_redis") {
        docker update --restart=unless-stopped lifeos_postgres lifeos_redis | Out-Null
    }
    docker start $targets | Out-Null
    Write-Output "Started lab containers:"
    $targets | ForEach-Object { Write-Output " - $_" }
} else {
    Write-Output "No matching lab containers were found for the selected profiles."
}

if ($IncludeOllama) {
    [Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "1", "Process")
    [Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "Process")
    # 2026-08-13: se comprueba el PUERTO, no el proceso. La app de bandeja
    # ("ollama app.exe") cuenta como proceso y hacia que este bloque dijera
    # "ya estaba corriendo" sin que nadie sirviera la API. Ver gotcha 61.
    if (-not $env:OLLAMA_HOST) { $env:OLLAMA_HOST = "127.0.0.1:11435" }
    $ollamaPort = [int]($env:OLLAMA_HOST -replace '.*:', '')
    $sirviendo = $false
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$ollamaPort/api/tags" -TimeoutSec 5 -UseBasicParsing | Out-Null
        $sirviendo = $true
    } catch { $sirviendo = $false }

    if (-not $sirviendo) {
        $ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
        if (Test-Path $ollamaExe) {
            Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 8
            try {
                Invoke-WebRequest -Uri "http://127.0.0.1:$ollamaPort/api/tags" -TimeoutSec 15 -UseBasicParsing | Out-Null
                Write-Output "Started Ollama on port $ollamaPort."
            } catch {
                Write-Warning "Ollama arranco pero el puerto $ollamaPort no responde. Comprueba quien lo tiene con: Get-NetTCPConnection -LocalPort $ollamaPort"
            }
        } else {
            Write-Warning "Ollama executable was not found at $ollamaExe"
        }
    } else {
        Write-Output "Ollama ya esta SIRVIENDO en el puerto $ollamaPort."
    }
}

Write-Output ""
Write-Output "Currently running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
