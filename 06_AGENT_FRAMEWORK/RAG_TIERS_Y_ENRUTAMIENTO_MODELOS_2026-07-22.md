# RAG por tiers y enrutamiento de modelos — diseño operativo (v1)

Fecha: 2026-07-22  
Estado: diseño v1 con primera integración LAB implementada el 2026-07-23.

> **Decisión permanente (2026-07-23), con datos reales:** el wrapper
> RAG NO es el default para tareas de Q&A acotada sobre documentación
> del framework cuando Claude ya conoce y puede citar los archivos
> exactos a revisar. Medición real de 6 corridas (3 tareas × 2
> condiciones, con RAM liberada): el RAG agregó +107.5% de tiempo
> (+116.6% con arranque de sesión) y +17.3% de tokens, sin mejora de
> calidad — Codex sin RAG ya localiza y cita las fuentes correctas por
> su cuenta. Razón: cuando Claude estructura quirúrgicamente qué
> archivos revisar y arma el prompt completo, consultar el RAG además
> es trabajo redundante, no complementario. Detalle y artefactos:
> `PRUEBA_EFICIENCIA_RAG_2026-07-23.md`.
>
> El wrapper queda construido, probado y disponible para el caso
> distinto donde sí podría aportar: corpus muy grande, pregunta
> ambigua, o contexto que Claude no tiene curado de antemano — no se
> descarta, se restringe su uso por defecto.

> **Implementación LAB inicial:** [`invoke_with_rag_context.ps1`](./invoke_with_rag_context.ps1)
> consulta el endpoint local `/query`, inyecta `answer` y `sources` como contexto
> orientativo no certificado e invoca Codex u OpenCode. Desde 2026-07-23 explicita
> el ciclo ReAct mínimo `Thought → Action → Observation` en un `.react.jsonl` por
> invocación: declara el motivo de la consulta, registra `/query` y su respuesta;
> sin respuesta, fuentes o confianza suficiente, registra la abstención y pasa sólo
> el prompt original. La primera prueba real fue B13.5. ACL, DLP y citas verificadas
> permanecen fuera de este tier.

## Cambios v1 respecto de v0

Esta versión conserva el razonamiento y las propuestas de v0, y aplica los cuatro ajustes aprobados a partir del [piloto retroactivo de la matriz v0](./PILOTO_MATRIZ_V0_2026-07-22.md): (1) se vuelve obligatoria la telemetría mínima antes de que exista una ruta elegible y la ausencia de registro bloquea promoción/certificación; (2) se separa el harness mecánico de evaluación, que puede ser LAB/determinista, de la auditoría crítica y la conclusión de certificación, que siempre son BLINDADO; (3) todo conector que alcance datos personales requiere BLINDADO incluso en lectura; y (4) `certified` pasa a ser un estado verificable mediante evidencia válida, no una etiqueta prevista.

## Dictamen

No conviene elegir entre un RAG siempre frágil y uno siempre blindado. El contexto central debe ser único y gobernado, pero la ruta de consulta puede tener **perfiles explícitos**: se acepta fricción sólo cuando el riesgo lo justifica. La misma regla aplica a modelos: la asignación debe ser una decisión declarada, revisable y basada en capacidad certificada, no una suposición de que todos hacen lo mismo.

La recomendación inicial es usar tres tiers: **LAB**, **EVIDENCIA** y **BLINDADO**. Para enrutar modelos, empezar con una matriz declarativa y un registro de capacidades/mediciones; no desplegar todavía un gateway propio ni forzar que Claude Code pase por una API externa.

## 1. Tiers de RAG

El punto de partida es el RAG real de laboratorio: búsqueda densa multilingüe + BM25 local + RRF + cross-encoder, chunking estructural y respuesta extractiva. Hoy no hay generación LLM dentro de `query`; por ello el riesgo generativo es menor, pero no desaparecen poisoning, exposición de datos ni falta de trazabilidad. Véase [RAG actual](../11_LAB/rag-comparison/tchasky_rag_system.py) y el [diseño blindado](../08_REPORTS/TECH_RADAR/RAG_BLINDADO_DISENO_2026-07-22.md).

