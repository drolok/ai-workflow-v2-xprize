[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Task,

    [ValidateSet('codigo', 'investigacion', 'auditoria')]
    [string]$TaskType = 'codigo',

    [string]$RepoRoot,
    [string]$OutputPath,
    [string]$LogPath,
    [ValidateRange(1, 7200)]
    [int]$TimeoutSec = 900,

    # Sólo para pruebas controladas: permite comprobar la degradación sin invocar Codex.
    [string]$CodexExeOverride
)

$ErrorActionPreference = 'Stop'
# $PSScriptRoot puede llegar vacío en el default de un parámetro según cómo se
# invoque el script (ej. powershell -File anidado); $PSCommandPath es fiable.
$ScriptRoot = Split-Path -Parent $PSCommandPath
if (-not $LogPath) { $LogPath = Join-Path $ScriptRoot 'fallback-chain.jsonl' }
$workspaceRoot = Split-Path -Parent $ScriptRoot
if (-not $RepoRoot) { $RepoRoot = $workspaceRoot }
$fallbackModels = @(
    'nvidia/z-ai/glm-5.2',
    'nvidia/mistralai/mistral-small-4-119b-2603',
    'nvidia/nvidia/nemotron-3-super-120b-a12b',
    'nvidia/nvidia/nemotron-3-ultra-550b-a55b',
    'nvidia/minimaxai/minimax-m3',
    'nvidia/stepfun-ai/step-3.7-flash'
)

if (-not $OutputPath) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputPath = Join-Path $ScriptRoot "fallback-invocations\\task-$stamp.md"
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath), (Split-Path -Parent $LogPath) | Out-Null

function Write-FallbackLog([hashtable]$Entry) {
    $record = [ordered]@{ timestamp = (Get-Date).ToUniversalTime().ToString('o') }
    foreach ($key in $Entry.Keys) { $record[$key] = $Entry[$key] }
    ($record | ConvertTo-Json -Compress -Depth 5) | Add-Content -LiteralPath $LogPath -Encoding utf8
}

