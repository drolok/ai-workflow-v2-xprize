# =============================================================================
# HARNESS -- smoke test del entorno C:\AI_WORKFLOW_V2
#
# ASCII PURO A PROPOSITO: powershell 5.1 lee .ps1 sin BOM como ANSI y un
# em-dash UTF-8 termina conteniendo el byte de una comilla curva que ROMPE
# el parseo (paso en la primera corrida de este mismo archivo). No agregar
# caracteres no-ASCII ni en comentarios.
#
# Verifica lo que de verdad tiene que seguir andando (handoff 4.2):
#   1. hook_heartbeat   -- el hook escribe el latido (se invoca de verdad)
#   2. isolation        -- hook y settings.json apuntan a V2, no al original
#   3. watchdog         -- parsea, su REANUDAR existe, pwsh/claude resolubles,
#                          tarea programada consultable
#   4. doc_paths        -- cada ruta citada en los docs operacionales existe
#   5. scripts_parse    -- los scripts del framework parsean (ps1/py/sh)
#   6. bridge_queue     -- las colas del puente Codex-Claude existen
#   7. ai_commands      -- los comandos verificados de cada IA responden
#
# Salida: JSON con _meta en 08_REPORTS\HARNESS\smoke_latest.json (+ copia
# timestampeada). Exit code = cantidad de checks en rojo. WARN no bloquea.
#
# Baseline de fallos conocidos (scripts heredados que nunca parsearon):
# baseline_known_failures.json en este mismo directorio. Se regenera con
# -UpdateBaseline tras revision humana. Un fallo NUEVO (fuera de baseline)
# pone el check en rojo; los de baseline se reportan como known.
#
# CANARIO (condicion de aceptacion, no extra): romper una ruta citada en un
# doc operacional real -> corrida ROJA; restaurar -> VERDE. Y plantar un .ps1
# con sintaxis rota en un directorio real de scripts -> ROJA; sacarlo ->
# VERDE. Las cuatro salidas van pegadas en el reporte de la sesion.
# =============================================================================
param(
    [switch]$UpdateBaseline,
    [string]$OutFile = ''
)

# RUNTIME DECLARADO (decision post-S1 #4): pwsh 7 y PS 5.1 dan veredictos
# DISTINTOS sobre los mismos .ps1 -- dos scripts sanos de PS7 pasaron por
# "rotos" porque el harness los parseo con 5.1. Un detector que cambia de
# veredicto segun quien lo lance no es un detector. Lanzar SIEMPRE con:
#   pwsh -NoProfile -File smoke.ps1
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Output "FATAL: smoke.ps1 declara runtime pwsh 7+ y fue lanzado con PowerShell $($PSVersionTable.PSVersion). Lanzalo con pwsh."
    exit 99
}

$ErrorActionPreference = 'Continue'
$ROOT     = 'C:\AI_WORKFLOW_V2'
$HARNESS  = Join-Path $ROOT '06_AGENT_FRAMEWORK\HARNESS'
$REPORTS  = Join-Path $ROOT '08_REPORTS\HARNESS'
$BASELINE = Join-Path $HARNESS 'baseline_known_failures.json'
$swTotal  = [System.Diagnostics.Stopwatch]::StartNew()
$checks   = [ordered]@{}

function New-Check { param($status, $detail, $failures = @(), $warnings = @(), $ms = 0)
    [ordered]@{ status = $status; detail = $detail; failures = @($failures); warnings = @($warnings); duration_ms = [int]$ms }
}

# --- 1. hook_heartbeat -------------------------------------------------------
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$hb = Join-Path $ROOT '08_REPORTS\WATCHDOG\heartbeat.txt'
$hookScript = Join-Path $ROOT '.claude\hooks\critical_action_guard.ps1'
$before = ''
if (Test-Path $hb) { $before = (Get-Content $hb -Raw).Trim() }
'{"tool_input":{"command":"echo smoke_harness"}}' | powershell -NoProfile -File $hookScript | Out-Null
$after = ''
if (Test-Path $hb) { $after = (Get-Content $hb -Raw).Trim() }
if ($after -and $after -ne $before) {
    $checks['hook_heartbeat'] = New-Check 'PASS' "latido avanzo: '$before' -> '$after'" @() @() $sw.ElapsedMilliseconds
} else {
    $checks['hook_heartbeat'] = New-Check 'FAIL' "el hook NO escribio latido nuevo (antes='$before', despues='$after')" @("$hookScript no actualizo $hb") @() $sw.ElapsedMilliseconds
}

