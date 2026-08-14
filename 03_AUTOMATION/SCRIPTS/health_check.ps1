param(
    [string]$AiWorkflowRoot = "C:\AI_WORKFLOW_V2",
    [switch]$UpdateCanonical
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-SafeCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    try {
        $output = & $FilePath @Arguments 2>&1 | Out-String
        return [pscustomobject]@{
            Ok   = ($LASTEXITCODE -eq 0)
            Text = $output.Trim()
        }
    } catch {
        return [pscustomobject]@{
            Ok   = $false
            Text = $_.Exception.Message
        }
    }
}

function Get-PortListener {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $listeners) {
        return [pscustomobject]@{
            Listening = $false
            Details   = "Port $Port is free"
        }
    }

    $processRows = foreach ($listener in $listeners | Sort-Object OwningProcess -Unique) {
        try {
            $proc = Get-Process -Id $listener.OwningProcess -ErrorAction Stop
            "{0} (PID {1})" -f $proc.ProcessName, $proc.Id
        } catch {
            "PID {0}" -f $listener.OwningProcess
        }
    }

    return [pscustomobject]@{
        Listening = $true
        Details   = ($processRows -join ", ")
    }
}

function Test-HttpEndpoint {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        return [pscustomobject]@{
            Ok     = $true
            Status = [int]$response.StatusCode
            Detail = "HTTP $($response.StatusCode)"
        }
    } catch {
        # Bajo Set-StrictMode -Version Latest, leer una propiedad que no existe
        # es un error, no $null. Cuando el host no responde (servicio caido,
        # puerto cerrado) la excepcion NO trae .Response, asi que el
        # `if ($_.Exception.Response)` de antes reventaba el script entero.
        # Resultado: el health check no podia correr justo en el caso para el
        # que existe, que es un servicio caido. Encontrado el 2026-08-11.
        $respuesta = $_.Exception.PSObject.Properties['Response']
        if ($respuesta -and $respuesta.Value) {
            $codigo = [int]$respuesta.Value.StatusCode
            return [pscustomobject]@{
                Ok     = $false
                Status = $codigo
                Detail = "HTTP $codigo"
            }
        }

        return [pscustomobject]@{
            Ok     = $false
            Status = $null
            Detail = $_.Exception.Message
        }
    }
}

function New-Check {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Detail
    )

    [pscustomobject]@{
        Name   = $Name
        Status = $Status
        Detail = $Detail
    }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$reportDir = Join-Path $AiWorkflowRoot "08_REPORTS\HEALTH_CHECKS"
$canonicalPath = Join-Path $AiWorkflowRoot "00_COMMAND_CENTER\SYSTEM_HEALTH.md"
$reportPath = Join-Path $reportDir ("health_check_{0}.md" -f $timestamp)
$jsonPath = Join-Path $reportDir ("health_check_{0}.json" -f $timestamp)
$latestJsonPath = Join-Path $reportDir "latest_health_check.json"

New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$git = Invoke-SafeCommand -FilePath "git" -Arguments @("--version")
$python = Invoke-SafeCommand -FilePath "python" -Arguments @("--version")
$node = Invoke-SafeCommand -FilePath "node" -Arguments @("--version")
$docker = Invoke-SafeCommand -FilePath "docker" -Arguments @("version", "--format", "{{.Server.Version}}")
$ollama = Invoke-SafeCommand -FilePath "ollama" -Arguments @("--version")

$lmStudioPort = Get-PortListener -Port 1234
$openWebUiPort = Get-PortListener -Port 3100
$anythingPort = Get-PortListener -Port 3110
$n8nPort = Get-PortListener -Port 5678

$openWebUiHttp = Test-HttpEndpoint -Url "http://localhost:3100"
# 3110 y /api/ping, los dos a proposito (corregido 2026-08-11):
#   - El puerto era 3101, que es el VIEJO. El RAG se movio al 3110 para dejarle
#     el 3101 al gate de tests de Tchasky. Con el gate corriendo, este chequeo
#     interrogaba al servidor de tests y reportaba su respuesta como si fuera
#     la del RAG ("HTTP 404; listener: wslrelay"). Observabilidad mirando el
#     servicio equivocado y sin forma de notarlo.
#   - La raiz del RAG devuelve 404 aunque este sano; /api/ping devuelve
#     {"online":true}. Preguntar por la raiz daba WARN permanente.
$anythingHttp = Test-HttpEndpoint -Url "http://127.0.0.1:3110/api/ping"

$n8nContainer = Invoke-SafeCommand -FilePath "docker" -Arguments @(
    "ps",
    "-a",
    "--filter",
    "name=^n8n-local-automation$",
    "--format",
    "{{.Status}}|{{.Ports}}|{{.Image}}"
)

