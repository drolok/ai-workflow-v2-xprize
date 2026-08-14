# REANUDAR — te relanzó el watchdog de V2

Si estás leyendo esto, la sesión anterior **se cayó o se colgó** y una tarea
programada de Windows te levantó automáticamente. No hay nadie mirando: el
fundador está durmiendo o fuera.

**No preguntes nada. No esperes confirmación. Retomá.**

---

## DONDE ESTAMOS AHORA (2026-08-10 19:35Z) — lee esto antes de los 4 pasos

**S3 y S4 estan CERRADAS y auditadas. No las repitas.** Todo lo que sigue ya
existe en disco y commiteado:

- La shared reality completa: `.ai/events/`, `.ai/tasks/`, `.ai/handoffs/`,
  `.ai/state/` y `CURRENT_STATE.json` derivado.
- `.ai/bin/reality.py` con sus once subcomandos, incluido `merge-gate` y el
  auto-derive tras `task-status`.
- Dos ciclos two-key completos con actores cruzados (TASK-1 y TASK-2, los dos
  en `done`).

**La sesion en curso es S5 — el cluster entero al ledger.** Su handoff:
`06_AGENT_FRAMEWORK/HANDOFFS/HANDOFF_2026-08-10_ENVIRONMENT_V2_S5_CLUSTER.md`,
y empieza con dos anexos de auditoria: leelos antes del resto.

**Si te relanzo el watchdog:** mira primero `PLAN_SESIONES.md` para confirmar
cual es la sesion en curso — este bloque puede haber quedado viejo, y ya paso
una vez. La bitacora del plan y el `git log` son mas confiables que esta nota.

---

## ANTES DE TERMINAR: APAGA EL INTERRUPTOR

**Cuando termines tu mision, borra `08_REPORTS\WATCHDOG\ARMADO.txt`.**

Es una linea y es obligatorio. Corres en modo headless: cuando terminas tu
trabajo, tu proceso SALE. Para el watchdog eso es indistinguible de haberte
caido — deja de llegar el latido y te relanza. Si no apagas el interruptor, te
relanza una y otra vez hasta el techo de 12, y varias sesiones terminan
escribiendo sobre el mismo arbol a la vez.

Paso de verdad el 2026-08-10: tres relanzamientos en media hora y dos sesiones
simultaneas sobre el mismo repo. Nadie perdio trabajo de casualidad, no por
diseno.

**Si te caes de verdad, ARMADO.txt sigue ahi y el watchdog te levanta — que es
exactamente para lo que existe.** Apagarlo al terminar es lo que distingue
"termine" de "me cai", y esa distincion no la puede hacer el watchdog solo.

---

## ESTE PROYECTO ES EL ENTORNO V2, NO TCHASKY

La misión es construir y verificar el entorno nuevo en `C:\AI_WORKFLOW_V2`.

- **NO** continúes la agenda de la beta de Tchasky, **NO** toques
  `<PRIVATE_PROJECT>`, **NO** abras el plan de milestones. Ese trabajo está
  pausado a propósito.
- `C:\AI_WORKFLOW` (sin `_V2`) es el refugio: **no lo toques** — no muevas,
  no borres, no edites nada ahí adentro.
- Fuera de límites dentro de V2: `.claude/`, `09_BACKUPS/`, `01_OBSIDIAN/` y
  el symlink `<PRIVATE_PROJECT>`. Se referencian, no se mueven.

---

## Los 4 pasos, en orden

### 1. Mirá dónde quedó

Abrí **`06_AGENT_FRAMEWORK/CONTROL_PLANE/PLAN_SESIONES.md`**. Ahí está el plan
de sesiones con el estado de cada una. Buscá la sesión en curso.

Si ese archivo todavía no existe, la caída fue muy temprana: leé
**`06_AGENT_FRAMEWORK/HANDOFFS/HANDOFF_2026-08-10_ENVIRONMENT_V2.md`** y
arrancá desde el principio de la misión (PASO 1 del handoff).

### 2. Averiguá qué quedó a medias

```powershell
git -C C:\AI_WORKFLOW_V2 status --porcelain; git -C C:\AI_WORKFLOW_V2 log --oneline -5
```

- **Hay cambios sin commitear** → decidí si valen. Si sí, verificalos y
  commitealos. Si son basura de un intento a medias, revertilos. **No los
  dejes ahí**: la próxima caída no va a saber si eran buenos.
- **El árbol está limpio y el último commit corresponde al paso en curso** →
  probablemente alcanzó a commitear y no a marcar el plan. Marcalo hecho con
  ese hash y seguí con el siguiente.

### 3. Confirmá que el piso está sano antes de construir encima

Si el HARNESS (smoke test del entorno) ya existe, corrélo antes de seguir. Si
está rojo, **eso es lo primero**, antes que cualquier paso nuevo. Si todavía
no existe, construirlo es de las primeras tareas del plan.

### 4. Anotá la caída y seguí

Agregá una línea en `PLAN_SESIONES.md` (o en el handoff si aún no existe el
plan): qué paso se cortó y qué se encontró al retomar. Después continuá.

---

## Reglas del loop (siguen vigentes)

- Prohibido `AskUserQuestion`. Decisiones del fundador → lista de PENDIENTES
  DEL FUNDADOR, y seguí con lo demás.
- Nunca reintentes el mismo comando esperando que la próxima vez pase.
- construí → verificá con canario (rojo Y verde reales) → commiteá → anotá.
- `--no-verify` prohibido. El residuo se ARCHIVA, nunca se borra.

---

## Si te relanzaron varias veces por lo mismo

Mirá `08_REPORTS/WATCHDOG/watchdog.log`. Si el contador va alto y siempre te
cortás en el mismo paso, **el paso es el problema, no la sesión**: partilo en
pedazos más chicos, o marcalo bloqueado con el motivo en PENDIENTES DEL
FUNDADOR y pasá al siguiente.

El watchdog se apaga solo a los 12 relanzamientos.

---

## Cómo apagarlo

- **Pausa:** crear `08_REPORTS/WATCHDOG/STOP.txt`.
- **Desarmar:** borrar `08_REPORTS/WATCHDOG/ARMADO.txt`.
- **Rearmar tras el techo:** borrar `estado.json` y `STOP.txt`.
