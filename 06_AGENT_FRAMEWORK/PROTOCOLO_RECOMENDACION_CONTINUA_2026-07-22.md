# Protocolo de recomendación continua, trazable y fiable

Fecha: 2026-07-22  
Estado: diseño propuesto; no implementa código ni modifica el repo de Tchasky.  
Alcance: convertir los avances de trabajo en evidencia reutilizable para recomendaciones oportunas, conectadas al RAG blindado.

## Dictamen

El mecanismo no debe ser un chat que “recuerda todo” ni un generador de consejos. Debe ser un ciclo gobernado: **capturar un evento estructurado al cierre de cada avance material -> consolidar sólo aprendizajes con evidencia -> recuperar candidatos al iniciar una tarea -> emitir como máximo recomendaciones con evidencia, alcance y confianza explícitos -> registrar si ayudaron o no**.

Así el sistema aprende del trabajo real sin confundir memoria, decisión y recomendación. Una recomendación nunca autoriza una acción, no sustituye una decisión del fundador y no se presenta como fiable si sólo es semejanza semántica.

## Relación con lo que ya existe

Esto extiende, no reemplaza, tres precedentes:

- [`Rastros_Patrones_Observados.md`](../01_OBSIDIAN/VAULT_TEMPLATE/10_Personal/Rastros_Patrones_Observados.md) es una nota viva, lateral y explícitamente provisional sobre cómo trabaja el fundador. Sigue siendo humana, cualitativa y con revisión; sus observaciones no se convierten automáticamente en reglas ni recomendaciones técnicas.
- [`Patrones_Prompting_Codex_Claude.md`](../01_OBSIDIAN/VAULT_TEMPLATE/09_Workflow_IA_Local/Patrones_Prompting_Codex_Claude.md) ya registra hallazgos empíricos de invocación y una tabla mínima de métricas. Pasa a ser una fuente de evidencia de tipo `workflow_learning`, no un duplicado que haya que reescribir en cada turno.
- [`RAG_BLINDADO_DISENO_2026-07-22.md`](../08_REPORTS/TECH_RADAR/RAG_BLINDADO_DISENO_2026-07-22.md) ya define catálogo, procedencia, ACL, versiones, retrieval con filtros, citas verificables, abstención y evaluación. Este protocolo usa esas garantías; no crea un segundo RAG informal ni amplía `TOOL_REGISTRY.md` hasta volverlo un log de sesiones.

La distinción central es:

| Activo | Pregunta que responde | Fuente de verdad |
|---|---|---|
| Registro de evento | ¿Qué ocurrió en este avance? | `WorkEvent` inmutable y sus evidencias |
| Lección consolidada | ¿Qué patrón ya se confirmó o se refutó? | `LearningRecord` versionado, aprobado según nivel |
| Decisión | ¿Qué se eligió y por qué? | ADR/decision log canónico |
| Herramienta/repo | ¿Qué está certificado y bajo qué condiciones? | `TOOL_REGISTRY.md` + informe/certificación |
| Recomendación | ¿Qué antecedente aplica a la tarea actual? | salida efímera, citada y auditada |

## Guardrails operativos del wrapper RAG (implementados)

[`invoke_with_rag_context.ps1`](invoke_with_rag_context.ps1) aplica controles mínimos al invocar Codex u OpenCode. Son controles del flujo de invocación, no sustituyen el diseño P0 del RAG blindado.

1. **Calidad de código.** Tras una invocación que termina sin error, si el directorio de trabajo contiene `package.json` o `tsconfig.json`, el wrapper ejecuta `npm run typecheck` cuando existe ese script (o `tsc --noEmit`) y `npm run test` cuando existe script de test. Un fallo registra `QUALITY_GATE_FAILED` y convierte la invocación en fallida; por tanto, una respuesta verbal del modelo no cierra la tarea.
2. **Contenido RAG no ejecutable.** Antes de incorporar `answer` y fuentes al prompt, el wrapper redacta patrones básicos de secretos (`API_KEY`, `SECRET`, contraseñas, JWT y hashes largos) con `[REDACTADO]` y registra el evento sin persistir el valor sensible. El contexto se delimita como `<CONTEXTO_RAG_NO_EJECUTABLE>` y se declara explícitamente evidencia de referencia, nunca instrucciones.
3. **Alcance explícito.** `-AllowedDirectory` es obligatorio. Antes de iniciar Codex u OpenCode se valida que `-RepoRoot` (y `-FrameworkDocsDir` para Codex) estén dentro de esa allowlist. El scope `tchasky` además exige `-AuthorizeTchasky`; cualquier incumplimiento falla con `SCOPE_REJECTED` antes de invocar el agente.