| Tier | Garantías activas | P0/P1/P2 cubiertos | Latencia relativa esperada | Cuándo usarlo | No promete |
|---|---|---|---|---|---|
| **LAB** | Retrieval híbrido actual, reranking, filtros locales de corpus, respuesta extractiva y guardrail de RAM. Manifiesto básico y smoke/regression actual. | Conserva la línea base; no activa controles P0. Puede registrar métricas de latencia sin bloquear. | **1.0×**: referencia más rápida. | Exploración rutinaria del laboratorio, lectura de documentación no sensible, prototipos, iteración y preparación de `TaskBrief`. | ACL/tenant, DLP, cuarentena, citas verificadas por claim, abstención calibrada, audit trail o aislamiento multi-proyecto. No se usa para decisiones de riesgo basadas sólo en su salida. |
| **EVIDENCIA** | Núcleo LAB más contrato `Answer/Claim/Citation`: `chunk_id`, versión, span/quote y procedencia; unión exacta entre claims y fuentes; abstención mínima por falta de soporte, conflicto o cita inválida; evaluación de no-answer y citas. Contenido tratado como datos, no instrucciones. | **P0 de output:** citas verificables y abstención/soporte. **P1 inicial:** golden set externo y controles de conflicto/frescura cuando existan metadatos. | **~1.05–1.25×** si verificación determinista/local; medir p50/p95. Evita por defecto NLI/LLM-as-judge síncrono. | Diseño técnico, auditoría documental, recomendaciones respaldadas, cambios que necesitan evidencia citable y bloqueos técnicos sin datos sensibles ni separación de tenants. | No garantiza autorización por documento, DLP/PII ni cuarentena. Una cita válida prueba el span, no que la política de acceso sea correcta. |
| **BLINDADO** | Gateway con identidad, propósito, allow-list y prefilter obligatorio en dense y sparse; tenant/ACL; clasificación, cuarentena/sanitización, DLP de entrada/salida; catálogo/ledger de procedencia; índice candidate/active y rollback; citas por claim, abstención, conflicto/frescura y auditoría sin texto sensible; suite adversarial y gates. | **Todos los P0** del diseño; **P1** de cadena de custodia, evaluación continua, conflictos, incremental/promoción; **P2** sólo cuando la evaluación lo apruebe (formatos, parent-child, multimodal, query routing). | **~1.2–2×** con políticas y verificadores deterministas cacheados. Un verificador NLI/LLM puede llevarlo a cientos de ms o segundos: es opt-in y se mide, no se presupone. | Incidente, seguridad/PII, datos de varios proyectos o sujetos, decisión irreversible, recomendación `CERTIFIED`, promoción de índice/modelo y todo trabajo que pueda producir una fuga o una acción sensible. | DLP ni detección de inyección perfectos; tampoco sustituye aprobación humana ni decide negocio/producto. |

### Precondición operativa de elegibilidad

Antes de asignar tier, modelo o fallback debe existir un `WorkEvent` inicial con: `rag_tier`, `modelo_id/version`, `surface`, `herramientas/permisos`, `coste_usd` (valor o `null` acompañado de motivo), latencia y resultado/estado esperado. Si cualquiera falta, **no existe ruta elegible**: la tarea se detiene o se completa el registro antes de ejecutar. `no registrado` nunca significa LAB, ni habilita una degradación silenciosa. Un registro incompleto puede conservarse como evidencia histórica, pero bloquea promoción de índice/modelo, recomendación `CERTIFIED` y cualquier certificación.

### Reglas de degradación y precedencia

