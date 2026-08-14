# Protocolo two-key Claude↔Codex — Fase 2 (S4)

**Fecha:** 2026-08-10 · **Base:** contrato 2.1 del SPEC + el ciclo probado en
S3 (TASK-1: el reviewer rechazó, se arregló, aprobó y firmó el done).

## El ciclo, formalizado

```
task (YAML) → accepted → implementing (owner, EN SU WORKTREE)
   → checkpoints al ledger → review (reviewer audita el DIFF, no el reporte)
   → RECHAZADO → fixing → review (con RESUME del thread, no re-pagar contexto)
   → APROBADO → merge (solo con la compuerta verde) → done (LO FIRMA EL REVIEWER)
```

## Reglas (las hace cumplir `reality.py`, no la costumbre)

1. **`owner != reviewer`**, siempre. `task-create` y `task-validate` lo rechazan.
2. **Riesgo HIGH exige criterio de canario** en acceptance. Rechazado si falta.
3. **El done lo firma el reviewer** (`task-status TASK-N done --actor <reviewer>`).
   **Forzado en código desde el 2026-08-11.** Hasta esa fecha era solo esta
   línea: `task-status TASK-N done --actor <el owner>` devolvía `OK`. El agujero
   apareció haciendo el rojo del registro retroactivo de TASK-10 — el owner
   firmó su propio done y nada lo frenó.

   Que `owner != reviewer` se validara en `task-create` no alcanzaba: eso separa
   los roles al ABRIR el task, pero si el owner puede firmar el CIERRE, el
   dos-llaves vuelve a ser una convención. Ahora `cmd_task_status` rechaza con
   exit 2 cualquier `done` que no firme el reviewer, y distingue en el mensaje
   si lo intentó el owner o un tercero.
4. **Merge solo tras `REVIEW_VERDICT APROBADO`**: la compuerta `merge-gate`
   (exit 0 solo si el último veredicto del task es APROBADO) corre antes de
   cualquier `git merge`. Sin verde de la compuerta, no hay merge.
5. **El ledger nunca se reescribe.** Un estado nuevo es un evento nuevo.
6. **Derive automático tras `task-status`/`task-create`** — achica la ventana
   de estado viejo. **El enforcement de `read` NO se toca**: auto-derive es
   conveniencia, `read` es la red. Las dos (decisión del anexo de S3).

## Worktrees — el aislamiento del owner

- El task declara `worktree` y `branch`. El owner implementa AHÍ; el árbol
  principal no se toca hasta el merge.
- Worktrees viven FUERA de V2 (`C:\AI_WORKFLOW_V2_WORKTREES\<task>`) para no
  contaminar censo ni harness del árbol principal.
- Sandbox del owner: `workspace-write` limitado a su worktree. No puede tocar
  el árbol principal ni el refugio, por construcción.
- La rama del task NO se borra al terminar (`branch -D` está vetado por el
  hook); queda como historia. El worktree sí se desmonta (`git worktree
  remove`) tras el merge — es espacio de trabajo transitorio, no residuo.

## Checkpoints — quién los emite y por qué

`CHECKPOINT` es un evento del ledger con el progreso observable del owner.
**Los emite el ORQUESTADOR (quien despacha), no el owner**: el ledger
principal vive fuera del worktree y el sandbox del owner no puede escribirlo
— ese aislamiento es deliberado (un owner no puede fabricar su propia
historia en el ledger). El orquestador observa (log del dispatch, diff
parcial, salida) y registra. El owner tampoco toca `.ai/events/**` de su
worktree: va en `scope.forbidden` del task, para que el merge del ledger sea
trivial.

## Rondas de corrección

Primera ronda: prompt completo POR ARCHIVO + `--json` para **capturar el
thread_id** (S3 lo omitió y re-pagó el contexto entero — la evidencia externa
del auditor lo confirmó: dos rollouts separados en `~/.codex/sessions/`).
Rondas siguientes: `codex exec resume <thread_id>` + solo los hallazgos.