function Quote-ProcessArgument([string]$Value) {
    # Win32 command-line quoting for Start-Process; keeps prompts with spaces/quotes intact.
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Invoke-External([string]$FilePath, [string[]]$Arguments, [string]$StdoutPath, [string]$StderrPath) {
    $commandLine = ($Arguments | ForEach-Object { Quote-ProcessArgument $_ }) -join ' '
    try {
        $process = Start-Process -FilePath $FilePath -ArgumentList $commandLine -WorkingDirectory $RepoRoot -PassThru -NoNewWindow `
            -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath
    } catch {
        return @{ started = $false; timed_out = $false; exit_code = $null; error = $_.Exception.Message }
    }
    if (-not $process.WaitForExit($TimeoutSec * 1000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        return @{ started = $true; timed_out = $true; exit_code = $null; error = "timeout after $TimeoutSec seconds" }
    }
    $exitCode = $process.ExitCode
    return @{ started = $true; timed_out = $false; exit_code = $exitCode; error = '' }
}

function Get-CodexExe {
    if ($CodexExeOverride) { return $CodexExeOverride }
    return Get-ChildItem '<WINDOWS_HOME>\AppData\Local\OpenAI\Codex\bin' -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
        ForEach-Object { Join-Path $_.FullName 'codex.exe' }
}

function Get-OpenCodeCmd {
    $command = Get-Command 'opencode.cmd' -ErrorAction SilentlyContinue
    if (-not $command) { throw 'No se encontró opencode.cmd en PATH.' }
    return $command.Source
}

function Get-ErrorSummary([string]$Path) {
    if (-not (Test-Path $Path)) { return '' }
    $text = ((Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue) -join ' ') -replace '\s+', ' '
    $text = $text.Trim()
    return $text.Substring(0, [Math]::Min(500, $text.Length))
}

function Get-OpenCodeText([string]$Path) {
    if (-not (Test-Path $Path)) { return '' }
    $parts = foreach ($line in Get-Content -LiteralPath $Path) {
        try {
            $event = $line | ConvertFrom-Json -ErrorAction Stop
            if ($event.type -eq 'text' -and $event.part.text) { [string]$event.part.text }
        } catch { }
    }
    return $parts -join "`n"
}

$attempt = 0
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("fallback-chain-$([guid]::NewGuid().ToString('N'))")
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
try {
    $opencodeCmd = Get-OpenCodeCmd
    $codexExe = Get-CodexExe
    $stdout = Join-Path $tempRoot 'codex.stdout.log'
    $stderr = Join-Path $tempRoot 'codex.stderr.log'
    $attempt++
    if (-not $codexExe -or -not (Test-Path $codexExe)) {
        $codexResult = @{ started = $false; timed_out = $false; exit_code = $null; error = "codex.exe not found: $codexExe" }
    } else {
        $codexResult = Invoke-External $codexExe @('exec', '-s', 'danger-full-access', '-C', $RepoRoot, '--add-dir', $ScriptRoot, '-o', $OutputPath, $Task) $stdout $stderr
    }
    $codexError = "$($codexResult.error) $(Get-ErrorSummary $stderr)".Trim()
    $codexUsageLimit = $codexError -like "*You've hit your usage limit*"
    $codexSucceeded = $codexResult.started -and -not $codexResult.timed_out -and $codexResult.exit_code -eq 0 -and (Test-Path $OutputPath)
    Write-FallbackLog @{ attempt = $attempt; provider = 'codex'; model = 'codex'; task_type = $TaskType; status = $(if ($codexSucceeded) { 'success' } else { 'failed' }); exit_code = $codexResult.exit_code; timed_out = $codexResult.timed_out; usage_limit_detected = $codexUsageLimit; error = $codexError; output_path = $OutputPath }
    if ($codexSucceeded) {
        Write-Output "Resuelto por Codex. Salida: $OutputPath"
        exit 0
    }

    foreach ($model in $fallbackModels) {
        $attempt++
        $safeModel = $model -replace '[^a-zA-Z0-9._-]', '_'
        $stdout = Join-Path $tempRoot "$safeModel.stdout.log"
        $stderr = Join-Path $tempRoot "$safeModel.stderr.log"
        $result = Invoke-External $opencodeCmd @('run', '--agent', 'build', '--model', $model, '--dir', $RepoRoot, '--auto', '--format', 'json', $Task) $stdout $stderr
        $text = Get-OpenCodeText $stdout
        # Windows PowerShell no expone ExitCode para wrappers .cmd de npm; en ese
        # caso el contrato de éxito es un evento JSON `text` de OpenCode. Para un
        # exit code disponible, cualquier valor distinto de cero sigue fallando.
        $exitSucceeded = ($null -eq $result.exit_code -or $result.exit_code -eq 0)
        $succeeded = $result.started -and -not $result.timed_out -and $exitSucceeded -and -not [string]::IsNullOrWhiteSpace($text)
        $attemptError = "$($result.error) $(Get-ErrorSummary $stderr)".Trim()
        Write-FallbackLog @{ attempt = $attempt; provider = 'opencode'; model = $model; task_type = $TaskType; status = $(if ($succeeded) { 'success' } else { 'failed' }); exit_code = $result.exit_code; timed_out = $result.timed_out; error = $attemptError; output_path = $OutputPath }
        if ($succeeded) {
            Set-Content -LiteralPath $OutputPath -Value $text -Encoding utf8
            if ($model -eq 'nvidia/stepfun-ai/step-3.7-flash') {
                Add-Content -LiteralPath $OutputPath -Value "`n`n⚠️ RESUELTO POR STEP-3.7-FLASH — REQUIERE REVISIÓN ADICIONAL ANTES DE CONFIAR EN CÓDIGO DE PRODUCCIÓN" -Encoding utf8
            }
            Write-Output "Resuelto por fallback $model. Salida: $OutputPath"
            exit 0
        }
    }
    throw "La cadena de fallback se agotó. Revisá $LogPath"
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
