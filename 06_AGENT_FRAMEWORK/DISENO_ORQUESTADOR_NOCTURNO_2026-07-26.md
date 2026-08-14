# Diseño: orquestador nocturno adaptativo con redundancia

**Estado: SOLO DISEÑO — nada de esto está implementado.** Documento de
trabajo, desarrollado en conjunto por Claude (síntesis), Codex y
Gemini (consultados por separado, mismo problema, preguntas distintas).
Requiere visto bueno del fundador antes de construir una sola línea.

## 1. Idea central

Un proceso liviano y determinista (no un LLM) decide, cada 30-60
segundos, qué tarea de la cola le corresponde a qué IA, según:
salud de la máquina (RAM/CPU), estado de salud de cada IA (tier de
confianza), y el nivel de riesgo/complejidad declarado de la tarea.
Claude sigue siendo el único que audita evidencia real y autoriza
integrar — el orquestador nunca decide "esto ya está bien", solo
decide "quién lo intenta ahora".

**Decisión de arquitectura clave (recomendación unánime de Codex,
adoptada):** el loop de decisión NO debe ser Claude despertando cada
minuto vía `ScheduleWakeup` — eso gasta tokens en decisiones mecánicas
y es fràgil bajo presión de RAM. Debe ser un script standalone
(Python), barato, con estado explícito en disco. Claude/yo solo
entramos para: auditar resultados, resolver escalaciones ambiguas, y
autorizar cualquier integración de código financiero.

## 2. Capas (sobre lo que ya existe, no lo reemplaza)

```
┌─────────────────────────────────────────────┐
│  SCHEDULER (nuevo, Python, tick 30-60s)      │  ← decide QUIÉN hace QUÉ
├─────────────────────────────────────────────┤
│  bridge_queue.py (ya existe)                 │  ← transporte de tareas
│  host_runner.py /run/enqueue-task (ya existe)│  ← disparo desde n8n
├─────────────────────────────────────────────┤
│  Codex | OpenCode | Gemini | Antigravity     │  ← ejecutores
├─────────────────────────────────────────────┤
│  Claude — auditor, única autoridad de merge  │
└─────────────────────────────────────────────┘
```

## 3. Métricas por tarea (síntesis Codex + Gemini)

Registro mínimo por cada tarea despachada, en un JSON/SQLite simple:

| Campo | Qué mide |
|---|---|
| `task_id`, `agent`, `task_type` | Identidad |
| `outcome` | `success` / `infra_fail` (rate limit, crash, cupo) / `quality_fail` (auditoría rechazó) |
| `audit_score` | 1-10 de Claude tras revisar el resultado |
| `retries` | cuántos reintentos necesitó antes de pasar |
| `duration_vs_estimate` | tiempo real / tiempo esperado para ese tipo de tarea |
| `complexity_delta` | ¿el diff ensució el código (más complejidad ciclomática) o no? |

**Punto crítico de ambos: separar fallo de infraestructura (rate limit,
sin cupo, crash del proceso) de fallo de calidad (la auditoría lo
rechazó).** Un rate limit no dice nada sobre si la IA programa bien —
solo la deja temporalmente no disponible. Mezclar ambos en el mismo
score castiga injustamente a una IA por quedarse sin tokens.

## 4. Tiers de confianza por agente (no un score continuo)

Ventana móvil de las últimas 10-20 tareas por agente y por tipo de
tarea → clasificación discreta:

- **Confiable** → puede recibir tareas complejas (cross-module, cerca
  de invariantes, pero NUNCA financieras sin supervisión — ver §6).
- **Normal** → tareas estándar.
- **Degradado** → solo tareas simples/aisladas, mientras se recupera.
- **Suspendido** → no recibe nada hasta revisión humana explícita.

Promoción/degradación por reglas simples (ej. 3 éxitos seguidos sube
un tier, 2 fallos de calidad seguidos baja un tier) — no hace falta
machine learning, es una máquina de estados.

## 5. Clasificación objetiva de "simple" vs "compleja" (Codex)

Nunca por juicio subjetivo de un modelo. Por metadatos declarativos de
la tarea, calculables mecánicamente:

- ¿Toca más de un módulo/capa?
- ¿Modifica schema, migraciones, contratos/API?
- ¿Cambia invariantes financieros (saldos, idempotencia, concurrencia)?
- ¿Requiere una decisión de negocio aún no resuelta?
- ¿Cuántos archivos estima tocar?
- ¿Tiene cobertura de tests existente o necesita integración nueva?
- ¿Es una operación irreversible?

De esto salen campos automáticos: `risk_level`, `touches_financial_invariant`,
`cross_module`, `requires_decision`, `estimated_files`. **Para el
ledger, casi ninguna tarea califica como "simple" salvo tests,
documentación o fixes muy acotados** — coincide con lo que ya vivimos
hoy en la práctica.

## 6. Redundancia real ante fallo (el corazón del pedido del fundador)

Cuando una IA cae a mitad de tarea (sin cupo, crash, rate limit), NO
se le pasa "la conversación" a otra IA — eso pierde contexto y genera
reescritura desde cero. Se transfiere una **"ficha de relevo"**
estructurada y persistida en disco:

- Objetivo y criterio de aceptación exacto de la tarea.
- Estado real del repo: commit base, diff actual, `git status`.
- Qué archivos se tocaron y por qué.
- Qué tests se corrieron y con qué resultado.
- Qué quedó terminado, qué falta, cuál es el siguiente paso.
- Bloqueos/errores/decisiones abiertas.
- Invariantes y restricciones relevantes de esa tarea.

