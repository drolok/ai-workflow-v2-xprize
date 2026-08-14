param(
    [string]$OutputPath = "C:\AI_WORKFLOW_V2\04_DOCUMENT_PROCESSING\00_Inbox\phase4_audio_test.wav",
    [string]$Text = "this is a test"
)

Add-Type -AssemblyName System.Speech

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = -1
$speaker.Volume = 100
$speaker.SetOutputToWaveFile($resolvedOutput)
$speaker.Speak($Text)
$speaker.Dispose()

Write-Output $resolvedOutput
