# Control Plane — Contratos v1 (agnostic layer)

**Para:** la sesión que construya esto (Fable).
**Autor:** Claude (Engineer A). Fase 0 en paralelo por Codex (Engineer B).
**Fecha:** 2026-08-10.

Esta es la parte de la arquitectura que **no puede depender de Claude, de Codex
ni de ningún IDE** (§36 del documento del fundador). Si estos contratos están
bien, mañana se agrega un modelo o un agente nuevo sin reconstruir nada.

---

## 0. La regla que gobierna todo lo demás

> **Ningún artefacto del Control Plane puede estar vivo sin una forma de
> detectar que está viejo.**

No es una preferencia de estilo. En la semana previa a escribir esto, tres
artefactos de este mismo proyecto mintieron con autoridad:

| Artefacto | Qué decía | Qué era |
|---|---|---|
| `apps/api/openapi.json` | 252 operaciones documentadas | 32. Congelado una ronda entera de trabajo. |
| `AUDITORIA_PARIDAD_WEB_MOBILE_2026-08-03.md` | mobile sin paridad, 8 gaps | los 8 cerrados |
| Criterio de aceptación C4 | ✅ cumple | no se cumplía |

Los tres eran documentos convincentes, bien escritos y **falsos**. El Control
Plane que estamos construyendo agrega ~8 registries más y un `CURRENT_STATE`.
Sin esta regla, estamos fabricando ocho mentiras nuevas con mejor tipografía.

**Consecuencias de diseño, no negociables:**

1. **Todo lo generado se genera, nunca se edita a mano.** Si un humano o un
   agente puede editar `SKILLS.json`, va a divergir del disco.
2. **Todo generado lleva `_meta`** con `generated_at`, `generator`,
   `generator_hash`, `inputs_hash`, `item_count`.
3. **Todo generador tiene un canario probado**: se le planta un cambio, se
   verifica que lo detecta, se saca, se verifica que desaparece. Sin ese par
   verde/rojo, el generador no se acepta.
4. **Todo dato lleva su procedencia y su frescura** (§44): `source`,
   `verified_at`, `freshness` ∈ `live | derived | historical`.
5. Un artefacto sin `_meta` fresco **se trata como ausente**, no como verdadero.

---

## 1. Formatos: una desviación deliberada del documento

El documento del fundador usa YAML en todos lados. Propongo:

| Qué | Formato | Por qué |
|---|---|---|
| Estado **generado** (registries, `CURRENT_STATE`, manifests) | **JSON** | Cero dependencias en Python/Node (YAML no está en stdlib), diffs exactos, y determinismo trivial con `sort_keys=True`. Con 6.470 documentos el generador corre seguido: no puede depender de instalar nada. |
| Contratos **escritos a mano** (task contracts, constitución) | **YAML** | Los escriben y leen agentes y el fundador. La legibilidad gana. |
| Ledger de eventos | **JSONL** | Append-only, una línea por evento, sin releer el archivo para escribir. |

**Es una desviación consciente del `.yaml` de tu spec y este es el motivo.**
Si preferís YAML uniforme, se hace — pero entonces el generador necesita un
emisor de YAML propio y hay que probarlo, porque un YAML mal emitido rompe en
silencio.

---

## 2. Los cinco contratos que importan

Todo lo demás se puede derivar de estos. Los otros registries (§13-§20) son
**generados** y su forma la fija el generador, no un contrato humano.

### 2.1 TASK CONTRACT — `.ai/tasks/TASK-<n>.yaml`

Es el que elimina el *"creo que estabas haciendo tal cosa"* (§24).

```yaml
id: TASK-481
title: eliminar capturas de pago duplicadas
objective: >
  Una sola captura por contrato aunque el PSP reintente el webhook.
reason:
  incident: INC-102

owner: codex          # quién implementa
reviewer: claude      # quién valida — NUNCA el mismo
created_by: claude
created_at: 2026-08-10T04:12:00Z

scope:
  allowed:
    - apps/api/src/payments/**
    - packages/shared/payments/**
  forbidden:
    - apps/api/src/auth/**
    - "**/lending-schema/**"

worktree: <HOME>/wt-task-481
branch: fix/task-481-payment-race
locked_files:
  - apps/api/src/services/paymentCapture.ts

acceptance:
  - id: A1
    criterio: dos webhooks idénticos producen una sola captura
    verificacion: test de integración con doble entrega
  - id: A2
    criterio: el saldo del Pro no cambia dos veces
    verificacion: aserción contra la BASE, no contra el código HTTP
  - id: A3
    criterio: canario en rojo
    verificacion: >
      quitar el guard y demostrar que A1 falla. Sin ver el rojo, A1 no
      está verificado.

risk: HIGH
required_validation: [unit, integration, reviewer, gate]
status: implementing   # proposed|accepted|implementing|review|fixing|done|blocked
```