1. Un tier sólo puede añadir garantías; nunca permite saltar una política requerida por el tipo de dato o la acción posterior. Si hay PII —incluido cualquier conector a Gmail, Drive, Calendar u otra fuente de datos personales, aunque la operación sea read-only—, multi-proyecto, identidad ajena, fuente no confiable o una acción de alto impacto, el mínimo es **BLINDADO**, aunque se pida LAB. Read-only reduce el impacto de modificación, no el riesgo de exposición.
2. Una respuesta obtenida en LAB es una pista. Para convertirla en recomendación `SUPPORTED` o `CERTIFIED`, se reconsulta o verifica en EVIDENCIA/BLINDADO según la clasificación de datos.
3. La precondición de elegibilidad prevalece sobre estas reglas: sin el registro operativo completo no se asigna LAB por defecto ni se habilita fallback, promoción o certificación.
4. La configuración se registra en el `TaskBrief` y en todo `WorkEvent`: `rag_tier`, motivo, corpus/versión, políticas aplicadas, `modelo_id/version`, `surface`, herramientas/permisos, coste, latencia y resultado. Nunca se guarda texto sensible ni stdout crudo.
5. El tier no cambia la precedencia documental: núcleo declarado por el fundador -> ADR/decisión vigente -> evidencia certificada -> aprendizaje confirmado -> recomendación efímera. Tampoco autoriza decisiones de negocio.

## 2. Mecanismo concreto de consulta: «¿qué tier de RAG querés usar?»

La pregunta no debe aparecer antes de cada búsqueda. Se integra a la apertura del `TaskBrief` del [protocolo de recomendación continua](./PROTOCOLO_RECOMENDACION_CONTINUA_2026-07-22.md), después de recuperar contexto mínimo y antes de una consulta RAG material.

### Disparadores

Se pregunta explícitamente al fundador si ocurre cualquiera de estos casos:

- se declara un bloqueo que impide continuar, o se solicita una recomendación/decisión con evidencia;
- el `risk_level` es `high`, hay datos sensibles, dos proyectos/tenants, contenido externo/no confiable, o la salida puede conducir a ejecución, promoción o divulgación;
- el agente detecta que LAB no tiene evidencia suficiente, hay fuentes contradictorias o la respuesta requiere cita verificable;
- se cambia de LAB a una tarea de auditoría, incidente, diseño crítico o certificación.

No se pregunta para exploración rutinaria ya clasificada como LAB ni cuando una regla dura exige BLINDADO: en ese caso se informa el motivo y se usa el mínimo obligatorio. En todos los casos, primero se completa la precondición operativa; sin ella no hay elección ni ruta ejecutable.

### Tarjeta de consulta

```text
El bloqueo afecta [ámbito] y requiere [tipo de evidencia].
¿Qué tier de RAG querés usar?

1. LAB — rápido; retrieval híbrido local; resultado orientativo.
2. EVIDENCIA — citas verificables y abstención; sin ACL/DLP completos.
3. BLINDADO — identidad/ACL/DLP/auditoría y verificación completa; más latencia.

Recomendación: [tier], porque [riesgo concreto].
```

La tarjeta muestra siempre el coste cualitativo y no etiqueta como “seguro” lo que no lo es. Para que la elección sea útil, el `TaskBrief` debe incluir `project`, intención, fase, riesgo, datos previstos, acción posterior y presupuesto de latencia.

### Si no hay respuesta

- Si existe mínimo obligatorio, se aplica **BLINDADO** y se deja constancia: `tier_forced_by_policy` con la regla que lo exigió.
- Si no hay mínimo obligatorio y el trabajo es puramente exploratorio, se continúa en **LAB**, marcado `provisional`; no se convierte el resultado en decisión ni recomendación certificada.
- Si el bloqueo exige una conclusión verificable y sólo LAB está disponible, se **abstiene de concluir**: se entrega la pista y se registra que falta la elección o disponibilidad de EVIDENCIA/BLINDADO. No se infiere consentimiento para pagar más coste/latencia.

## 3. Enrutamiento de tareas a modelos

### Cadena automática ante indisponibilidad de Codex (2026-07-23)

