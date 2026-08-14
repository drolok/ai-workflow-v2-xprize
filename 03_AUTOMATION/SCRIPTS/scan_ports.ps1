param(
    [int[]]$Ports = @(3000, 3001, 3100, 3101, 5173, 8000, 8080, 1234, 5432, 6379, 27017),
    [int[]]$AdditionalPorts = @(),
    [string]$AiWorkflowRoot = "C:\AI_WORKFLOW_V2"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ollamaPort = if ($env:OLLAMA_HOST) { [int]($env:OLLAMA_HOST -replace '.*:', '') } else { 11434 }
$scanPorts = ($Ports + $ollamaPort + $AdditionalPorts | Sort-Object -Unique)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$reportDir = Join-Path $AiWorkflowRoot "08_REPORTS\PORT_SCANS"
$reportPath = Join-Path $reportDir ("port_scan_{0}.md" -f $timestamp)
$jsonPath = Join-Path $reportDir ("port_scan_{0}.json" -f $timestamp)
$latestJsonPath = Join-Path $reportDir "latest_port_scan.json"

New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$rows = foreach ($port in $scanPorts) {
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if (-not $listeners) {
        [pscustomobject]@{
            Port      = $port
            State     = "FREE"
            Process   = "-"
            Pid       = "-"
            Path      = "-"
            Addresses = "-"
        }
        continue
    }

    foreach ($listener in $listeners | Sort-Object OwningProcess -Unique) {
        $processName = "Unknown"
        $processPath = "-"
        try {
            $proc = Get-Process -Id $listener.OwningProcess -ErrorAction Stop
            $processName = $proc.ProcessName
            if ($proc.Path) {
                $processPath = $proc.Path
            }
        } catch {
        }

        [pscustomobject]@{
            Port      = $port
            State     = "LISTEN"
            Process   = $processName
            Pid       = $listener.OwningProcess
            Path      = $processPath
            Addresses = ($listener.LocalAddress -join ", ")
        }
    }
}

$markdownLines = foreach ($row in $rows) {
    "| {0} | {1} | {2} | {3} | {4} | {5} |" -f $row.Port, $row.State, $row.Process, $row.Pid, $row.Addresses, $row.Path
}

$markdown = @"
# Port Scan

Generated at: $generatedAt

| Port | State | Process | PID | Address | Path |
| --- | --- | --- | --- | --- | --- |
$(($markdownLines -join "`n"))
"@

Set-Content -LiteralPath $reportPath -Value $markdown -Encoding UTF8
@{
    generated_at = $generatedAt
    report_path  = $reportPath
    ports        = $rows
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@{
    generated_at = $generatedAt
    report_path  = $reportPath
    ports        = $rows
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $latestJsonPath -Encoding UTF8

$rows | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ("Report: {0}" -f $reportPath)
Write-Output ("JSON:   {0}" -f $jsonPath)