Esto complementa, sin duplicarlo, a [`.claude/hooks/critical_action_guard.ps1`](../.claude/hooks/critical_action_guard.ps1): el hook de Claude Code intercepta patrones de comandos de riesgo, mientras el wrapper gobierna el directorio y la evidencia que reciben Codex/OpenCode.

### Sesiones RAG persistentes

El modo predeterminado sigue siendo por invocación: el wrapper levanta el RAG sólo si no está disponible y lo detiene únicamente si él lo inició. Para un bloque de varias tareas, ejecutar `start_rag_session.ps1` una vez, usar `invoke_with_rag_context.ps1` normalmente y cerrar con `stop_rag_session.ps1`. El wrapper detecta el endpoint ya sano, lo reutiliza y no lo apaga; los scripts de sesión registran PID y fecha de inicio en `11_LAB/rag-comparison/runtime/rag-session.json` para que la parada sea explícita y verificable. No dejar una sesión abierta al finalizar el bloque.

Los ADRs justifican esta separación: capturan una decisión significativa, su contexto, alternativas y consecuencias; juntos forman un decision log, pero no son el historial exhaustivo de toda actividad. [ADR GitHub](https://adr.github.io/) y [MADR](https://adr.github.io/madr/) también admiten registrar evidencia/confianza y cuándo revisar una decisión.

## 1. Qué se captura por turno o avance

### Unidad mínima: `WorkEvent`

No se captura cada frase. Se genera un evento al cerrar un **avance material**: decisión, uso/evaluación de herramienta, experimento, cambio de estado, bloqueo, incidente, verificación, descarte justificado o medición. Un turno sin avance material no produce evento; a lo sumo se agrega al mismo `task_id` como telemetría resumida.

Esquema conceptual, serializable y validable (JSON Schema en una fase posterior):

```yaml
event_id: WE-2026-07-22-0001
occurred_at: 2026-07-22T14:30:00-05:00
project: tchasky
task_id: PAYMENTS-SPIKE-001
event_type: tool_evaluation | decision | experiment | verification | blocker | incident | outcome
scope:
  domains: [payments, webhooks]
  capabilities: [sdk_integration, idempotency, signature_validation]
  technologies: [nodejs, typescript, mercadopago]
intent: "evaluar SDK oficial para pagos y webhooks"
action: "spike aislado con credenciales de prueba"
artifact_refs: [doc-or-file IDs versionados]
evidence:
  - kind: test | benchmark | source | review | command_result
    ref: stable-document-or-artifact-id
    excerpt_or_metric: "144/144 tests; firma y event_id verificados"
    observed_at: 2026-07-22T14:28:00-05:00
outcome: success | partial | failed | blocked | not_applicable
metrics:
  elapsed_minutes: 42
  cost_usd: null
  tokens_read_estimate: null
  ram_min_gb: null
  tests_passed: 144
constraints: ["adaptador propio", "idempotencia persistente", "secret obligatorio"]
supersedes: []
captured_by: codex | claude | human
review_status: auto_captured | reviewed | approved | rejected
```

### Dashboard local de Capa 1 (2026-07-23)

El visor local de eventos normaliza el ciclo ReAct del wrapper (`*.react.jsonl`) y las salidas directas de `codex exec` en `CODEX_CLAUDE_BRIDGE\tasks\outputs` como `WorkEvent` auto-capturados. No almacena prompts completos ni stdout crudo. Iniciar en primer plano:

```powershell
Set-Location C:\AI_WORKFLOW
.\06_AGENT_FRAMEWORK\dashboard\start_dashboard.ps1
```

La URL preferida es `http://127.0.0.1:8765`; si está ocupada, el servidor selecciona e imprime un puerto local libre. El feed usa SSE, por lo cual incorpora nuevos eventos sin refrescar la página. Phoenix (`:6006`) y Langfuse (`:3000`) son enlaces de preparación y no se levantan desde esta Capa 1.

Reglas de calidad:

1. `outcome`, `artifact_refs` y al menos una evidencia son obligatorios salvo un evento `blocker`, que debe llevar la condición reproducible del bloqueo.
2. Las métricas desconocidas quedan `null`, nunca se estiman como hecho.
3. No se guarda prompt completo, secretos, PII ni stdout crudo; se guarda un resumen, IDs y hashes/URLs autorizadas. Respeta la minimización, DLP, ACL y trazabilidad del RAG blindado.
4. El capturador puede proponer etiquetas; la taxonomía y el estado se validan determinísticamente. No se permite que un modelo convierta una anécdota en “hecho certificado”.

### Consolidación: `LearningRecord`

Al final de un hito, o cuando al menos dos eventos comparables apoyan/refutan una misma hipótesis, un revisor crea o actualiza una lección. Es una síntesis corta, no texto libre acumulativo:

```yaml
learning_id: LR-PAYMENTS-001
statement: "Para Tchasky, Mercado Pago SDK Node es candidato directo sólo detrás de un adaptador propio y con webhook firmado e idempotente."
applies_when:
  project: tchasky
  domains: [payments]
  stack: [nodejs, typescript]
evidence_refs: [WE-..., report-version-id, test-artifact-id]
counterexamples_refs: []
status: candidate | confirmed | refuted | superseded
confidence: supported # calculated; not prose
owner: founder-or-designated-reviewer
reviewed_at: 2026-07-22
expires_or_review_after: 2026-10-22
```

Una decisión arquitectónica o de producto que cumpla el umbral de significancia crea además un ADR/entrada del decision log. El `LearningRecord` enlaza al ADR, pero no decide por sí mismo. Esta disciplina coincide con el uso de ADR como registro de decisiones y con un decision log que mantiene alternativas, razonamiento y trabajo requerido, como documenta el [Engineering Playbook de Microsoft](https://microsoft.github.io/code-with-engineering-playbook/design/design-reviews/decision-log/doc/decision-log/).

## 2. Dónde vive y cómo se conecta al RAG blindado

### Fuente canónica y proyecciones

| Capa | Contenido | Escritura | Uso |
|---|---|---|---|
| Ledger de aprendizaje | `WorkEvent` y `LearningRecord` append-only/versionados, con hashes, ACL y referencias | agente propone; validador y revisor promueven | auditoría, patrones y evaluación |
| Decision log/ADR | decisiones significativas y sus consecuencias | humano/fundador según la regla vigente | precedencia y decisiones vinculantes |
| `TOOL_REGISTRY.md` | catálogo legible de herramientas: estado certificado, condiciones y fuente | curado, no automático | descubrimiento humano y fuente indexable |
| Índice `continuous-learning` | proyección de eventos aprobados, lecciones, ADRs, registros de herramientas y certificados | pipeline controlado | retrieval para recomendar |

Es una **colección lógica separada** dentro del mismo `rag-core` y con el mismo `project-pack`, no parte textual de `TOOL_REGISTRY.md`. Recibe los metadatos obligatorios del diseño blindado: `tenant_id`, `project`, ACL, clasificación, `document_version_id`, hash, origen, estado, fecha efectiva, `supersedes`, confianza y retención. Sólo se indexan `reviewed/approved` para recomendaciones fiables; los eventos `auto_captured` pueden entrar a una cola analítica aislada, jamás a la ruta de sugerencia.

El índice principal de conocimiento de Tchasky conserva documentos, arquitectura y evidencias. La colección de aprendizaje permite consultas por estructura (dominio, stack, fase, resultado, coste, estado de certificación) y por semántica. Ambos se recuperan bajo el mismo gateway de autorización, filtros de proyecto/ACL y contrato de citas del RAG blindado.

La separación sigue el principio de memoria jerárquica: usar almacenamiento persistente con recuperación selectiva, en vez de intentar sostener todo el historial en el contexto. [MemGPT](https://arxiv.org/abs/2310.08560) propone precisamente gestión por niveles de memoria para análisis documental y sesiones largas; aquí se adopta el principio, no se adopta el producto ni se concede autonomía al agente.

## 3. Mecanismo de activación y entrega

### Entrada: `TaskBrief`

Al comenzar una tarea de Tchasky, Claude/Codex llena o extrae un brief mínimo antes de actuar:

```yaml
project: tchasky
intent: "implementar integración de pagos"
domains: [payments, webhooks]
capabilities: [sdk_integration, signature_validation, idempotency]
stack: [nodejs, typescript]
task_phase: design | spike | implementation | review | incident
constraints: ["no decisión de proveedor sin fundador"]
risk_level: high
```

No basta con buscar la frase de la tarea. El router normaliza capacidades y consulta en paralelo: (1) herramientas/repos certificados, (2) ADRs/decisiones vigentes, (3) `LearningRecord` confirmado, (4) checklists/controles de seguridad pertinentes y (5) contraejemplos, bloqueos o material supersedido.

### Pipeline de recomendación

```text
TaskBrief -> filtros duros (proyecto, ACL, vigencia, estado) -> retrieval híbrido
          -> agrupar por recomendación/precedente -> verificar evidencia y contradicción
          -> score de aplicabilidad + política anti-ruido -> 0..3 recomendaciones
          -> tarjeta citada + registro de aceptación/resultado
```

Filtros duros antes de similitud: mismo proyecto (salvo evidencia explícitamente reusable), estado `certified`/`confirmed`, no supersedido/revocado, tecnología compatible, evidencia accesible y sin conflicto material no resuelto. El reranker nunca puede resucitar una fuente revocada ni cruzar ACL.

La salida no interrumpe sin motivo: se muestra sólo al inicio de una tarea material, al entrar en un dominio/riesgo nuevo, o si un evento posterior invalida una recomendación activa. En una tarea normal, máximo tres tarjetas; en tareas de alto riesgo, una tarjeta de control obligatorio puede aparecer aunque no haya recomendación de herramienta. Si no supera el umbral, el sistema calla y registra `no_recommendation_due_to_insufficient_evidence`.

Formato de tarjeta:

```text
[SUPPORTED — 0.91] Mercado Pago SDK Node aplica al spike de pagos.
Por qué: mismo dominio/stack; evaluación oficial certificada para Tchasky.
Condiciones: adaptador propio, idempotencia persistente, firma de webhook obligatoria.
Evidencia: TOOL-MP-...; informe ...; pruebas/decisión ...
Límite: candidato técnico; no decide proveedor ni habilita producción.
```

La aceptación, descarte o resultado vuelve como un `WorkEvent`; no como señal implícita. Eso permite medir valor real por recomendación y corregir el catálogo.

La idea de convertir feedback externo en memoria que guía intentos posteriores tiene precedentes experimentales en [Reflexion](https://arxiv.org/abs/2303.11366). La diferencia decisiva aquí es gobernanza: el feedback se estructura, se cita, se revisa y no altera pesos del modelo ni reglas de negocio automáticamente.

## 4. Criterio objetivo de fiabilidad

“Totalmente fiable” no puede significar infalible. Significa que el sistema es **totalmente transparente sobre su nivel de evidencia, límites y abstención**. Toda tarjeta tiene una clase calculada:

| Clase | Requisitos acumulativos | Puede decir |
|---|---|---|
| `CERTIFIED` | fuente canónica vigente + evidencia reproducible/validada + aplicabilidad alta + sin conflicto + owner/revisión | “recomendación certificada para estas condiciones” |
| `SUPPORTED` | al menos una evidencia verificable y pertinente, sin contradicción conocida, pero falta certificación completa o repetición | “antecedente respaldado; validar antes de adoptar” |
| `HYPOTHESIS` | similitud, investigación externa o un solo indicio sin validación local | “posible pista”; por defecto no se muestra proactivamente |
| `ABSTAIN` | evidencia insuficiente, desactualizada, inaccesible o conflictiva | “no recomiendo” |

Score auditable (no un número mágico):

`reliability = 0.30 evidencia + 0.25 aplicabilidad + 0.20 reproducibilidad + 0.15 vigencia + 0.10 consenso - penalizaciones`

Cada componente se deriva de campos observables: número/calidad de artefactos, coincidencia de dominio/stack/fase, prueba o certificación repetible, fecha/`effective_to`, contradicciones y resultado histórico de recomendaciones equivalentes. Se bloquea `CERTIFIED` si falta cualquiera de: cita verificable, estado vigente, evidencia reproducible o revisión requerida. La etiqueta y el desglose se guardan con el `recommendation_id`.

Para comprobar que el motor no sólo recupera texto plausible, se medirá precisión de contexto, recall, faithfulness/grounding y citas válidas, combinando golden set humano y pruebas negativas; [Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) documenta métricas separadas para esas dimensiones. También se mide precisión de recomendación (`accepted-and-helpful / shown`), cobertura, tasa de silencios correctos, falsos positivos, reversión y coste/latencia. Ninguna métrica de aceptación sola prueba verdad: una recomendación popular puede ser errónea.

## 5. Riesgos de ruido y mitigaciones

| Riesgo | Mitigación obligatoria |
|---|---|
| Consejo genérico por similitud superficial | `TaskBrief` estructurado, filtros por dominio/stack/fase y requisito de evidencia local o fuente primaria; sin match fuerte, silencio. |
| Spam y fatiga | presupuesto máximo de 3, deduplicación por `recommendation_key`, mostrar sólo en hitos y registrar `dismissed/not useful`. |
| Repetir conocimiento supersedido | `supersedes`, vigencia y estado como filtros duros; recuperación activa también de contraejemplos/conflictos. |
| Autoconfirmación del agente | ninguna recomendación se promueve por la propia narrativa del modelo; necesita artefacto externo, test, revisión o decisión canónica. |
| Confundir decisión con sugerencia | tarjeta declara “no decide”; las decisiones de producto/negocio escalan al fundador y ADR vigente gana. |
| Filtrar secretos o PII desde el historial | misma cuarentena, DLP, ACL, retención y auditoría del RAG blindado; no se indexa output crudo. |
| Métricas manipulables o incompletas | campos nulos explícitos, hashes de evidencia, registro append-only y revisión de muestreo; nunca inferir coste/tiempo. |
| Aprendizaje local convertido indebidamente en regla universal | alcance obligatorio (`project`, stack, condiciones) y fecha de revisión; sólo evidencia multi-proyecto habilita reutilización transversal. |

## 6. Ejemplo simulado: mañana se implementan pagos

**TaskBrief**: `project=tchasky`, `domains=[payments, webhooks]`, `stack=[nodejs, typescript]`, `risk=high`, intención “implementar sistema de pagos”.

El motor primero recupera la fila vigente de [`INVENTARIO_COMPLETO_FRAMEWORK_2026-07-22.md`](../00_COMMAND_CENTER/INVENTARIO_COMPLETO_FRAMEWORK_2026-07-22.md): **Mercado Pago SDK Node** está “evaluado; sí, condicionado”, candidato para API Node/TypeScript con adaptador e idempotencia, y remite al informe certificado [`GITHUB_TOOLS_MARKETPLACE_2026-07-22.md`](../08_REPORTS/TECH_RADAR/GITHUB_TOOLS_MARKETPLACE_2026-07-22.md). No lo presenta como “ya instalado” ni como decisión de proveedor.

Después recupera evidencia operativa del [`BANCO_PREGUNTAS_ESTADO.md`](../01_OBSIDIAN/VAULT_TEMPLATE/03_Tchasky/BANCO_PREGUNTAS_ESTADO.md): el estado documentado el 2026-07-19 exige `event_id` y deduplicación Redis para Mercado Pago, validación fail-closed de secret/firma, y pruebas concretas. Esos controles se transforman en checklist adaptado, con fuente por ítem:

1. Implementar detrás de un adaptador propio; no acoplar dominio al SDK. Fuente: informe de marketplace, recomendación de interfaz propia.
2. Exigir y verificar firma/secret del webhook en fail-closed. Fuente: `BANCO_PREGUNTAS_ESTADO.md`, cierre B9.1.
3. Deduplicar `event_id` antes de mutar estado y conservar idempotencia de la operación de cobro. Fuente: cierres B8.2/B9.2.
4. Ejecutar las pruebas de webhook enumeradas; si cambia el estado, crear nuevos artefactos de evidencia, no reutilizar el “144/144” como prueba de código futuro.
5. Elevar al fundador cualquier elección de proveedor, condición comercial o activación productiva.

La tarjeta sería `SUPPORTED` o `CERTIFIED` sólo según las referencias realmente aprobadas en el ledger. Con los documentos actuales, el ejemplo puede afirmar “antecedente certificado/condicionado” para la evaluación de herramienta y “controles documentados con evidencia”; no puede afirmar que una implementación futura sea segura hasta que el nuevo evento adjunte pruebas y revisión.

## 7. Plan por fases — sin código aún

### Fase 0 — Aprobación de gobernanza

Definir con el fundador: quién promueve `confirmed/certified`, retención/ACL, taxonomía mínima, umbrales de silencio, qué dominio se pilota y cuándo un resultado genera ADR. Acordar explícitamente que las recomendaciones no deciden producto ni ejecutan acciones.

**Salida:** contrato aprobado de estados y responsables.

### Fase 1 — Registro manual estructurado y piloto de pagos

Crear el esquema `WorkEvent`/`LearningRecord`, una plantilla versionada y un ledger fuera del repo real. Capturar manualmente un conjunto pequeño de avances ya documentados (pagos, tool registry, patrones Codex-Claude) con enlaces, no copiar contenido. Producir manualmente la tarjeta del ejemplo y auditar que sólo use fuentes válidas.

**Salida:** 10–20 eventos con evidencia y 3–5 lecciones, sin automatización ni vector DB nuevo.

### Fase 2 — Proyección segura al RAG blindado

Conectar el ledger y los registros/ADRs como colección `continuous-learning` del `rag-core`: esquema, hashes, ACL, versionado, filtros de vigencia, citas y trazas. Construir evaluación offline con TaskBriefs conocidos, no-answer y fuentes revocadas/conflictivas.

**Salida:** recuperar correctamente antecedentes sin fuga, sin recomendación ante evidencia insuficiente y con citas por tarjeta.

### Fase 3 — Activación asistida y feedback explícito

Activar el hook al inicio de tareas Tchasky, con máximo de tres tarjetas y botones/estados `used`, `dismissed`, `not_applicable`, `helpful`, `harmful`. Los resultados generan eventos revisables, no cambios automáticos de confianza.

**Salida:** métricas de precisión, fatiga, silencio correcto y coste durante un piloto acotado.

### Fase 4 — Calibración y expansión

Ajustar reglas con resultados del piloto; incorporar otros dominios sólo si se mantiene calidad. Agregar detección de patrones entre eventos aprobados, con toda nueva lección como `candidate` hasta revisión. Establecer gates para degradación de grounding, falsos positivos y seguridad.

**Salida:** recomendaciones repetibles, explicables y medibles; no “memoria automática” no auditada.

## Fuentes externas consultadas

- [Architectural Decision Records](https://adr.github.io/) — definición de decisión, razón, trade-offs y decision log.
- [MADR / Markdown Any Decision Records](https://adr.github.io/madr/) — plantilla y tratamiento de evidencia, confianza y revisión.
- [Microsoft Engineering Playbook: decision log](https://microsoft.github.io/code-with-engineering-playbook/design/design-reviews/decision-log/doc/decision-log/) — registro de alternativas, razonamiento y trabajo requerido.
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) — memoria jerárquica y recuperación selectiva para contexto persistente.
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) — uso de feedback como memoria episódica para intentos posteriores; aplicado aquí con revisión y evidencia.
- [Ragas metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) — métricas separadas para evaluar retrieval y grounding.