Para tareas del framework se usa `06_AGENT_FRAMEWORK\\invoke_with_fallback.ps1`. Intenta primero el CLI real de **Codex** y, ante `You've hit your usage limit`, timeout, binario ausente o cualquier exit code no cero, continúa automáticamente por OpenCode (`build`) en este orden: GLM-5.2, Mistral Small 4, Nemotron Super, Nemotron Ultra, MiniMax M3 y, al final, Step 3.7 Flash. Cada intento queda en `06_AGENT_FRAMEWORK\\fallback-chain.jsonl`, incluyendo proveedor, modelo, orden, estado, timeout, exit code y archivo de salida.

Uso:

```powershell
powershell -File .\\06_AGENT_FRAMEWORK\\invoke_with_fallback.ps1 -Task 'Tarea concreta' -TaskType codigo
```

| Modelo | Rol constante | Motivo |
|---|---|---|
| GLM-5.2 | Auditor principal + fallback #1 de código | Único "incompleto no roto" en prueba real |
| Mistral Small 4 | Segunda opinión rápida / verificación liviana | 7/7 consistente, rápido |
| Nemotron Super | Tareas de contexto largo | 1M contexto, rápido |
| Nemotron Ultra | Respaldo de Nemotron Super | Mismo patrón, más lento |
| MiniMax M3 | Cola de baja prioridad | 7/7 pero lento (120s) |
| Step 3.7 Flash | Solo planning/generación, nunca código de producción sin revisión extra | Rompió una migración SQL real una vez |
| MiniMax M2.7 / DeepSeek V4 Pro | Fuera de rotación activa | Timeouts / peor score |

Si responde Step 3.7 Flash, el archivo final añade un aviso visible de revisión adicional obligatoria antes de confiar en código de producción. La cadena no entrega autoridad de negocio: conserva las reglas de riesgo, evidencia y revisión de este documento.

### Principio de selección

No se fija un modelo por prestigio. Se clasifica la tarea mediante campos explícitos: `reasoning_depth`, `risk`, `latency_budget`, `cost_budget`, `needs_tools`, `needs_long_context`, `output_contract` y `requires_independent_audit`. Luego se elige entre modelos habilitados en el registro local; sólo se puede afirmar o usar el estado **certified** cuando la ficha identifica versión, alcance, batería/caso válido, grounding requerido, mediciones reproducibles y revisión independiente aprobada para esa clase de tarea. Sin esas evidencias el estado es `provisional` o `disabled`, nunca “certificado” por aspiración, score barato o resultado histórico.

La tabla usa nombres de familias, no promesas sobre una versión concreta. Antes de automatizar, cada fila debe apuntar a una medición reproducible de calidad, tiempo, coste y tool-use. “Fable” no se asume equivalente a Haiku/Sonnet/Opus: hasta que el registro local identifique proveedor, versión y resultados, queda como `experimental` y nunca como única ruta de tareas críticas.

