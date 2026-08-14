# gotcha_recall.ps1 - PreToolUse advisory
# Entrega el conocimiento ya escrito EN EL MOMENTO de la accion, no en un archivo
# que nadie abre. Se midio: la auto-carga por sesion es el 0,26% de lo escrito.
# Deniega el patron conocido-malo y dice el reemplazo, asi no necesita un humano
# para resolverse (sirve en modo loop). Escape: agregar #gotcha-ok al comando.
$ErrorActionPreference = 'Stop'
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $data = $raw | ConvertFrom-Json
    $cmd = $data.tool_input.command
    if (-not $cmd) { exit 0 }
    if ($cmd -match '#gotcha-ok') { exit 0 }

    $rulesPath = Join-Path $PSScriptRoot 'gotcha_rules.json'
    if (-not (Test-Path $rulesPath)) { exit 0 }
    $rules = (Get-Content $rulesPath -Raw -Encoding UTF8) | ConvertFrom-Json

    $nl = [char]10
    foreach ($r in $rules) {
        if ($cmd -notmatch $r.pattern) { continue }
        if ($r.PSObject.Properties.Name -contains 'unless' -and $r.unless -and ($cmd -match $r.unless)) { continue }

        $lines = @(
            ('GOTCHA ' + $r.id + ' - ' + $r.title),
            '',
            $r.why,
            '',
            ('Hazlo asi: ' + $r.instead),
            '',
            ('Detalle: ' + $r.source),
            '',
            'Si es un falso positivo, agrega #gotcha-ok al comando.'
        )
        # Registro en disco: si la decision alguna vez no se honra, igual queda
        # la prueba de que la regla disparo. Es el canario del canario.
        try {
            $logLine = ((Get-Date).ToUniversalTime().ToString('s') + 'Z  ' + $r.id + '  ' + ($cmd -replace '[
]+', ' '))
            Add-Content -Path (Join-Path $PSScriptRoot 'gotcha_recall_log.txt') -Value $logLine -Encoding UTF8
        } catch { }

        $out = @{
            hookSpecificOutput = @{
                hookEventName            = 'PreToolUse'
                permissionDecision       = 'deny'
                permissionDecisionReason = ($lines -join $nl)
            }
        } | ConvertTo-Json -Depth 5 -Compress
        Write-Output $out
        exit 0
    }
    exit 0
} catch {
    exit 0
}