**Reglas que el sistema debe hacer cumplir, no solo documentar:**

- `owner != reviewer`. Siempre. Es el Two-Key del §3.
- Toda acceptance de riesgo `HIGH` lleva un criterio de **canario**. Esta
  sesión encontró cuatro suites que pasaban en verde con el dinero roto; la
  única defensa que funcionó fue exigir el rojo.
- `locked_files` es un **lease**: si otro agente quiere tocar uno, el sistema
  responde quién lo tiene y desde cuándo. No hace falta un lock real del SO —
  alcanza con que sea consultable y que la violación quede en el ledger.

### 2.2 EVENT — `.ai/events/EVENTS.jsonl`

La columna vertebral (§29). Append-only. **Es el único artefacto que no puede
mentir, porque no se reescribe.**

```json
{"ts":"2026-08-10T04:12:00Z","type":"TASK_CREATED","actor":"claude","task":"TASK-481","payload":{"risk":"HIGH"}}
{"ts":"2026-08-10T04:31:22Z","type":"TEST_FAILED","actor":"codex","task":"TASK-481","payload":{"suite":"b1_7","failed":3}}
{"ts":"2026-08-10T05:02:10Z","type":"REVIEW_FINDING","actor":"claude","task":"TASK-481","payload":{"severity":"high","file":"paymentCapture.ts","line":214}}
```

Campos obligatorios: `ts` (UTC ISO), `type`, `actor`. Todo lo demás en
`payload`. **Un tipo nuevo no rompe a los lectores viejos** — esa es la razón
de tener `payload` libre y no un esquema por tipo.

`CURRENT_STATE` se **deriva** del ledger más las consultas en vivo. No se
escribe a mano jamás.

### 2.3 HANDOFF — `.ai/handoffs/<id>.yaml`

Universal (§49): sirve para Claude→Claude, Codex→Claude, OpenCode→Codex, etc.

```yaml
id: HO-2026-08-10-01
from: {agent: claude, session: sess-782}
to: {agent: fable, session: null}
created_at: 2026-08-10T04:40:00Z

state_ref: .ai/generated/CURRENT_STATE.json   # no se copia el estado: se apunta
open_tasks: [TASK-481, TASK-482]
blocked: []
decisions_pending_human: [D15, D16]

what_i_verified:
  - claim: el gate corre 148 archivos de API
    evidence: "gate completo, exit 0, 2026-08-10T03:55Z"
what_i_did_not_verify:
  - claim: la boleta sale con datos del receptor
    why: exige un cobro real; cuelga de D1

next_action: implementar la válvula de 72h de LOGISTICS
```

Las dos secciones `what_i_verified` / `what_i_did_not_verify` son obligatorias.
**Un handoff que no distingue lo comprobado de lo asumido es cómo nace el
próximo C4.**

### 2.4 AGENT STATUS — `.ai/state/agents.json` (generado)

Responde `agent_status()` del §26.

```json
{
  "_meta": {"generated_at":"...","generator":"scan_agent_status.py","freshness":"live"},
  "agents": {
    "claude": {"task":"TASK-482","role":"reviewer","status":"reviewing","branch":"review/task-482","heartbeat":"2026-08-10T04:38:11Z"},
    "codex":  {"task":"TASK-481","role":"implementer","status":"testing","branch":"fix/task-481","heartbeat":"2026-08-10T04:37:02Z"}
  }
}
```

`heartbeat` es lo que distingue *trabajando* de *muerto*. El watchdog del
proyecto ya usa exactamente ese mecanismo y funciona: lo escribe el hook del
harness, no el modelo, así que una sesión colgada deja de latir sola.

### 2.5 CONTEXT BUNDLE — salida de `context_compile(task, agent)`

Lo que recibe un agente al arrancar (§23, §47). **Contrato de la salida, no de
cómo se arma:** así el compilador puede evolucionar sin romper a los agentes.