| Tipo de tarea / perfil | Modelo principal | Alternativa / escalamiento | Motivo y límites |
|---|---|---|---|
| Exploración, clasificación, lectura masiva, extracción de metadatos y resúmenes no vinculantes | **Haiku** o el modelo rápido certificado (p. ej., **Fable** sólo si pasa el benchmark local) | Sonnet si hay ambigüedad técnica o baja cobertura; no Opus por defecto. | Prioriza throughput y coste. Muestreo de QA y escalamiento si falla estructura, precisión o cobertura. |
| Borrador rápido de documentación, prompts, plantillas, traducción y reformulación | **Haiku/Fable certificado** | Sonnet para revisión de coherencia o estilo técnico. | Es texto de bajo riesgo; la salida se marca como borrador y no sustituye fuentes/citas. |
| Implementación contenida, debugging normal, síntesis técnica y planificación de varios pasos | **Sonnet** | Opus si hay bloqueo de razonamiento, interacción compleja entre subsistemas o revisión posterior adversarial. | Equilibrio de razonamiento, coste y velocidad. El código real se ejecuta y verifica: el modelo no certifica su propio resultado. |
| Harness de evaluación mecánico (casos repetitivos, fixtures, cortes, formato y recolección de métricas) | **Automatización determinista**; modelo rápido habilitado sólo si el harness lo requiere | Repetir o corregir el harness; no escalar el score a juicio crítico. | Es una actividad **LAB**: mide casos, grounding, coste y latencia. Su salida es evidencia de evaluación, no una certificación de modelo ni una auditoría crítica. |
| Decisión crítica, arquitectura, auditoría profunda, incidente, análisis de contradicciones y revisión independiente | **Opus** | Segundo modelo independiente certificado (Sonnet/GLM-5.2/Nemotron/Kimi según benchmark y sensibilidad); fundador para decisión de negocio. | Se compra razonamiento y análisis de trade-offs, pero se exige EVIDENCIA/BLINDADO, fuentes y verificación. Opus no reemplaza evidencia ni autoridad humana. |
| Auditoría crítica o conclusión de promoción/certificación de un modelo | **Auditor/surface independiente certificado para ese alcance** | Segundo auditor independiente certificado; fundador para decisión de negocio. | Siempre **BLINDADO**, aunque el harness que generó los resultados haya sido LAB/determinista. Exige caso válido, grounding de herramientas cuando aplique, citas verificables, telemetría completa y repetición/revisión independiente; un score o benchmark por sí solo no certifica. |
| Tarea mecánica repetitiva y de bajo riesgo (renombres, inventario, formato, checks simples) | **Haiku/Fable certificado** o automatización determinista | Sonnet sólo si falla el patrón. | Primero usar scripts/validadores; el modelo barato coordina, no inventa complejidad. |
| Investigación o comparación externa con lectura/síntesis, sin ejecutar cambios | **Sonnet** | Opus para síntesis decisional; GLM-5.2, Nemotron o Kimi como segunda opinión si la evaluación local demuestra fortaleza en ese dominio/idioma. | La ruta debe distinguir búsqueda de síntesis. Las fuentes primarias ganan frente a consenso de modelos. |
| Ejecución real con herramientas (shell, repositorio, navegador, conectores) | **El agente/surface que posee las herramientas y permisos**: Claude Code/Codex con Sonnet u Opus según riesgo. | Modelo externo sólo para análisis que se devuelve como evidencia; nunca recibe autoridad implícita sobre herramientas locales. | “Saber razonar” y “poder ejecutar” son capacidades distintas. El router verifica soporte de tools/JSON, aislamiento y política antes de asignar. Si un conector toca Gmail, Drive, Calendar u otra fuente con PII, la ruta es obligatoriamente **BLINDADO**, incluso read-only. |
| Razonamiento sólo texto, sin herramientas ni datos restringidos | Modelo certificado más económico que cumpla profundidad y contexto: Haiku/Fable para simple, Sonnet para medio, Opus para crítico. | Modelos externos ya evaluados pueden competir por esta ruta con una ficha de evaluación comparable. | Es la mejor superficie para comparar GLM-5.2, Nemotron y Kimi vía OpenRouter, porque no se confunden resultados con permisos de ejecución. |
| Fallback por caída, rate limit o presupuesto | Lista declarada por capacidad compatible, nunca “cualquier modelo”. | Degradar sólo dentro de la misma clase de riesgo; si falta capacidad/cita/tools, abstener o escalar. | Un fallback debe conservar requisitos: herramientas, JSON/schema, contexto, residencia de datos y clasificación. |