# --- 2. isolation ------------------------------------------------------------
$sw.Restart()
$isoFails = @()
$hookSrc = Get-Content $hookScript -Raw
if ($hookSrc -match 'C:\\AI_WORKFLOW_V2\\') { $isoFails += 'critical_action_guard.ps1 contiene rutas al ORIGINAL (C:\AI_WORKFLOW_V2\)' }
$settingsPath = Join-Path $ROOT '.claude\settings.json'
try {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    $hookCmd = $settings.hooks.PreToolUse[0].hooks[0].command
    if ($hookCmd -notmatch 'AI_WORKFLOW_V2') { $isoFails += "settings.json invoca un hook fuera de V2: $hookCmd" }
} catch { $isoFails += "settings.json no parsea como JSON: $($_.Exception.Message)" }
$wdV2 = Join-Path $ROOT '06_AGENT_FRAMEWORK\WATCHDOG\watchdog_revision_integral.ps1'
if ((Get-Content $wdV2 -Raw) -match 'C:\\AI_WORKFLOW_V2\\') { $isoFails += 'watchdog V2 contiene rutas al ORIGINAL' }
if ($isoFails.Count -eq 0) { $checks['isolation'] = New-Check 'PASS' 'hook, settings.json y watchdog solo referencian V2' @() @() $sw.ElapsedMilliseconds }
else { $checks['isolation'] = New-Check 'FAIL' 'referencias al original en piezas criticas' $isoFails @() $sw.ElapsedMilliseconds }

# --- 3. watchdog -------------------------------------------------------------
$sw.Restart()
$wdFails = @(); $wdWarns = @()
$tokens = $null; $parseErrs = $null
[System.Management.Automation.Language.Parser]::ParseFile($wdV2, [ref]$tokens, [ref]$parseErrs) | Out-Null
if ($parseErrs -and $parseErrs.Count -gt 0) { $wdFails += "watchdog no parsea: $($parseErrs[0].Message)" }
$reanudar = Join-Path $ROOT '06_AGENT_FRAMEWORK\WATCHDOG\REANUDAR.md'
if (-not (Test-Path $reanudar)) { $wdFails += "falta $reanudar" }
$wdSrc = Get-Content $wdV2 -Raw
if ($wdSrc -match "Lee\s+(C:\\[^\s`"']+REANUDAR\.md)") {
    if (-not (Test-Path $Matches[1])) { $wdFails += "el prompt de relanzamiento apunta a un REANUDAR inexistente: $($Matches[1])" }
} else { $wdFails += 'no se encontro la ruta de REANUDAR en el prompt de relanzamiento' }
foreach ($bin in 'pwsh', 'claude') {
    if (-not (Get-Command $bin -ErrorAction SilentlyContinue)) { $wdFails += "'$bin' no resoluble: el relanzamiento fallaria" }
}
$task = schtasks /Query /TN 'V2_Watchdog_Revision' 2>&1
if ($LASTEXITCODE -ne 0) { $wdWarns += 'tarea programada V2_Watchdog_Revision no consultable (schtasks fallo); el latido igual queda como evidencia' }
elseif (-not (($task | Out-String) -match 'Listo|Ready|Running|ejecut')) { $wdWarns += "tarea V2_Watchdog_Revision en estado inesperado: $(($task | Select-Object -Last 1))" }
$armado = Join-Path $ROOT '08_REPORTS\WATCHDOG\ARMADO.txt'
if (-not (Test-Path $armado)) { $wdWarns += 'watchdog DESARMADO (sin ARMADO.txt) -- valido si es a proposito' }
if ($wdFails.Count -eq 0) { $checks['watchdog'] = New-Check 'PASS' 'parsea, REANUDAR existe, pwsh y claude resolubles' @() $wdWarns $sw.ElapsedMilliseconds }
else { $checks['watchdog'] = New-Check 'FAIL' 'watchdog no relanzaria bien' $wdFails $wdWarns $sw.ElapsedMilliseconds }

