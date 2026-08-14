# =============================================================================
# Watchdog de la misión ENTORNO V2 (C:\AI_WORKFLOW_V2)
#
# POR QUÉ ES EXTERNO Y NO UN HOOK
# Un watchdog dentro de la sesión no sirve para nada: si la sesión muere, nada
# adentro corre. Tiene que ser un proceso de afuera, y por eso vive como tarea
# programada de Windows y no en `.claude/hooks/`.
#
# CÓMO SABE QUE LA SESIÓN ESTÁ VIVA
# El hook `critical_action_guard.ps1` (el de V2) escribe un latido en cada
# Bash/PowerShell. No depende de que el modelo se acuerde de nada: lo escribe
# el harness. Una sesión colgada o muerta deja de tocar el archivo sola.
#
# POR QUÉ NO ACTÚA SIEMPRE
# Solo hace algo si existe ARMADO.txt. Sin eso, una sesión que termina bien no
# dispara relanzamientos fantasma que gastarían tokens sin que nadie los pida.
# =============================================================================

$ErrorActionPreference = 'SilentlyContinue'

$dir       = 'C:\AI_WORKFLOW_V2\08_REPORTS\WATCHDOG'
$heartbeat = Join-Path $dir 'heartbeat.txt'
$armado    = Join-Path $dir 'ARMADO.txt'
$stop      = Join-Path $dir 'STOP.txt'
$estado    = Join-Path $dir 'estado.json'
$log       = Join-Path $dir 'watchdog.log'

# Minutos sin latido para considerar la sesión muerta o colgada. 12 = 4 ciclos
# del watchdog. Menos que eso da falsos positivos: un conteo de 300k archivos o
# un parseo masivo de scripts pueden pasar varios minutos sin tocar herramienta.
# 25, no 12: el latido solo se refresca con Bash/PowerShell (matcher del hook),
# asi que una sesion que lee archivos o razona un rato largo parece muerta y se
# gatillan relanzamientos duplicados sobre el mismo arbol. Paso el 2026-08-10:
# tres relanzamientos en 30 min, dos sesiones simultaneas sobre el mismo repo.
$STALL_MINUTES      = 25
# Techo duro. Es la red contra un bucle que queme tokens toda la noche: si se
# relanzó 12 veces y sigue cayéndose, relanzar otra vez no lo va a resolver.
$MAX_RELANZAMIENTOS = 12
# Espera después de relanzar, para darle tiempo a arrancar y latir.
$COOLDOWN_MINUTES   = 10

function Escribir-Log([string]$msg) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    "$([DateTime]::UtcNow.ToString('o'))  $msg" | Add-Content -Path $log -Encoding utf8
}

# --- Interruptores ----------------------------------------------------------
if (Test-Path $stop)          { exit 0 }
if (-not (Test-Path $armado)) { exit 0 }

# --- Estado -----------------------------------------------------------------
$st = @{ relanzamientos = 0; ultimoRelanzamiento = $null }
if (Test-Path $estado) {
    try {
        $leido = Get-Content $estado -Raw | ConvertFrom-Json
        if ($null -ne $leido.relanzamientos)      { $st.relanzamientos      = [int]$leido.relanzamientos }
        if ($null -ne $leido.ultimoRelanzamiento) { $st.ultimoRelanzamiento = $leido.ultimoRelanzamiento }
    } catch { }
}

if ($st.relanzamientos -ge $MAX_RELANZAMIENTOS) {
    Escribir-Log "TECHO ALCANZADO ($MAX_RELANZAMIENTOS relanzamientos). El watchdog se detiene solo. Borra estado.json y STOP.txt para rearmarlo."
    Set-Content -Path $stop -Value 'techo de relanzamientos alcanzado' -Encoding utf8
    exit 0
}

