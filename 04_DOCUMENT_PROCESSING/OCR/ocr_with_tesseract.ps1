param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputMarkdownPath
)

$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$tessdataPath = "C:\Program Files\Tesseract-OCR\tessdata"

if (-not (Test-Path $tesseractPath)) {
    throw "Tesseract no fue encontrado en $tesseractPath"
}

$env:TESSDATA_PREFIX = $tessdataPath

$resolvedImage = (Resolve-Path $ImagePath).Path
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputMarkdownPath)
$outputDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$rawDir = "C:\AI_WORKFLOW_V2\04_DOCUMENT_PROCESSING\Processed"
New-Item -ItemType Directory -Force -Path $rawDir | Out-Null

$stem = [System.IO.Path]::GetFileNameWithoutExtension($resolvedImage)
$rawPrefix = Join-Path $rawDir ($stem + "_ocr")

& $tesseractPath $resolvedImage $rawPrefix --oem 1 --psm 6 -l eng

$rawTxt = $rawPrefix + ".txt"
if (-not (Test-Path $rawTxt)) {
    throw "No se genero la salida OCR esperada en $rawTxt"
}

$ocrText = (Get-Content $rawTxt -Raw).Trim()

$markdown = @"
# OCR Extraction: $stem

- Source file: $resolvedImage
- Engine: `Tesseract 5.x`

## Extracted Text

$ocrText
"@

Set-Content -Path $resolvedOutput -Value $markdown -Encoding UTF8
Write-Output $resolvedOutput
