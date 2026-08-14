param(
    [ValidateSet("core", "rag-qdrant", "rag-weaviate", "graph-rag", "observability", "management", "all")]
    [string[]]$Profiles = @("all"),
    [switch]$KeepOllama
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

function Resolve-ContainerNames {
    param([string[]]$Patterns)

    $allContainers = docker ps -a --format '{{.Names}}'
    $resolved = foreach ($pattern in ($Patterns | Select-Object -Unique)) {
        $allContainers | Where-Object { $_ -like $pattern }
    }

    return $resolved | Sort-Object -Unique
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
                "qdrant-toolstack",
                "graphiti-neo4j",
                "weaviate-lab",
                "open-webui-localai",
                "anythingllm-localai",
                "metabase-lab",
                "pghero-lab",
                "pghero-lab-db",
                "unleash-lab",
                "unleash-lab-db",
                "plane-app-*",
                "n8n-local-automation",
                "seaweedfs-main",
                "posthog-hobby-*",
                "sentry-self-hosted-*"
            )
        }
        default { return @() }
    }
}

if (-not (Test-DockerReady)) {
    Write-Error "Docker Desktop no responde. Repara Docker antes de apagar laboratorios."
    exit 1
}

$patterns = foreach ($profile in $Profiles) {
    Get-PatternsForProfile -Profile $profile
}

$targets = Resolve-ContainerNames -Patterns $patterns

if ($targets) {
    docker update --restart=no $targets | Out-Null
    $runningTargets = docker ps --format '{{.Names}}' | Where-Object { $targets -contains $_ }
    if ($runningTargets) {
        docker stop $runningTargets | Out-Null
        Write-Output "Stopped lab containers:"
        $runningTargets | ForEach-Object { Write-Output " - $_" }
    } else {
        Write-Output "No heavy lab containers were running."
    }
} else {
    Write-Output "No heavy lab containers were found."
}

if (-not $KeepOllama) {
    $ollamaProcesses = Get-Process | Where-Object { $_.ProcessName -like "ollama*" }
    if ($ollamaProcesses) {
        $ollamaProcesses | Stop-Process -Force
        Write-Output "Stopped Ollama."
    } else {
        Write-Output "Ollama was already stopped."
    }
}

Write-Output ""
Write-Output "Remaining running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
