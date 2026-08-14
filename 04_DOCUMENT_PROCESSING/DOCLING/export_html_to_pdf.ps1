param(
    [Parameter(Mandatory = $true)]
    [string]$HtmlPath,

    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

$edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

if (-not (Test-Path $edgePath)) {
    throw "Microsoft Edge no fue encontrado en $edgePath"
}

$resolvedHtml = [System.IO.Path]::GetFullPath($HtmlPath)
$resolvedPdf = [System.IO.Path]::GetFullPath($PdfPath)
$pdfDir = Split-Path -Parent $resolvedPdf

if (-not (Test-Path $resolvedHtml)) {
    throw "No se encontro el HTML esperado en $resolvedHtml"
}

New-Item -ItemType Directory -Force -Path $pdfDir | Out-Null

$fileUri = [System.Uri]::new($resolvedHtml).AbsoluteUri

& $edgePath `
    --headless `
    --disable-gpu `
    --no-pdf-header-footer `
    "--print-to-pdf=$resolvedPdf" `
    $fileUri | Out-Null

if (-not (Test-Path $resolvedPdf)) {
    throw "No se genero el PDF esperado en $resolvedPdf"
}

Write-Output $resolvedPdf
