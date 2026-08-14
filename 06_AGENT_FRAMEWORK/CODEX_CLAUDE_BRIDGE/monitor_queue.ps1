param (
    [string]$QueueDir = "C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\queue\requests"
)

# Loop infinito hasta encontrar un archivo
while ($true) {
    # Buscar archivos .json y tomar el más antiguo primero
    $files = Get-ChildItem -Path $QueueDir -Filter "*.json" | Sort-Object CreationTime
    
    if ($files.Count -gt 0) {
        # Si hay una tarea, la imprimimos y salimos.
        # Salir (exit 0) hará que Antigravity reciba la notificación de que la tarea en background terminó, despertándolo automáticamente.
        Write-Output "NEW_TASK_READY:$($files[0].FullName)"
        exit 0
    }
    
    # Pausar 5 segundos antes de volver a mirar
    Start-Sleep -Seconds 5
}
