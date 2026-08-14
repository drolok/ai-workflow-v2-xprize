# Graphify Operativo

## Rol final

Graphify en este framework es un acelerador de navegacion para desarrollo.

- Si sirve para: ubicar hubs, imports directos, caminos estructurales cortos y reducir el universo inicial de archivos a revisar.
- No sirve como fuente de verdad arquitectonica final.
- No reemplaza verificacion humana linea por linea.
- No se deja ningun proceso residente: `query`, `path` y `explain` leen `graph.json` y terminan.

## Ubicacion operativa

- Carpeta operativa: `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY`
- Grafo: `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json`
- HTML: `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.html`
- Reporte: `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\GRAPH_REPORT.md`

## Consultar sin reconstruir

Comandos exactos:

```powershell
<WINDOWS_HOME>\.local\bin\graphify.exe query "where is task detail handled?" --graph "C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json"
<WINDOWS_HOME>\.local\bin\graphify.exe path "TaskDetailPage.tsx" "tasks" --graph "C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json"
<WINDOWS_HOME>\.local\bin\graphify.exe explain "taskService.ts" --graph "C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY\graphify-out\graph.json"
```

Atajo opcional si primero entras a la carpeta operativa:

```powershell
Set-Location "C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY"
<WINDOWS_HOME>\.local\bin\graphify.exe query "where is task detail handled?"
```

## Rebuild manual

No hay `watch`, hooks de Git ni servidor permanente.

Cuando el repo cambie de forma sustancial, reconstruir manualmente con:

```powershell
C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\rebuild_graphify.ps1
```

## Ultima evidencia operativa

- Consulta real probada sin rebuild: `graphify explain "taskService.ts" --graph ...`
- Tiempo observado de esa consulta: ~`715 ms`
- Sin proceso `graphify` residente despues de terminar