$checks = @()
$checks += New-Check -Name "Git" -Status ($(if ($git.Ok) { "OK" } else { "FAIL" })) -Detail $git.Text
$checks += New-Check -Name "Python" -Status ($(if ($python.Ok) { "OK" } else { "FAIL" })) -Detail $python.Text
$checks += New-Check -Name "Node.js" -Status ($(if ($node.Ok) { "OK" } else { "FAIL" })) -Detail $node.Text
$checks += New-Check -Name "Docker Engine" -Status ($(if ($docker.Ok) { "OK" } else { "FAIL" })) -Detail $docker.Text
$checks += New-Check -Name "Ollama" -Status ($(if ($ollama.Ok) { "OK" } else { "FAIL" })) -Detail $ollama.Text
$checks += New-Check -Name "LM Studio" -Status ($(if ($lmStudioPort.Listening) { "OK" } else { "FAIL" })) -Detail $lmStudioPort.Details
$checks += New-Check -Name "Open WebUI" -Status ($(if ($openWebUiHttp.Ok) { "OK" } else { "WARN" })) -Detail ("{0}; listener: {1}" -f $openWebUiHttp.Detail, $openWebUiPort.Details)
$checks += New-Check -Name "AnythingLLM" -Status ($(if ($anythingHttp.Ok) { "OK" } else { "WARN" })) -Detail ("{0}; listener: {1}" -f $anythingHttp.Detail, $anythingPort.Details)

if ($n8nContainer.Ok -and $n8nContainer.Text) {
    $n8nStatus = if ($n8nPort.Listening) { "OK" } else { "WARN" }
    $checks += New-Check -Name "n8n" -Status $n8nStatus -Detail ("{0}; listener: {1}" -f $n8nContainer.Text, $n8nPort.Details)
}

$okCount = @($checks | Where-Object { $_.Status -eq "OK" }).Count
$warnCount = @($checks | Where-Object { $_.Status -eq "WARN" }).Count
$failCount = @($checks | Where-Object { $_.Status -eq "FAIL" }).Count

$jsonObject = [ordered]@{
    generated_at = $generatedAt
    report_path  = $reportPath
    checks       = $checks
    ports        = @(
        [pscustomobject]@{ Port = 1234; Listening = $lmStudioPort.Listening; Detail = $lmStudioPort.Details }
        [pscustomobject]@{ Port = 3100; Listening = $openWebUiPort.Listening; Detail = $openWebUiPort.Details }
        [pscustomobject]@{ Port = 3101; Listening = $anythingPort.Listening; Detail = $anythingPort.Details }
        [pscustomobject]@{ Port = 5678; Listening = $n8nPort.Listening; Detail = $n8nPort.Details }
        # 2026-08-13: no basta con que alguien escuche el puerto de Ollama. El
        # 11434 lo tenia Antigravity IDE, que aceptaba la conexion y no respondia:
        # este chequeo habria informado "escuchando = true" con Ollama muerto.
        # Ahora se comprueba que la API CONTESTE, y en el puerto real. Gotcha 61.
        $ollamaPort = if ($env:OLLAMA_HOST) { [int]($env:OLLAMA_HOST -replace '.*:', '') } else { 11434 }
        $ollamaEscucha = (Get-PortListener -Port $ollamaPort)
        $ollamaResponde = $false
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:$ollamaPort/api/tags" -TimeoutSec 5 -UseBasicParsing | Out-Null
            $ollamaResponde = $true
        } catch { $ollamaResponde = $false }
        $ollamaDetalle = if ($ollamaResponde) { "Ollama responde en $ollamaPort" }
                         elseif ($ollamaEscucha.Listening) { "OCUPADO POR OTRO PROCESO: alguien escucha $ollamaPort pero no responde /api/tags -> $($ollamaEscucha.Details)" }
                         else { "nadie escucha $ollamaPort" }
        [pscustomobject]@{ Port = $ollamaPort; Listening = $ollamaResponde; Detail = $ollamaDetalle }
    )
}

$summaryLines = foreach ($check in $checks) {
    "- **{0}**: {1} - {2}" -f $check.Name, $check.Status, $check.Detail
}

$markdown = @"
# Health Check

Generated at: $generatedAt

## Summary

- OK: $okCount
- WARN: $warnCount
- FAIL: $failCount

## Checks

$(($summaryLines -join "`n"))

## Canonical files

- Current state: `C:\AI_WORKFLOW_V2\00_COMMAND_CENTER\CURRENT_STATE.md`
- System health: `C:\AI_WORKFLOW_V2\00_COMMAND_CENTER\SYSTEM_HEALTH.md`

## Notes

- This script is read-only with respect to live services.
- Reports are written to `C:\AI_WORKFLOW_V2\08_REPORTS\HEALTH_CHECKS`.
"@

Set-Content -LiteralPath $reportPath -Value $markdown -Encoding UTF8
$jsonObject | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$jsonObject | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $latestJsonPath -Encoding UTF8

# Nota: -UpdateCanonical actualiza SYSTEM_HEALTH.md; CURRENT_STATE.md solo se menciona en el informe.
if ($UpdateCanonical) {
    if (Test-Path $canonicalPath) {
        $backupPath = Join-Path (Split-Path -Parent $canonicalPath) ("SYSTEM_HEALTH.backup_{0}.md" -f $timestamp)
        Copy-Item -LiteralPath $canonicalPath -Destination $backupPath -Force
    }

    Set-Content -LiteralPath $canonicalPath -Value $markdown -Encoding UTF8
}

$checks | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ("Report: {0}" -f $reportPath)
Write-Output ("JSON:   {0}" -f $jsonPath)