if ($st.ultimoRelanzamiento) {
    try {
        $ultimo = [DateTime]::Parse($st.ultimoRelanzamiento, $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
        if (([DateTime]::UtcNow - $ultimo).TotalMinutes -lt $COOLDOWN_MINUTES) { exit 0 }
    } catch { }
}

# --- ¿Late? -----------------------------------------------------------------
if (-not (Test-Path $heartbeat)) {
    Escribir-Log 'Sin archivo de latido. Armado pero la sesion nunca latio; no se relanza (podria no haber arrancado nunca).'
    exit 0
}

try {
    $ultimoLatido = [DateTime]::Parse((Get-Content $heartbeat -Raw).Trim(), $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
} catch {
    Escribir-Log 'Latido ilegible. No se actua: un archivo corrupto no es prueba de que la sesion murio.'
    exit 0
}

$minutosSinLatir = ([DateTime]::UtcNow - $ultimoLatido).TotalMinutes
if ($minutosSinLatir -lt $STALL_MINUTES) { exit 0 }

# --- Relanzar ---------------------------------------------------------------
Escribir-Log ('SIN LATIDO hace {0:N1} min (umbral {1}). Relanzando (intento {2}/{3}).' -f `
    $minutosSinLatir, $STALL_MINUTES, ($st.relanzamientos + 1), $MAX_RELANZAMIENTOS)

# El prompt va corto y sin caracteres raros a proposito: todo el detalle vive en
# el archivo que nombra. Meter un prompt largo aca reproduce exactamente el
# problema de quoting de los gotchas #3 y #20.
#
# RUTAS COMPLETAS, NUNCA NOMBRES PELADOS (hallazgo de la auditoria de S1/S2):
# 'pwsh' pelado es el alias de Microsoft Store -- un reparse point de 0 bytes
# que el Programador de tareas NO resuelve (0x80070002, ~32h fallando cada
# 3 min sin que nadie lo viera). powershell.exe de System32 es la unica shell
# con ruta estable de esta maquina; claude.cmd se fija a su ruta real de npm.
$PS_LAUNCHER = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$CLAUDE_CMD  = '<WINDOWS_HOME>\AppData\Roaming\npm\claude.cmd'
$prompt  = 'Reanuda la mision. Lee C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\WATCHDOG\REANUDAR.md y segui desde ahi.'
# --dangerously-skip-permissions NO es opcional aca: sin el, la sesion relanzada
# arranca, lee el prompt, intenta su primera herramienta y queda colgada en un
# pop-up de permiso que nadie va a contestar -- proceso vivo, CPU plana, sin
# archivo de sesion y sin latido. Un watchdog que relanza a una sala de espera
# no protege nada. Es el mismo flag con el que el fundador abre sus sesiones.
$comando = "Set-Location 'C:\AI_WORKFLOW_V2'; & '$CLAUDE_CMD' --dangerously-skip-permissions `"$prompt`""

if (-not (Test-Path $CLAUDE_CMD)) {
    Escribir-Log "FALLO al relanzar: no existe $CLAUDE_CMD (se movio la instalacion npm de claude?)"
    exit 0
}
try {
    # -ErrorAction Stop es obligatorio: con SilentlyContinue, un Start-Process
    # que no encuentra el binario emite error NO terminante, el catch no corre
    # y el log dice "Relanzada" sobre un proceso que nunca nacio.
    # La salida se redirige a archivo por DOS motivos, y el segundo importa mas:
    #  1. Auditabilidad: sin esto, una sesion relanzada que muere no deja rastro
    #     de por que. Se gastaron tres intentos adivinando lo que habria estado
    #     en una linea de stdout.
    #  2. Sin consola, claude corre HEADLESS y ejecuta el prompt hasta terminar.
    #     Con consola propia (que es lo que da Start-Process sin redirigir) queda
    #     en modo interactivo esperando un humano que no existe. Probado a mano:
    #     la misma invocacion, con la salida capturada, corre y termina bien.
    # Se saca -NoExit: con la salida redirigida ya no hay ventana que mantener.
    $salida = Join-Path $dir 'ultimo_relanzamiento.out.txt'
    $errores = Join-Path $dir 'ultimo_relanzamiento.err.txt'
    $proc = Start-Process -FilePath $PS_LAUNCHER -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $comando -WorkingDirectory 'C:\AI_WORKFLOW_V2' -RedirectStandardOutput $salida -RedirectStandardError $errores -PassThru -ErrorAction Stop
    $st.relanzamientos      = $st.relanzamientos + 1
    $st.ultimoRelanzamiento = [DateTime]::UtcNow.ToString('o')
    $st | ConvertTo-Json | Set-Content -Path $estado -Encoding utf8
    Escribir-Log "Relanzada. PID $($proc.Id). Total acumulado: $($st.relanzamientos)."
} catch {
    Escribir-Log "FALLO al relanzar: $($_.Exception.Message)"
}
