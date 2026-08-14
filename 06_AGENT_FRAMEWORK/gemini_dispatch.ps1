[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Prompt,

    [Parameter(Mandatory)]
    [string]$OutputFile,

    [string]$Model = 'gemini-3-flash-preview'
)

$ErrorActionPreference = 'Stop'

function Write-OutputFile([string]$Text) {
    $directory = Split-Path -Parent $OutputFile
    if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
    Set-Content -LiteralPath $OutputFile -Value $Text -Encoding utf8
}

function Get-GeminiStatus([System.Management.Automation.ErrorRecord]$ErrorRecord) {
    $response = $ErrorRecord.Exception.Response
    if (-not $response) { return 0 }
    return [int]$response.StatusCode
}

function Get-GeminiError([System.Management.Automation.ErrorRecord]$ErrorRecord) {
    $response = $ErrorRecord.Exception.Response
    if (-not $response) { return 'Request failed before an HTTP response was received.' }

    $statusCode = [int]$response.StatusCode
    $statusDescription = $response.StatusDescription
    $body = $ErrorRecord.ErrorDetails.Message
    try {
        if (-not $body -and $response.Content) {
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        } elseif (-not $body) {
            $stream = $response.GetResponseStream()
            if ($stream) {
            $reader = [System.IO.StreamReader]::new($stream)
            try { $body = $reader.ReadToEnd() } finally { $reader.Dispose(); $stream.Dispose() }
            }
        }
    } catch { }

    if ($body) {
        try {
            $apiError = $body | ConvertFrom-Json
            if ($apiError.error.message) { return "HTTP $statusCode ($statusDescription): $($apiError.error.message)" }
        } catch { }
        return "HTTP $statusCode ($statusDescription): $body"
    }
    return "HTTP $statusCode ($statusDescription)"
}

try {
    $envFile = 'C:\AI_WORKFLOW_V2\.env'
    $keyLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^\s*GEMINI_API_KEY\s*=\s*(.*)$' } | Select-Object -First 1
    if (-not $keyLine) { throw 'GEMINI_API_KEY was not found in C:\AI_WORKFLOW_V2\.env.' }

    $apiKey = ([regex]::Match($keyLine, '^\s*GEMINI_API_KEY\s*=\s*(.*)$').Groups[1].Value).Trim().Trim('"').Trim("'")
    if (-not $apiKey) { throw 'GEMINI_API_KEY in C:\AI_WORKFLOW_V2\.env is empty.' }

    $body = @{ contents = @(@{ parts = @(@{ text = $Prompt }) }) } | ConvertTo-Json -Depth 5 -Compress
    $uri = "https://generativelanguage.googleapis.com/v1beta/models/$([uri]::EscapeDataString($Model)):generateContent?key=$([uri]::EscapeDataString($apiKey))"
    # ponytail: se reintenta SOLO 429 y 503. El free tier de Gemini permite unas
    # pocas consultas por minuto y la cuota se repone sola pasado el minuto, asi
    # que esperar alcanza. Un 400 o un 403 no se reintentan: esos no se arreglan
    # esperando. Si algun dia hace falta mas control -- leer el retry-delay que
    # viene en el cuerpo del error, o backoff con jitter -- ese es el upgrade.
    $waits = @(25, 35)
    $attempt = 0
    $response = $null
    while ($true) {
        $attempt++
        try {
            $response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body
            break
        } catch {
            $status = Get-GeminiStatus $_
            if (($status -eq 429 -or $status -eq 503) -and $attempt -le $waits.Count) {
                $wait = $waits[$attempt - 1]
                Write-Verbose "HTTP $status en el intento $attempt. Espero $wait s y reintento."
                Start-Sleep -Seconds $wait
                continue
            }
            throw
        }
    }
    $text = (@($response.candidates[0].content.parts | ForEach-Object { $_.text }) -join '')
    if (-not $text) { throw 'The Gemini API returned HTTP 200 but no candidate text.' }
    Write-OutputFile $text
    exit 0
} catch {
    Write-OutputFile (Get-GeminiError $_)
    exit 1
}