```json
{
  "_meta": {"task":"TASK-481","agent":"codex","compiled_at":"...","budget_tokens":40000},
  "l0_constitution": ["..."],
  "l1_state":        {"...": "..."},
  "l2_task":         {"...": "..."},
  "l3_documents":    [{"path":"...","why":"rag score 0.82","excerpt":"..."}],
  "l4_graph":        [{"from":"paymentCapture","edge":"CALLS","to":"culqiClient"}],
  "l5_history":      [{"commit":"abc123","why":"tocó paymentCapture.ts"}],
  "l6_live":         [{"source":"railway","value":"deploy X","verified_at":"..."}],
  "omitted":         [{"layer":"l3","count":214,"reason":"budget"}]
}
```

**`omitted` es obligatorio.** Un bundle que no dice qué dejó afuera hace que el
agente crea que vio todo. Es la versión de contexto del mismo error que el
informe de auditoría que se lee como completo.

---

## 3. Qué construir primero — y qué NO

Tu documento tiene 10 fases. La sesión de Fable **no debe intentarlas todas**.
Tu propio §41 (*cheapest reliable executor*) y §51 dicen construir la columna
vertebral primero, y vos mismo escribiste que la Fase 2 "ya debería darte una
mejora enorme".

### Alcance de la primera sesión de Fable

| Fase | Qué | Por qué entra |
|---|---|---|
| **0** | Registries generados | Ya en curso por Codex. Es el piso de todo. |
| **1** | Ledger de eventos + `CURRENT_STATE` derivado + task system + handoff + blackboard + agent status | Es la "shared reality". Sin esto, las fases siguientes no tienen dónde apoyarse. |
| **2** | Protocolo Claude↔Codex: ownership, worktrees, leases, contratos, checkpoints, merge | **Es la fase que cambia el comportamiento hoy.** Todo lo demás es infraestructura para después. |

### Lo que NO entra, y el motivo

- **Fase 3 (Context Fabric) y 4 (MCP Fabric):** valen mucho, pero necesitan que
  las Fases 0-2 estén asentadas y usadas de verdad. Construir el compilador de
  contexto antes de tener eventos reales que compilar es adivinar.
- **Fase 6 (Model Router) y 10 (self-improving):** el router necesita métricas
  para enrutar. Sin el ledger acumulado, enrutaría por corazonada — que es
  exactamente lo que tenemos hoy.
- **Fase 9 (Dashboard):** es una vista. Se construye cuando haya algo real que
  ver; hacerlo antes fija la forma de datos que todavía no existen.

**Umbral de upgrade escrito** (tu criterio de siempre): la Fase 3 arranca
cuando el ledger tenga **≥200 eventos reales de trabajo** y el task system haya
cerrado **≥10 tareas** con el protocolo de dos llaves. Antes de eso, no hay
señal para compilar.

---

## 4. Lo que este diseño rechaza a propósito

- **No creo un tercer líder.** OpenCode queda como gateway de especialistas
  (tu §39), no como L1. Tres líderes es la receta del *multi-agent theater*
  que vos mismo descartás en §41.
- **No pongo a los agentes a hablar libremente entre sí.** Toda comunicación
  Claude↔Codex pasa por el ledger y los contratos. Un mensaje libre no se puede
  auditar seis meses después.
- **No sincronizo Obsidian automáticamente en las dos direcciones.** Máquina →
  Obsidian sí (§10). Obsidian → estado operacional **no**: es la puerta por la
  que un documento viejo se convierte en "realidad", que es el problema que
  estamos resolviendo.
- **No indexo los 6.470 `.md` de entrada.** El RAG de la Fase 3 arranca por un
  subconjunto declarado y crece con evidencia de uso. Indexar todo garantiza
  que el ruido entre al contexto con la misma autoridad que la señal.

---

## 5. Lo que Fable debe demostrar antes de decir "terminado"

No alcanza con que exista la estructura. Por cada pieza:

1. **El canario.** Plantar el cambio, verlo detectado, sacarlo, verlo
   desaparecer. Con la salida real pegada en el reporte.
2. **Determinismo.** Dos corridas seguidas, `diff` vacío.
3. **Una tarea real de punta a punta**: crear un `TASK`, que un agente la tome,
   que el otro la revise, que los eventos queden en el ledger, y que
   `CURRENT_STATE` derivado refleje el resultado sin que nadie lo escriba a
   mano.
4. **Lo que NO funciona**, dicho explícitamente. Un reporte que solo tiene
   verdes es el reporte que ya nos mintió tres veces.