Anthropic distingue Opus como su modelo más capaz para razonamiento/código complejo y Sonnet como perfil de alto rendimiento/eficiencia; su guía de tool use recomienda modelos más capaces para herramientas complejas y Haiku para herramientas simples. Esto respalda la **dirección** de la matriz, no certifica la calidad para el corpus local. [Anthropic: familias Claude](https://docs.anthropic.com/en/docs/welcome), [guía de tool use](https://docs.anthropic.com/ko/docs/agents-and-tools/tool-use/implement-tool-use). El diferencial de coste también es significativo y debe medirse con tokens reales, no sólo por etiqueta de modelo. [Precios Anthropic](https://docs.anthropic.com/en/docs/about-claude/pricing).

### Registro declarativo mínimo (diseño, no código)

Una única ficha versionada por modelo/proveedor contiene:

```yaml
model_ref: anthropic/claude-sonnet/<version>
status: certified | provisional | disabled
allowed_data_classes: [internal]
capabilities: [text, code, tools, json_schema]
task_classes: [implementation, research_synthesis]
max_risk: medium
latency_budget_class: medium
evidence_refs: [benchmark-id, certification-report]
certification_basis: [valid-case-id, reproducible-measurement-id, independent-review-id]
certified_task_scope: [task-class]
fallbacks: [approved-compatible-model-ref]
review_after: 2026-10-22
```

GLM-5.2, Nemotron y Kimi no obtienen una clase por su nombre ni por estar disponibles en OpenRouter: se incorporan con su identificador/versionado, condiciones del proveedor, soporte real de parámetros y resultados comparables del laboratorio. OpenRouter expone metadatos de capacidades, incluidos `tools`, JSON/schema y razonamiento, y permite filtrar por coste, throughput y latencia; éstos son insumos útiles, pero no sustituyen la certificación local. El estado `certified` requiere además los campos de `certification_basis`, alcance explícito y telemetría completa del `WorkEvent`; de lo contrario el modelo queda provisional o deshabilitado. [OpenRouter Models API](https://openrouter.ai/docs/guides/overview/models).

## 4. ¿Plataforma/gateway o reglas declarativas?

### Opción A — Reglas declarativas dentro del flujo actual (recomendada ahora)

Se mantiene Claude Code/Codex como superficies de ejecución y el `TaskBrief` como punto de clasificación. Una tabla versionada de modelos/tareas define principal, fallback, tier de RAG mínimo y evidencia requerida. La elección se registra en `WorkEvent`; las excepciones se revisan. Para APIs externas ya usadas, se invoca el modelo elegido directamente o por OpenRouter **sólo** en tareas texto/sin privilegios que ya lo permitan.

**Beneficio:** cero servicio nuevo, cero proxy siempre activo, una sola superficie de permisos, depuración simple y adopción inmediata. Permite capturar datos de coste/latencia/éxito antes de convertir suposiciones en automatización. **Costo:** la selección no es centralmente forzada, la telemetría es inicialmente manual/fragmentada y los fallbacks no son automáticos.

Esta opción usa capacidades existentes: Claude Code ya permite seleccionar modelo por sesión/ejecución y automatizar salidas JSON en modo print; no requiere montar una plataforma para comenzar. [CLI de Claude Code](https://docs.anthropic.com/en/docs/claude-code/cli-usage).

### Opción B — Gateway/router real

Un proxy central recibe la tarea clasificada, consulta el registro, escoge proveedor/modelo, aplica budgets, telemetría y fallbacks, y llama APIs de Anthropic/OpenRouter/u otros. Un producto como LiteLLM ofrece SDK/router directo y, opcionalmente, un proxy con autenticación, costes y límites; OpenRouter ya resuelve routing de proveedores/fallbacks y publica señales de precio, latencia y throughput. [LiteLLM](https://docs.litellm.ai/), [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks).

**Beneficio:** política y observabilidad centralizadas, fallback automático, budgets por proyecto y una API uniforme entre modelos. **Costo real:** nuevo secreto/endpoint/operación, mapeo imperfecto de capacidades entre proveedores, dependencia adicional, gestión de datos/residencia y riesgo de que el proxy se vuelva el punto de fallo. Además, no hace que una tarea externa tenga acceso seguro a las herramientas de Claude Code/Codex; un gateway de inferencia y una superficie de ejecución son responsabilidades distintas. Anthropic documenta gateways para Claude Code como una integración de proxy, no como requisito para usarlo. [Claude Code LLM gateways](https://docs.anthropic.com/en/docs/claude-code/llm-gateway).

### Recomendación clara

**Empezar con Opción A.** Es suficiente para obtener la mayor parte del valor: decidir conscientemente entre modelos, controlar tiers RAG y registrar resultados. Sólo evaluar Opción B después de un piloto que demuestre simultáneamente:

1. llamadas API recurrentes a al menos dos proveedores para tareas elegibles;
2. volumen de selección/fallback que vuelva inaceptable la coordinación declarativa;
3. necesidad comprobada de budget/telemetría centralizados; y
4. un diseño aprobado de secretos, clasificación de datos, retención y operación.

Un router automático no decide qué es “mejor” universalmente. OpenRouter, por ejemplo, puede ordenar por precio, throughput o latencia y hacer fallback de proveedor; eso resuelve disponibilidad/optimización de endpoint, no la política local de riesgo, herramientas, evidencia y autoridad. [OpenRouter routing](https://openrouter.ai/docs/guides/routing/provider-selection).

## 5. Conexión entre tiers, modelos y contexto central

```text
TaskBrief
  -> clasificar riesgo, datos, acción, profundidad y presupuesto
  -> verificar precondición: tier, modelo/version, surface, permisos, coste, latencia y resultado
  -> imponer tier RAG mínimo + modelo/surface elegible
  -> recuperar sólo el contexto permitido
  -> ejecutar o razonar con el modelo seleccionado
  -> verificar según tier; abstener/escalar si falta evidencia
  -> WorkEvent completo con tier, modelo/version, surface, permisos, coste/latencia y resultado
  -> LearningRecord sólo tras evidencia y revisión
```

El contexto central sigue siendo una fuente gobernada, no una excusa para aplicar el máximo control a toda iteración. LAB favorece velocidad para descubrir; EVIDENCIA vuelve rastreable lo que se quiere sostener; BLINDADO protege cuando la consecuencia exige frontera de datos y auditoría. El modelo se adapta a la tarea, mientras que las decisiones significativas continúan escalando al fundador y los resultados se verifican de forma independiente.

## 6. Plan por fases — sin código todavía

| Fase | Acción | Salida/criterio |
|---|---|---|
| 0. Acordar política | Fundador aprueba nombres de tiers, reglas duras de BLINDADO, clases de datos, presupuestos y quién puede elevar una conclusión. | Contrato corto de decisión; no hay plataforma ni cambio de RAG. |
| 1. Matriz y piloto manual | Crear la ficha declarativa de capacidades para Claude y los modelos externos ya evaluados; clasificar 10–20 tareas reales y registrar obligatoriamente tier, modelo/version, surface, herramientas/permisos, coste o motivo de `null`, latencia, resultado, reintentos y utilidad. | Línea base comparativa; sin registro completo no hay promoción/certificación. Fable y externos sólo quedan `certified` si satisfacen la base verificable; de otro modo quedan provisionales/deshabilitados. |
| 2. EVIDENCIA primero | Diseñar contratos de cita/abstención y dataset externo de regresión para habilitar EVIDENCIA sin añadir ACL/DLP completos. | Métricas de citas, no-answer, p50/p95 y costo incremental. |
| 3. Calibrar reglas | Revisar fallos de routing y consultas de tier; ajustar sólo reglas respaldadas por `WorkEvent`/evaluación. | Menos escalamiento inútil y sin rutas críticas degradadas. |
| 4. Decidir gateway con evidencia | Comparar coste operativo del proxy contra el coste de selección manual y llamadas multi-proveedor. | Decisión ADR: mantener reglas o pilotar gateway mínimo aislado. |
| 5. BLINDADO cuando lo requiera el caso | Implementar por fases los P0/P1 del diseño blindado sólo si el caso habilita multi-proyecto, datos sensibles, acciones o promoción. | Controles medidos, no una plataforma pesada anticipada. |

## Primer paso propuesto

Crear y aprobar, fuera de Tchasky, una **matriz declarativa v0** de `tipo de tarea -> tier mínimo -> modelo/surface -> fallback -> evidencia requerida`, y pilotarla en diez tareas de laboratorio. El primer dato que debe capturarse no es una nueva API: es si la selección redujo tiempo/coste sin degradar la verificación ni forzar escalamiento incorrecto.
