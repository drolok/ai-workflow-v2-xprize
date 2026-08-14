$ErrorActionPreference = 'SilentlyContinue'

# ---------------------------------------------------------------------------
# LATIDO DEL WATCHDOG
#
# Va montado sobre este hook a proposito, y no en uno propio: este ya corre en
# cada Bash/PowerShell, asi que el proceso ya esta pago. Un hook aparte
# duplicaria el arranque de PowerShell en cada llamada a herramienta, que en
# una sesion larga son miles.
#
# El latido NO depende de que el modelo se acuerde de escribirlo: lo escribe el
# harness. Esa es toda la gracia -- una sesion colgada o muerta deja de tocar
# el archivo sola, sin tener que darse cuenta de nada.
#
# Va ANTES del try del guard y con su propio try: si el latido falla, no puede
# arrastrar consigo la verificacion de acciones criticas.
# ---------------------------------------------------------------------------
try {
    $hbDir = 'C:\AI_WORKFLOW_V2\08_REPORTS\WATCHDOG'
    if (-not (Test-Path $hbDir)) { New-Item -ItemType Directory -Force -Path $hbDir | Out-Null }
    [DateTime]::UtcNow.ToString('o') | Set-Content -Path (Join-Path $hbDir 'heartbeat.txt') -NoNewline -Encoding ascii
} catch { }

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $data = $raw | ConvertFrom-Json
    $cmd = $data.tool_input.command
    if (-not $cmd) { exit 0 }

    $patterns = @(
        'danger-full-access',
        'push[^\n]*(--force\b|-f\b)',
        '(--force\b|-f\b)[^\n]*push',
        'reset\s+--hard',
        'rm\s+-rf',
        'Remove-Item[^\n]*-Recurse[^\n]*-Force',
        'DROP\s+(TABLE|DATABASE)',
        '--no-verify',
        'docker(\s|-)compose[^\n]*down[^\n]*-v',
        'branch\s+-D'
    )

    $windowFile = "C:\AI_WORKFLOW_V2\.claude\hooks\danger_full_access_window.txt"

    foreach ($p in $patterns) {
        if ($cmd -match $p) {
            if ($p -eq 'danger-full-access' -and (Test-Path $windowFile)) {
                try {
                    $expiry = [DateTime]::Parse((Get-Content $windowFile -Raw).Trim(), $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
                    if ([DateTime]::UtcNow -lt $expiry) {
                        $logLine = "$([DateTime]::UtcNow.ToString('o')) BYPASS (ventana activa hasta $($expiry.ToString('o'))): $cmd"
                        Add-Content -Path "C:\AI_WORKFLOW_V2\.claude\hooks\danger_full_access_bypass_log.txt" -Value $logLine
                        $out = @{
                            systemMessage = "danger-full-access permitido sin confirmar: ventana de 2h activa hasta $($expiry.ToString('o')) UTC (registrado en danger_full_access_bypass_log.txt)."
                            hookSpecificOutput = @{
                                hookEventName = 'PreToolUse'
                                permissionDecision = 'allow'
                                permissionDecisionReason = 'Ventana temporal de 2h autorizada explicitamente por el fundador, se revierte sola al expirar.'
                            }
                        } | ConvertTo-Json -Depth 6 -Compress
                        Write-Output $out
                        exit 0
                    }
                } catch {}
            }
            $reason = "PROTOCOLO CRITICO (C:\AI_WORKFLOW_V2\CLAUDE.md): este comando coincide con el patron de riesgo '$p'. Antes de continuar confirma: (1) revisaste el protocolo, (2) si toca danger-full-access o el repo real de Tchasky, es caso-por-caso con reporte explicito -- nunca default silencioso, (3) si es una decision de producto/negocio o cambia postura de riesgo, ya escalo al fundador y no la estas tomando tu mismo."
            $out = @{
                hookSpecificOutput = @{
                    hookEventName = 'PreToolUse'
                    permissionDecision = 'ask'
                    permissionDecisionReason = $reason
                }
            } | ConvertTo-Json -Depth 6 -Compress
            Write-Output $out
            exit 0
        }
    }
    exit 0
} catch {
    exit 0
}
