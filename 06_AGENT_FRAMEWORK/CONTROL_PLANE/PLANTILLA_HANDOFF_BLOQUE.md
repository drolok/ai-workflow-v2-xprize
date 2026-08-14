# Plantilla de handoff por bloque — el modelo de dos IAs

**Qué corrige esto.** El protocolo two-key describe el *ciclo* (task → review →
merge → done). Lo que faltaba era la forma de **repartir el trabajo**: hasta
ahora se escribían prompts para "una sesión que hace cosas", cuando V2 se diseñó
para **dos ingenieros que se validan entre sí**.

Un bloque no se despacha con un prompt. Se despacha con **dos handoffs que
encajan**, uno por IA, derivados del mismo bloque.

---

## La unidad de trabajo: el bloque

Un **bloque** es un pedazo de trabajo con:

- **un objetivo compartido** que las dos IAs entienden igual,
- **un task en el ledger** con `owner` y `reviewer` declarados (nunca la misma),
- **dos handoffs**, uno por rol, que no se contradicen porque salen del mismo
  encabezado,
- **una definición de terminado** que el reviewer puede verificar sin preguntarle
  nada al owner.

Cada bloque se trabaja en **una sola sesión de un solo prompt por IA**. Las
sesiones son desechables; el bloque queda en el ledger.

---

## Cómo se reparte

**No hay un rol fijo.** Se elige por bloque, según qué convenga:

| Tipo de bloque | Owner | Reviewer | Por qué |
|---|---|---|---|
| Implementación mecánica con spec cerrada | Codex | Claude | Codex construye rápido; Claude audita el diff |
| Diseño, contratos, decisiones de arquitectura | Claude | Codex | Claude escribe la spec; Codex la ataca sin haberla escrito |
| Auditoría de algo ya construido | el que **no** lo construyó | — | La regla de oro: quien construye no valida |

**Lo que nunca cambia:** el que implementa no firma su propio `done`.

---

## Estructura de un bloque

### Parte A — Encabezado compartido

Va idéntico en los dos handoffs. Si difiere, las IAs están trabajando sobre
cosas distintas y nadie lo va a notar hasta el merge.

```
BLOQUE: <nombre corto>
TASK:   TASK-N
OWNER:    <codex|claude>   worktree: C:\AI_WORKFLOW_V2_WORKTREES\<task>
REVIEWER: <el otro>

OBJETIVO
  <una frase. Si necesita dos, probablemente son dos bloques.>

DEFINICIÓN DE TERMINADO
  <lo que el reviewer va a exigir, escrito ANTES de empezar>
  - criterio 1, con cómo se verifica
  - criterio 2, con cómo se verifica
  - si el riesgo es HIGH: el criterio de canario es obligatorio

FUERA DE ALCANCE
  <lo que este bloque NO toca, para que nadie lo amplíe por su cuenta>
```

### Parte B — Handoff del OWNER

```
Eres el OWNER del TASK-N. Implementas, no firmas.

TU AISLAMIENTO
  Trabajas en tu worktree y solo ahí. El árbol principal no se toca hasta el
  merge, y el merge no lo haces tú.
  NO escribas en .ai/events/** — el ledger principal no es tuyo. El orquestador
  registra tu progreso; tú no fabricas tu propia historia.

LO QUE TIENES QUE ENTREGAR
  El diff. No un reporte del diff: el diff.
  Por cada criterio de la definición de terminado, el comando y su salida.
  Y el ROJO: la prueba de que tu verificación puede fallar. Un verde sin su
  rojo no cuenta como entregado.

LO QUE DEBES DECIR SI PASA
  - lo que intentaste y no funcionó, y por qué lo descartaste
  - lo que no pudiste verificar, dicho como tal
  - si el alcance se te quedó corto o largo
  Esto no es contra ti. El reviewer lo va a encontrar igual, y encontrarlo él
  cuesta una ronda más.

CUANDO TERMINES
  Emites el evento de review y paras. NO mergeas. NO firmas el done.
```

### Parte C — Handoff del REVIEWER

```
Eres el REVIEWER del TASK-N. Auditas el DIFF, no el reporte.

LA REGLA QUE JUSTIFICA TU EXISTENCIA
  Un informe convincente no es evidencia, ni siquiera cuando lo escribió alguien
  que trabajó bien. Tu trabajo es ir a mirar.

QUÉ EXIGES, POR CADA CRITERIO
  1. el comando
  2. la salida pegada
  3. el rojo que prueba que el detector puede fallar
  Falta una de las tres → RECHAZADO. No "aprobado con observaciones".

QUÉ VERIFICAS POR TU CUENTA, SIN CREERLE
  - corres los canarios tú mismo, no lees los del owner
  - recalculas los números que el reporte afirma
  - si el owner dice "no existe" o "está roto", lo compruebas
  Un hallazgo que solo existe en el reporte del owner no está verificado.

CUANDO APRUEBAS
  Emites APROBADO, corre la compuerta de merge, y FIRMAS TÚ el done.
  Si la compuerta no da verde, no hay merge por más que hayas aprobado.

CUANDO RECHAZAS
  Los hallazgos concretos, con el comando que los demuestra. El owner los
  arregla y vuelve — y en la segunda ronda usas RESUME del hilo, no le vuelvas
  a pagar el contexto entero.
```

---

## Las dos reglas que aplican a los dos roles

**1. El handoff se construye DURANTE, no al final.** Cada vez que cierras algo,
descubres algo o descartas un camino, lo agregas y lo commiteas en ese momento.
Un handoff escrito al cierre pierde lo que más vale: lo que intentaste y no
funcionó. Eso ya no está en tu cabeza tres horas después.

Se verifica solo: `git log -- <ruta del handoff>`. Un solo commit al final
significa que se perdió el proceso, aunque el resultado esté bien.

**2. Al cerrar, la skill `auditor-de-sesion`.** Contra los objetivos declarados
al empezar. Owner y reviewer la corren cada uno sobre lo suyo.

---

## El error que esta plantilla existe para evitar

Durante los primeros días de V2 se escribieron prompts que hacían todo: una
sesión construía, verificaba y firmaba. Funcionó, y produjo trabajo real — pero
**cada vez que apareció un error de fondo, lo encontró alguien distinto del que
lo había cometido**, nunca el autor revisándose a sí mismo.

Esa observación no es una anécdota: es la razón de que `owner != reviewer` esté
forzado en código y no dejado a la buena voluntad.
