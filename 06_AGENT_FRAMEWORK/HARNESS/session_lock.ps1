# =============================================================================
# HARNESS -- candado de una sesion Claude por handoff
#
# ASCII PURO A PROPOSITO: PowerShell 5.1 lee .ps1 sin BOM como ANSI. Un
# caracter UTF-8 puede romper el parseo. No agregar caracteres no-ASCII ni en
# comentarios.
#
# Verifica que no haya otra sesion Claude viva que ya reclame el handoff. El
# lock persiste si la sesion cae: el proximo arranque recupera un PID muerto o
# reutilizado por un proceso que no sea Claude. Asi no hay bloqueo perpetuo ni
# dos sesiones trabajando el mismo handoff al mismo tiempo.
#
# Lanzar SIEMPRE con:
#   pwsh -NoProfile -File session_lock.ps1
# =============================================================================
param(
    [int]$SessionPid = 0,
    [string]$HandoffPath = 'C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\HANDOFFS\HANDOFF_ACTUAL.md'
)

if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Output "FATAL: session_lock.ps1 declara runtime pwsh 7+ y fue lanzado con PowerShell $($PSVersionTable.PSVersion). Lanzalo con pwsh."
    exit 99
}

$ErrorActionPreference = 'Stop'
$HARNESS = 'C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\HARNESS'
$LOCK_PATH = Join-Path $HARNESS 'SESION_ACTIVA.lock'
$MUTEX_NAME = 'AI_WORKFLOW_V2_SESSION_LOCK'

function Get-ProcessParentId {
    param([int]$ProcessId)
    $record = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $record) { return 0 }
    return [int]$record.ParentProcessId
}

function Get-ClaudeSessionPid {
    param([int]$RequestedPid)
    $candidate = $RequestedPid
    if ($candidate -eq 0) { $candidate = $PID }
    $visited = @{}

    while ($candidate -gt 0 -and -not $visited.ContainsKey($candidate)) {
        $visited[$candidate] = $true
        $process = Get-Process -Id $candidate -ErrorAction SilentlyContinue
        if ($null -ne $process -and $process.ProcessName -ieq 'claude') {
            return $candidate
        }
        if ($RequestedPid -ne 0) { break }
        $candidate = Get-ProcessParentId -ProcessId $candidate
    }
    return 0
}

function Read-Lock {
    param([string]$Path)
    $data = @{}
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        if ($line -match '^([^=]+)=(.*)$') { $data[$Matches[1]] = $Matches[2] }
    }
    return $data
}

function Write-Lock {
    param([int]$OwnerPid, [string]$OwnerHandoff, [bool]$Reentry = $false)
    $utc = [DateTime]::UtcNow.ToString('o')
    $body = "PID=$OwnerPid`r`nUTC=$utc`r`nHANDOFF=$OwnerHandoff`r`n"
    [System.IO.File]::WriteAllText($LOCK_PATH, $body, [System.Text.Encoding]::ASCII)
    if ($Reentry) {
        Write-Output "LOCK RE-ENTRY: PID $OwnerPid refrescado desde $utc UTC. Handoff: $OwnerHandoff"
    } else {
        Write-Output "LOCK ACQUIRED: PID $OwnerPid desde $utc UTC. Handoff: $OwnerHandoff"
    }
}

$ownerPid = Get-ClaudeSessionPid -RequestedPid $SessionPid
if ($ownerPid -eq 0) {
    Write-Output 'FATAL: no se encontro un proceso con ProcessName claude para reclamar el lock.'
    exit 3
}

$mutex = New-Object System.Threading.Mutex($false, $MUTEX_NAME)
$hasMutex = $false
try {
    $hasMutex = $mutex.WaitOne([TimeSpan]::FromSeconds(15))
    if (-not $hasMutex) {
        Write-Output 'FATAL: timeout esperando la operacion atomica del candado de sesion.'
        exit 4
    }

    if (Test-Path -LiteralPath $LOCK_PATH) {
        try {
            $lock = Read-Lock -Path $LOCK_PATH
            $lockedPid = 0
            if ($lock.ContainsKey('PID')) { [void][int]::TryParse($lock['PID'], [ref]$lockedPid) }
            $lockedSince = '(hora UTC no valida o ausente)'
            if ($lock.ContainsKey('UTC') -and $lock['UTC']) { $lockedSince = $lock['UTC'] }
            $lockedProcess = $null
            if ($lockedPid -gt 0) { $lockedProcess = Get-Process -Id $lockedPid -ErrorAction SilentlyContinue }

            if ($null -ne $lockedProcess -and $lockedProcess.ProcessName -ieq 'claude' -and $lockedPid -eq $ownerPid) {
                Write-Lock -OwnerPid $ownerPid -OwnerHandoff $HandoffPath -Reentry $true
                exit 0
            }

            if ($null -ne $lockedProcess -and $lockedProcess.ProcessName -ieq 'claude') {
                Write-Output "BLOCKED: la sesion Claude con PID $lockedPid bloquea este handoff desde $lockedSince UTC."
                exit 2
            }

            if ($null -eq $lockedProcess) {
                Write-Output "STALE LOCK: PID $lockedPid no esta vivo; se toma el candado."
            } else {
                Write-Output "STALE LOCK: PID $lockedPid ahora pertenece a $($lockedProcess.ProcessName), no a claude; se toma el candado."
            }
        } catch {
            Write-Output "STALE LOCK: no se pudo leer el lock existente ($($_.Exception.Message)); se toma el candado."
        }
    }

    Write-Lock -OwnerPid $ownerPid -OwnerHandoff $HandoffPath
    exit 0
} finally {
    if ($hasMutex) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
