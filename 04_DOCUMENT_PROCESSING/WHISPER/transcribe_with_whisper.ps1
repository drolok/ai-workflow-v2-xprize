param(
    [Parameter(Mandatory = $true)]
    [string]$AudioPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputMarkdownPath
)

$cliPath = "C:\AI_WORKFLOW_V2\04_DOCUMENT_PROCESSING\WHISPER\bin_v191\Release\whisper-cli.exe"
$modelPath = "C:\AI_WORKFLOW_V2\04_DOCUMENT_PROCESSING\WHISPER\models\ggml-tiny.en.bin"

if (-not (Test-Path $cliPath)) {
    throw "whisper-cli no fue encontrado en $cliPath"
}

if (-not (Test-Path $modelPath)) {
    throw "Modelo de whisper.cpp no fue encontrado en $modelPath"
}

$resolvedAudio = (Resolve-Path $AudioPath).Path
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputMarkdownPath)
$outputDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$rawDir = "C:\AI_WORKFLOW_V2\04_DOCUMENT_PROCESSING\Processed"
New-Item -ItemType Directory -Force -Path $rawDir | Out-Null

$stem = [System.IO.Path]::GetFileNameWithoutExtension($resolvedAudio)
$rawPrefix = Join-Path $rawDir ($stem + "_whisper")

& $cliPath -m $modelPath -f $resolvedAudio -l en -otxt -of $rawPrefix -nt *> $null

$rawTxt = $rawPrefix + ".txt"
if (-not (Test-Path $rawTxt)) {
    throw "No se genero la transcripcion esperada en $rawTxt"
}

$transcript = (Get-Content $rawTxt -Raw).Trim()

$markdown = @"
# Audio Transcript: $stem

- Source file: $resolvedAudio
- Engine: `whisper.cpp`
- Model: `ggml-tiny.en.bin`

## Transcript

$transcript
"@

Set-Content -Path $resolvedOutput -Value $markdown -Encoding UTF8
Write-Output $resolvedOutput
