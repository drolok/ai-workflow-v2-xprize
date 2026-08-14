param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Get-Command python -ErrorAction Stop
& $python.Source (Join-Path $PSScriptRoot 'server.py') --port $Port
