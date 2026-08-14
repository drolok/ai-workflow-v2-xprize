[CmdletBinding()]
param(
    [ValidateRange(1, 60)]
    [int]$IntervalSeconds = 2,
    [switch]$Once,
    [switch]$NoClear,
    [string]$DashboardUrl = 'http://127.0.0.1:8765/api/queue'
)

$ErrorActionPreference = 'Stop'
$BridgeRoot = $PSScriptRoot
$QueueRoot = Join-Path $BridgeRoot 'queue'
$TaskRoot = Join-Path $BridgeRoot 'tasks'
$DirectOutputRoot = Join-Path $TaskRoot 'outputs'

function Get-TextPreview {
    param([object]$Value, [int]$Maximum = 130)
    if ($null -eq $Value) { return '' }
    $text = ([string]$Value -replace "[\r\n]+", ' ').Trim()
    if ($text.Length -gt $Maximum) { return $text.Substring(0, $Maximum - 1) + '...' }
    return $text
}

function Get-QueueFromDisk {
    $sections = [ordered]@{}
    foreach ($folder in @('requests', 'in_progress', 'responses', 'archive')) {
        $folderPath = Join-Path $QueueRoot $folder
        $items = @()
        if (Test-Path $folderPath) {
            $items = @(Get-ChildItem -LiteralPath $folderPath -Filter '*.json' -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                ForEach-Object {
                    try { $body = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json } catch { $body = $null }
                    [pscustomobject]@{
                        task_id = $(if ($body) { $body.task_id } else { $_.BaseName })
                        title = $(if ($body) { $body.title } else { $_.Name })
                        status = $(if ($body) { $body.status } else { $folder })
                        summary = $(if ($body) { $body.summary } else { '' })
                        mtime = $_.LastWriteTime.ToString('s')
                    }
                })
        }
        $sections[$folder] = $items
    }
    [pscustomobject]@{ counts = [pscustomobject]@{
        requests = @($sections.requests).Count; in_progress = @($sections.in_progress).Count
        responses = @($sections.responses).Count; archive = @($sections.archive).Count
    }; sections = [pscustomobject]$sections; source = 'filesystem' }
}

function Get-QueueState {
    try {
        $state = Invoke-RestMethod -Uri $DashboardUrl -TimeoutSec 2
        $state | Add-Member -NotePropertyName source -NotePropertyValue 'dashboard API' -Force
        return $state
    } catch {
        return Get-QueueFromDisk
    }
}

function Get-RecentDirectFiles {
    $allFiles = @()
    if (Test-Path $TaskRoot) {
        $allFiles += Get-ChildItem -LiteralPath $TaskRoot -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in '.md', '.txt', '.json' } |
            Select-Object FullName, Name, Length, LastWriteTime
    }
    if (Test-Path $DirectOutputRoot) {
        $allFiles += Get-ChildItem -LiteralPath $DirectOutputRoot -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in '.md', '.txt', '.json' -and $_.Name -ne 'README.md' } |
            Select-Object FullName, Name, Length, LastWriteTime
    }
    return @($allFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 6)
}

function Show-Monitor {
    $state = Get-QueueState
    $now = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    if (-not $NoClear) { Clear-Host }
    Write-Host "AI_WORKFLOW - monitor terminal ($now)" -ForegroundColor Cyan
    Write-Host "Fuente cola: $($state.source) | refresco: $IntervalSeconds s | detener: Ctrl+C"
    Write-Host "Cola  pendientes=$($state.counts.requests)  activos=$($state.counts.in_progress)  respuestas=$($state.counts.responses)  archivo=$($state.counts.archive)" -ForegroundColor Yellow

    Write-Host "`nUltimas interacciones del puente" -ForegroundColor Green
    $shown = 0
    foreach ($folder in @('requests', 'in_progress', 'responses', 'archive')) {
        foreach ($item in @($state.sections.$folder | Select-Object -First 2)) {
            $shown++
            $id = $(if ($item.task_id) { $item.task_id } else { $item.file_name })
            $status = $(if ($item.status) { $item.status } else { $folder })
            $titlePreview = Get-TextPreview -Value ($item.title) -Maximum 90
            Write-Host "[$status] $id  $($item.mtime) - $titlePreview"
            $summary = Get-TextPreview -Value $item.summary
            if ($summary) { Write-Host "  $summary" -ForegroundColor DarkGray }
        }
    }
    if ($shown -eq 0) { Write-Host 'Sin JSON de cola.' -ForegroundColor DarkGray }

    $directFiles = Get-RecentDirectFiles
    Write-Host "`nArchivos de invocaciones directas codex exec" -ForegroundColor Green
    if (-not $directFiles) {
        Write-Host "Sin task/output capturados todavia. Guarda cada salida con -o en: $DirectOutputRoot" -ForegroundColor DarkGray
        return
    }
    foreach ($file in $directFiles) {
        $relative = $file.FullName.Substring($BridgeRoot.Length).TrimStart('\\')
        Write-Host "$($file.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))  $($file.Length) B  $relative"
    }

    $latestOutput = $directFiles | Where-Object { $_.FullName.StartsWith($DirectOutputRoot, [System.StringComparison]::OrdinalIgnoreCase) } | Select-Object -First 1
    if ($latestOutput) {
        Write-Host "`nTail de la ultima salida directa: $($latestOutput.Name)" -ForegroundColor Green
        Get-Content -LiteralPath $latestOutput.FullName -Tail 12 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_ }
    }
}

do {
    Show-Monitor
    if (-not $Once) { Start-Sleep -Seconds $IntervalSeconds }
} while (-not $Once)