**Regla dura:** el agente que recibe el relevo NUNCA continúa a ciegas.
Primero inspecciona el diff, corre los tests relevantes, y recién ahí
decide: continuar, corregir, o descartar el estado parcial. Si el
estado parcial no pasa tests o toca el núcleo financiero, se marca
"requiere auditoría" — no se reintenta indefinidamente con otro
modelo esperando que "le salga".

**Aislamiento obligatorio:** cada tarea corre en su propio git worktree
o branch — nunca dos agentes escribiendo el mismo working tree al
mismo tiempo (ya lo establecimos hoy con Codex mismo, antes de esta
sesión de diseño).

## 7. Freno automático — el punto no negociable para dinero

Unánime entre Codex y Gemini: **el modo nocturno nunca tiene
autoridad para integrar código del ledger ni resolver ambigüedades
financieras.** Puede preparar branches, implementar, correr tests —
pero cualquier tarea marcada `touches_financial_invariant: true`
**siempre** termina en cola de revisión humana/Claude, nunca se
autointegra, y nunca encadena otra mutación sensible sobre ella
automáticamente.

**Circuit breaker explícito — el sistema se detiene solo y espera al
fundador si ocurre cualquiera de estos:**

- Falla el invariante de "balance cero" (Gemini): la suma total de
  movimientos del ledger antes y después de un cambio debe cuadrar
  exactamente — si no cuadra, **se apaga el orquestador y se bloquea
  git** (nada de commits) hasta revisión presencial.
- Cambios a reglas de contabilización, redondeo, moneda, reversos,
  idempotencia.
- Migraciones/schema relacionados con dinero.
- Dos intentos fallidos de agentes DISTINTOS en la misma tarea (si ni
  Codex ni OpenCode la resuelven bien, no sigue probando con un
  tercero a ciegas — se escala).
- Conflicto de cambios entre tareas paralelas.
- Modificación fuera de la allowlist de archivos declarada para esa
  tarea.
- RAM libre bajo el piso (6GB, ya establecido) o uso sostenido alto.
- Cualquier intento de tocar credenciales, producción, o datos reales
  externos.

## 8. Qué falta definir (abierto, para la próxima conversación)

- Formato exacto del JSON/SQLite de métricas (¿reusar
  `queue/logs/bridge_log.jsonl` que ya existe, o uno nuevo dedicado al
  scheduler?).
- Cómo el scheduler distingue "Antigravity" (GUI+CLI, sin archivo de
  salida) del resto — probablemente Antigravity queda FUERA del loop
  automático y solo se dispara manualmente para casos puntuales (GPT-OSS),
  dado que no tiene forma headless real de reportar estado.
- Umbral exacto de concurrencia (Codex sugirió: 1 tarea pesada +
  1-2 livianas en simultáneo, coherente con lo que ya vimos hoy de
  RAM).
- Quién escribe el primer prototipo del scheduler (¿Codex, en una
  tarea acotada, con este mismo documento como spec?).

## 8.5. Adenda — "Claude a la cabeza" y por qué Antigravity NO puede reemplazarme como auditora

Antigravity propuso (por su cuenta, en su propio chat) que ella misma
asuma automáticamente mi rol de auditora/orquestadora cuando yo me
quede sin cupo de tokens o no responda. Consulté esto con Codex y
Gemini por separado — **veredicto unánime: rechazado**, con esta
resolución:

**"Claude a la cabeza" sí, pero con una precisión importante:**
significa que yo diseño los objetivos de alto nivel y tengo la
autoridad final de auditoría/certificación — **no** que yo despierte
cada minuto a decidir scheduling mecánico (eso lo sigue haciendo el
scheduler barato de la sección 1). Yo me despierto solo ante eventos
significativos: un plan nuevo, una excepción, un conflicto, una
entrega lista para auditar, o una decisión que le corresponde al
fundador.

**Por qué Antigravity NO puede asumir mi rol de auditora automáticamente:**
1. **No existe hoy un mecanismo real que detecte "Claude se quedó sin
   cupo/no responde".** El bridge (`bridge_queue.py`) solo guarda
   `pending`/`in_progress`/timestamps de claim — no hay heartbeats con
   lease, identidad de worker, ni una superficie externa verificable
   de mi salud/sesión/cuota. "Silencio por N minutos" no distingue
   entre tarea larga, app pausada, crash, cuota agotada, o que el
   fundador me pausó a propósito.
2. **Violaría separación de funciones (Gemini):** si el ejecutor se
   autoasigna el rol de auditor, desaparece el contrapeso crítico —
   riesgo real de **validación circular**, donde una IA valida sus
   propios errores como correctos para "mantener la continuidad".
3. El propio `automation_cluster_roles.json` que Antigravity construyó
   reserva la certificación explícitamente a `claude_auditor` — su
   propuesta se contradice con su propio diseño.

**Diseño seguro real para continuidad sin mí (consenso de los 3):**
otra IA puede **seguir ejecutando** tareas ya aprobadas, acotadas e
idempotentes mientras no estoy disponible — pero todo resultado queda
marcado `pending_audit` en un buffer de staging, nunca se autointegra,
nunca se cierra una fase, nunca se decide algo financiero o de
producto sin mi auditoría o la aprobación explícita del fundador. Ante
una tarea nueva, ambigua, o con impacto financiero: el sistema pausa,
no improvisa un reemplazo de autoridad.

## 9. Resumen de una línea

**Loop determinista y barato para operar (scheduler Python) + agentes
para ejecutar + Claude para auditar y ser la única autoridad de merge
— con un circuit breaker duro que apaga todo automáticamente ante
cualquier señal de riesgo financiero real.**
