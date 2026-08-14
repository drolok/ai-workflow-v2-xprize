# Protocolo de mudanza de contexto

Prompt reutilizable para reactivar el workflow completo al empezar un
chat nuevo (Claude Code) cuando se agotó el contexto de la sesión
anterior. `C:\AI_WORKFLOW_V2\CLAUDE.md` ya se carga solo en cada sesión
que arranca en esta carpeta — este protocolo es el paso siguiente:
qué leer primero para reconstruir el estado real, no solo el rol.

## El prompt (copiar/pegar como primer mensaje)

    Mudanza de contexto — retomar workflow en C:\AI_WORKFLOW_V2.

    Antes de responder nada:
    1. Lee C:\AI_WORKFLOW_V2\CLAUDE.md si no se cargó ya solo (confirma
       roles: Codex ejecuta, Claude audita).
    2. Lee, en este orden: 00_COMMAND_CENTER\CURRENT_STATE.md,
       00_COMMAND_CENTER\BLOCKERS.md,
       00_COMMAND_CENTER\DECISION_LOG.md (últimas entradas),
       01_OBSIDIAN\BIS_BRAIN\00_Command_Center\Pendientes.md,
       00_COMMAND_CENTER\NEXT_ACTIONS.md.
    3. Si hace falta ver relaciones entre notas del vault, corré
       03_AUTOMATION\SCRIPTS\rebuild_graphify.ps1 para refrescar el
       grafo antes de asumir que está al día.
    4. Con eso, resumime en 5-8 líneas: qué se cerró último, qué
       sigue abierto/bloqueado, y cuál es la próxima acción concreta.
       No repitas el contenido completo de los archivos.
    5. Esperá mi confirmación de por dónde seguir — no arranques a
       ejecutar nada todavía.

## Por qué estos archivos y no "el grafo" solo

Graphify existe de verdad en este repo (`03_AUTOMATION\SCRIPTS\
rebuild_graphify.ps1`, salida en `06_AGENT_FRAMEWORK\GRAPHIFY\
graphify-out\`), pero es un mapa de relaciones entre notas, no un
resumen de estado operativo. Los archivos de `00_COMMAND_CENTER` y
`Pendientes.md` son la fuente de verdad de "qué pasó y qué sigue" —
son texto vivo actualizado en cada sesión. El grafo ayuda a navegar
conexiones cuando hace falta, no reemplaza esta lectura.

## Límite honesto

Nadie fuerza a Claude a ejecutar este protocolo automáticamente al
iniciar sesión — `CLAUDE.md` se carga solo, pero este prompt hay que
pegarlo a mano como primer mensaje. Es la misma categoría de límite
que ya documenta `CLAUDE.md` en su sección "Límites honestos": no
existe un mecanismo técnico que dispare esto sin que el fundador lo
invoque.

## Mantenimiento

Este archivo debe reflejar siempre la lista real de documentos vivos
de `00_COMMAND_CENTER` y `Pendientes.md`. Si se agregan o renombran
archivos de estado, actualizar la lista del paso 2 en la misma tarea
que los crea.