# --- 4. doc_paths ------------------------------------------------------------
$sw.Restart()
$docs = @(
    (Join-Path $ROOT 'CLAUDE.md'), (Join-Path $ROOT 'AGENTS.md'),
    (Join-Path $ROOT '06_AGENT_FRAMEWORK\HANDOFFS\HANDOFF_2026-08-10_ENVIRONMENT_V2.md'),
    (Join-Path $ROOT '06_AGENT_FRAMEWORK\WATCHDOG\REANUDAR.md'),
    (Join-Path $ROOT '06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\SESSION_RESUME_PROTOCOL.md'),
    (Join-Path $ROOT '06_AGENT_FRAMEWORK\GOTCHAS_TECNICOS_CRITICOS.md'),
    (Join-Path $ROOT '06_AGENT_FRAMEWORK\AGENT_ROLES.md')
)
$docs += (Get-ChildItem (Join-Path $ROOT '00_COMMAND_CENTER') -Filter '*.md' -File | ForEach-Object FullName)
$docs += (Get-ChildItem (Join-Path $ROOT '06_AGENT_FRAMEWORK\CONTROL_PLANE') -Filter '*.md' -File | ForEach-Object FullName)
# Rutas que los docs citan como "crear/borrar X" -- no existen por diseno:
$allowMissing = @('08_REPORTS\WATCHDOG\STOP.txt')
# INTERRUPTORES (decision post-S1 #1): rutas que existen o no POR DISENO --
# su presencia/ausencia es un estado valido, no salud. Se reporta como
# informacion, nunca como fallo. El motivo por entrada es obligatorio: es lo
# que impide que esta lista se vuelva el cajon donde se silencia lo incomodo.
$toggles = @{
    '08_REPORTS\WATCHDOG\ARMADO.txt' = 'interruptor del watchdog: presente = armado (sesion larga en curso), ausente = desarmado a proposito (cierre limpio)'
}
$pathFails = @(); $origRefs = 0; $checkedPaths = 0; $futureAi = @()
$reAbs = [regex]'[Cc]:\\[A-Za-z0-9_\\.\-]+'
$reRel = [regex]'(?<![\w\\/])((?:0[0-9]_[A-Z0-9_]+|1[0-2]_[A-Z0-9_]+|\.claude|\.ai)[\\/][A-Za-z0-9_\\/.\-]+[A-Za-z0-9_\-])'
foreach ($doc in $docs) {
    if (-not (Test-Path $doc)) { $pathFails += "doc operacional ausente: $doc"; continue }
    $ln = 0
    foreach ($line in [System.IO.File]::ReadLines($doc)) {
        $ln++
        foreach ($m in $reAbs.Matches($line)) {
            $p = $m.Value.TrimEnd('.', ',', ';', ':', '\')
            if ($p -match '[*<>]|\.\.\.') { continue }
            if ($p -match '^[Cc]:\\AI_WORKFLOW_V2\\') { $origRefs++; continue }
            if ($p -notmatch '^[Cc]:\\AI_WORKFLOW_V2\\') { continue }
            $checkedPaths++
            $rel = $p.Substring($ROOT.Length + 1) -replace '/', '\'
            if ($allowMissing -contains $rel) { continue }
            if ($toggles.ContainsKey($rel)) { continue }
            if (-not (Test-Path -LiteralPath $p)) { $pathFails += "$([System.IO.Path]::GetFileName($doc)):$ln -> $p" }
        }
        foreach ($m in $reRel.Matches($line)) {
            $p = $m.Groups[1].Value -replace '/', '\'
            if ($p -match '[*<>]|\.\.\.') { continue }
            if ($allowMissing -contains $p) { continue }
            if ($toggles.ContainsKey($p)) { continue }
            $checkedPaths++
            if (-not (Test-Path -LiteralPath (Join-Path $ROOT $p))) {
                # .ai\ es el namespace del Control Plane FUTURO (S2-S3): citarlo
                # antes de construirlo es estado declarado, no una ruta rota.
                if ($p -like '.ai\*') { $futureAi += $p }
                else { $pathFails += "$([System.IO.Path]::GetFileName($doc)):$ln -> $p" }
            }
        }
    }
}
$pathWarns = @()
foreach ($t in ($toggles.Keys | Sort-Object)) {
    $estadoToggle = 'AUSENTE'
    if (Test-Path -LiteralPath (Join-Path $ROOT $t)) { $estadoToggle = 'PRESENTE' }
    $pathWarns += "toggle $t : $estadoToggle -- $($toggles[$t])"
}
if ($origRefs -gt 0) { $pathWarns += "$origRefs referencias a C:\AI_WORKFLOW_V2 (original) en docs de V2 -- deuda de aislamiento, hoy resuelven porque el original sigue vivo" }
if ($futureAi.Count -gt 0) { $pathWarns += "$($futureAi.Count) rutas .ai\ citadas que aun no existen (Control Plane futuro declarado): $(($futureAi | Select-Object -Unique) -join ', ')" }
if ($pathFails.Count -eq 0) { $checks['doc_paths'] = New-Check 'PASS' "$checkedPaths rutas citadas verificadas en $($docs.Count) docs" @() $pathWarns $sw.ElapsedMilliseconds }
else { $checks['doc_paths'] = New-Check 'FAIL' "$($pathFails.Count) rutas citadas que NO existen (de $checkedPaths verificadas)" $pathFails $pathWarns $sw.ElapsedMilliseconds }

# --- 5. scripts_parse --------------------------------------------------------
$sw.Restart()
# 12_ARCHIVE es cuarentena de residuo (REORGANIZACION_2026-08-10.md): no es
# codigo vivo y no entra al censo. source_repos es codigo de terceros clonado
# (decision post-S1 #4): no lo vamos a arreglar y ensucia la senal.
$excludeDirs = @('node_modules', '__pycache__', '.venv', 'venv', '.git', 'site-packages', 'dist', 'build', '09_BACKUPS', '12_ARCHIVE', 'source_repos')
$extMap = @{ '.ps1' = 'ps'; '.psm1' = 'ps'; '.py' = 'py'; '.sh' = 'sh' }
$files = @{ ps = New-Object System.Collections.Generic.List[string]
            py = New-Object System.Collections.Generic.List[string]
            sh = New-Object System.Collections.Generic.List[string] }
$stack = New-Object System.Collections.Generic.Stack[string]
$stack.Push($ROOT)
while ($stack.Count -gt 0) {
    $dir = $stack.Pop()
    try {
        foreach ($sub in [System.IO.Directory]::EnumerateDirectories($dir)) {
            $name = [System.IO.Path]::GetFileName($sub)
            if ($excludeDirs -contains $name) { continue }
            if (([System.IO.File]::GetAttributes($sub) -band [System.IO.FileAttributes]::ReparsePoint)) { continue }
            $stack.Push($sub)
        }
        foreach ($f in [System.IO.Directory]::EnumerateFiles($dir)) {
            $ext = [System.IO.Path]::GetExtension($f).ToLowerInvariant()
            if ($extMap.ContainsKey($ext)) { $files[$extMap[$ext]].Add($f) }
        }
    } catch { }
}
$parseFails = New-Object System.Collections.Generic.List[object]
foreach ($f in $files.ps) {
    $t = $null; $e = $null
    [System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$e) | Out-Null
    if ($e -and $e.Count -gt 0) { $parseFails.Add(@{ file = $f; error = "PS: $($e[0].Message)" }) }
}
$tmpList = Join-Path $env:TEMP 'harness_pylist.txt'
[System.IO.File]::WriteAllLines($tmpList, $files.py)
$pyOut = & python (Join-Path $HARNESS 'parse_py.py') $tmpList 2>$null
try { foreach ($pf in ($pyOut | Out-String | ConvertFrom-Json)) { $parseFails.Add(@{ file = $pf.file; error = $pf.error }) } }
catch { $parseFails.Add(@{ file = 'parse_py.py'; error = "python no corrio o emitio basura: $(($pyOut | Out-String).Substring(0, [Math]::Min(300, ($pyOut | Out-String).Length)))" }) }
# Git Bash explicito: 'bash' del PATH puede resolver al de WSL (System32),
# que no ve rutas C:/ -- paso en la primera corrida de este harness.
$gitBash = 'C:\Program Files\Git\bin\bash.exe'
if ((Test-Path $gitBash) -and $files.sh.Count -gt 0) {
    $tmpSh = Join-Path $env:TEMP 'harness_shlist.txt'
    [System.IO.File]::WriteAllLines($tmpSh, ($files.sh | ForEach-Object { $_ -replace '\\', '/' }))
    $shScript = Join-Path $HARNESS 'parse_sh.sh'
    $shOut = & $gitBash ($shScript -replace '\\', '/') ($tmpSh -replace '\\', '/')
    foreach ($line in @($shOut)) {
        if ($line -match '^(.+?)\|(.*)$') { $parseFails.Add(@{ file = $Matches[1]; error = "SH: $($Matches[2])" }) }
    }
} elseif (-not (Test-Path $gitBash)) { $parseFails.Add(@{ file = '(bash)'; error = "Git Bash no encontrado en $gitBash : .sh sin verificar" }) }
$known = @()
if (Test-Path $BASELINE) { try { $known = ((Get-Content $BASELINE -Raw | ConvertFrom-Json).failures | ForEach-Object { $_.file }) } catch { } }
$newFails = @($parseFails | Where-Object { $known -notcontains $_.file })
$knownCount = $parseFails.Count - $newFails.Count
$census = "censo: $($files.ps.Count) ps1/psm1 + $($files.py.Count) py + $($files.sh.Count) sh (excluidos: $($excludeDirs -join ', '))"
if ($UpdateBaseline) {
    [ordered]@{ _meta = [ordered]@{ generated_at = [DateTime]::UtcNow.ToString('o'); generator = 'smoke.ps1 -UpdateBaseline'; item_count = $parseFails.Count }
                failures = $parseFails } | ConvertTo-Json -Depth 5 | Set-Content $BASELINE -Encoding utf8
}
if ($newFails.Count -eq 0) { $checks['scripts_parse'] = New-Check 'PASS' "$census; fallos conocidos en baseline: $knownCount, nuevos: 0" @() @() $sw.ElapsedMilliseconds }
else { $checks['scripts_parse'] = New-Check 'FAIL' "$census; $($newFails.Count) fallos NUEVOS fuera de baseline" ($newFails | ForEach-Object { "$($_.file): $($_.error)" }) @() $sw.ElapsedMilliseconds }

# --- 6. bridge_queue ---------------------------------------------------------
$sw.Restart()
$bq = Join-Path $ROOT '06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE'
$bqFails = @()
foreach ($d in 'queue\requests', 'queue\responses', 'queue\in_progress', 'queue\archive', 'queue\logs') {
    if (-not (Test-Path (Join-Path $bq $d))) { $bqFails += "falta $bq\$d" }
}
if (-not (Test-Path (Join-Path $bq 'bridge_queue.py'))) { $bqFails += 'falta bridge_queue.py' }
if ($bqFails.Count -eq 0) { $checks['bridge_queue'] = New-Check 'PASS' 'las 5 colas del puente + bridge_queue.py presentes' @() @() $sw.ElapsedMilliseconds }
else { $checks['bridge_queue'] = New-Check 'FAIL' 'estructura del puente incompleta' $bqFails @() $sw.ElapsedMilliseconds }

# --- 7. ai_commands ----------------------------------------------------------
# Solo invocabilidad (version/ping barato) -- un dispatch real cuesta tokens.
# Comandos EXACTOS de SESSION_RESUME_PROTOCOL.md, no reinventados.
# --- prompt_fresco -------------------------------------------------------------
# HANDOFF_ACTUAL.md es lo que lanza la sesion siguiente. Si el fundador siguio
# trabajando despues de que se escribio, quedo viejo -- y un prompt viejo se ve
# IDENTICO a uno fresco. Paso una vez con REANUDAR.md, que seguia diciendo que
# S3 estaba en curso cuando ya estaba cerrada, y casi hace que una sesion
# rehiciera el trabajo entero sobre archivos vivos.
#
# Esto no depende de que nadie se acuerde: el harness corre en cada sesion.
$sw.Restart()
$promptPath = Join-Path $ROOT '06_AGENT_FRAMEWORK\HANDOFFS\HANDOFF_ACTUAL.md'
$promptWarns = @(); $promptDetail = @()
if (-not (Test-Path $promptPath)) {
    $promptWarns += 'HANDOFF_ACTUAL.md no existe -- la sesion siguiente no tiene con que arrancar'
} else {
    $escrito = $null
    foreach ($linea in (Get-Content $promptPath -TotalCount 8)) {
        if ($linea -match '^escrito_el:\s*(.+)$') { $escrito = [datetime]::Parse($Matches[1].Trim()).ToUniversalTime() }
    }
    $ultimoCommit = $null
    try { $ultimoCommit = [datetime]::Parse((git -C $ROOT log -1 --format='%aI' 2>$null)).ToUniversalTime() } catch { }

    if ($null -eq $escrito) {
        $promptWarns += 'HANDOFF_ACTUAL.md no declara escrito_el -- no se puede saber si esta viejo'
    } elseif ($null -ne $ultimoCommit -and $ultimoCommit -gt $escrito.AddMinutes(10)) {
        $horas = [math]::Round(($ultimoCommit - $escrito).TotalHours, 1)
        $promptWarns += "HANDOFF_ACTUAL.md quedo VIEJO: hubo commits $horas h despues de escribirlo. Actualizalo antes de cerrar, o la sesion siguiente arranca con instrucciones vencidas"
        $promptDetail += "escrito_el $($escrito.ToString('yyyy-MM-dd HH:mm')) UTC  |  ultimo commit $($ultimoCommit.ToString('yyyy-MM-dd HH:mm')) UTC"
    } else {
        $promptDetail += "al dia (escrito_el $($escrito.ToString('yyyy-MM-dd HH:mm')) UTC)"
    }
}
$checks['prompt_fresco'] = New-Check 'PASS' ($promptDetail -join ' | ') @() $promptWarns $sw.ElapsedMilliseconds

$sw.Restart()
$aiFails = @(); $aiWarns = @(); $aiDetail = @()
$aiChecks = @(
    @{ name = 'kimi (Windows nativo)';  cmd = { kimi --version 2>&1 } },
    # OJO: --version responde 0.52.0 aunque la cuenta este muerta. El 2026-08-10 se
    # verifico con una llamada real: IneligibleTierError -- "no longer supported for
    # Gemini Code Assist for individuals". Un PASS aca solo dice que el BINARIO existe,
    # no que la IA sirva. Se deja como --version (una llamada real costaria tokens y
    # segundos en cada corrida) pero el nombre lo aclara, para que nadie lea un verde
    # como disponibilidad. Verificar auth es del despacho, no del harness.
    @{ name = 'gemini (binario; auth NO verificada -- ver AI_PERFORMANCE_LEDGER)'; cmd = { gemini --version 2>&1 } },
    @{ name = 'codex (WSL ~/.npm-global)'; cmd = { wsl -d Ubuntu -- bash -lc '~/.npm-global/bin/codex --version' 2>&1 } },
    @{ name = 'opencode (WSL via /mnt/c)'; cmd = { wsl -d Ubuntu -e bash -c 'opencode --version' 2>&1 } },
    @{ name = 'python (Windows, puente)'; cmd = { python --version 2>&1 } }
)
foreach ($c in $aiChecks) {
    $job = Start-Job -ScriptBlock $c.cmd
    if (Wait-Job $job -Timeout 90) { $out = (Receive-Job $job | Out-String).Trim() } else { Stop-Job $job; $out = 'TIMEOUT_90S' }
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    $firstLine = ($out -split "`r?`n")[0]
    if ($out -match 'TIMEOUT_90S|not recognized|no se reconoce|command not found|No such file') { $aiFails += "$($c.name): $firstLine" }
    else { $aiDetail += "$($c.name): $firstLine" }
}
$aiWarns += 'antigravity: solo via bridge pasivo (binario prohibido por el fundador); cubierto por bridge_queue'
if ($aiFails.Count -eq 0) { $checks['ai_commands'] = New-Check 'PASS' ($aiDetail -join ' | ') @() $aiWarns $sw.ElapsedMilliseconds }
else { $checks['ai_commands'] = New-Check 'FAIL' "IAs no invocables: $($aiFails.Count)" $aiFails ($aiWarns + $aiDetail) $sw.ElapsedMilliseconds }

# --- Reporte -----------------------------------------------------------------
$failCount = @($checks.Values | Where-Object { $_.status -eq 'FAIL' }).Count
$result = 'RED'
if ($failCount -eq 0) { $result = 'GREEN' }
$report = [ordered]@{
    _meta = [ordered]@{
        generated_at = [DateTime]::UtcNow.ToString('o')
        generator    = '06_AGENT_FRAMEWORK\HARNESS\smoke.ps1'
        root         = $ROOT
        duration_ms  = [int]$swTotal.ElapsedMilliseconds
        freshness    = 'live'
    }
    result = $result
    checks = $checks
}
New-Item -ItemType Directory -Force -Path $REPORTS | Out-Null
$json = $report | ConvertTo-Json -Depth 6
$json | Set-Content (Join-Path $REPORTS 'smoke_latest.json') -Encoding utf8
$json | Set-Content (Join-Path $REPORTS ("smoke_{0}.json" -f [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss'))) -Encoding utf8
if ($OutFile) { $json | Set-Content $OutFile -Encoding utf8 }

foreach ($k in $checks.Keys) {
    $c = $checks[$k]
    "{0,-14} {1,-4} {2}" -f $k, $c.status, $c.detail
    foreach ($f in $c.failures) { "               FAIL> $f" }
    foreach ($w in $c.warnings) { "               warn> $w" }
}
"RESULTADO: $result ($failCount checks en rojo) en $([int]($swTotal.ElapsedMilliseconds/1000))s"
exit $failCount
