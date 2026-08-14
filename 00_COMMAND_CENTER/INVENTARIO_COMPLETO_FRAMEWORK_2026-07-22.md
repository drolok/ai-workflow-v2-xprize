# Inventario completo del framework — Parte A (2026-07-22)

Alcance: inventario con evidencia local de las cuatro categorías solicitadas. “Certificado” significa que la evidencia disponible aprobó una batería válida; una instalación, una respuesta aislada o un catálogo visible no bastan. No se infiere una key activa si la fuente sólo acredita que un proveedor está disponible.

## 1. IAs / modelos probados

| Ítem | Proveedor / vía | Qué hace | Estado real verificado | Fuente |
|---|---|---|---|---|
| `qwen2.5-coder:7b` | Ollama local | Modelo de código usado como fallback offline del auditor. | **Parcial, no certificado**: pasó una prueba mínima, pero en la batería A–D inventó evidencia en B/C; sólo sería usable detrás de gateway de evidencia y validador de citas. | `08_REPORTS\TECH_RADAR\AUDITOR_RESPALDO_2026-07-21.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| `qwen3.5:9b` | Ollama local / OpenCode custom | Modelo local general; también configura Hermes. | **Parcial/bloqueado para auditoría**: la prueba OpenCode respondió sin leer el archivo; la auditoría extensa local excedió 180 s. | `08_REPORTS\TECH_RADAR\OPENCODE_INTEGRACION_2026-07-21.md`; `08_REPORTS\TECH_RADAR\AUDITOR_RESPALDO_2026-07-21.md` |
| `opencode/big-pickle` | OpenCode | Modelo operativo de OpenCode para lectura y auditoría con herramientas. | **Parcial, no certificado**: lectura real y 3/3 discrepancias iniciales detectadas; la certificación final quedó invalidada/requiere repetición del Caso C reparado. | `08_REPORTS\TECH_RADAR\AUDITOR_RESPALDO_2026-07-21.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| `nvidia/z-ai/glm-5.2` | NVIDIA vía OpenCode | Candidato de razonamiento/auditoría con herramientas de OpenCode. | **No certificado**: terminó la ronda histórica, pero en C reparado no emitió conclusión final antes de 90 s. | `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| `nvidia/minimaxai/minimax-m2.7` | NVIDIA vía OpenCode | Candidato de auditoría/código. | **No certificado**: en C reparado confundió `3.529 s` con `3.529 ms`. | `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| `nvidia/stepfun-ai/step-3.7-flash` | NVIDIA vía OpenCode | Candidato flash de razonamiento/agentes. | **No certificado**: timeout en A/C reparados y añadió un dato falso en B. | `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| `nvidia/mistralai/mistral-small-4-119b-2603` | NVIDIA vía OpenCode | Candidato mixto de razonamiento/código. | **No certificado**: detectó la discrepancia de C, pero afirmó erróneamente un resultado 9/10. | `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| Cohorte Top 50 de chat | NVIDIA y OpenAI vía OpenCode | 50 candidatos de texto/razonamiento seleccionados contra el catálogo local. | **Sin rol aprobado**: 4/50 completaron la batería histórica; tras C reparado, ninguno certificó. Los demás quedaron bloqueados, fallaron o no dieron respuesta evaluable. | `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\TOP50_CANDIDATOS_2026-07-22.md` |
| `nvidia/nvidia/nemotron-3-super-120b-a12b` | NVIDIA NIM directo / OpenCode | Modelo cloud de razonamiento/código. | **Parcial**: helper Python útil en 4.116 s y lectura OpenCode correcta en 14.98 s; no fue certificado como auditor. | `00_COMMAND_CENTER\TOOL_REGISTRY.md`; `08_REPORTS\TECH_RADAR\OPENCODE_INTEGRACION_2026-07-21.md` |
| `nvidia/gliner-pii` | NVIDIA NIM | Detector/redactor de PII previo a indexación. | **OK para la prueba puntual**: extrajo email, teléfono, ciudad y código postal en 496 ms. | `00_COMMAND_CENTER\TOOL_REGISTRY.md`; `08_REPORTS\TECH_RADAR\NVIDIA_NIM_CAPACIDAD_REAL_2026-07-21.md` |
| `nemotron-parse` | NVIDIA NIM | OCR y layout para scans/imágenes. | **Parcial/no aplicable hoy**: prueba de imagen funcionó, pero el corpus actual no tiene PDF ni imágenes y mezcla de texto devuelve 400. | `00_COMMAND_CENTER\TOOL_REGISTRY.md`; `08_REPORTS\TECH_RADAR\NVIDIA_NIM_CAPACIDAD_REAL_2026-07-21.md` |
| `google/diffusiongemma-26b-a4b-it` | NVIDIA NIM | VLM para QA/OCR ligero de imágenes. | **OK para prueba puntual**: leyó correctamente una imagen de benchmark; no sustituye parse/layout detallado. | `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| `flux.2-klein-4b` | NVIDIA NIM | Generación cloud de mockups. | **OK para prueba puntual**: generó JPG; texto embebido ilegible, por lo que no sirve para branding/texto exacto. | `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| `magpie-tts-multilingual` | NVIDIA NIM | Texto a voz multilingüe. | **OK para prueba puntual**: listó voces y sintetizó WAV. | `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| `nvidia/nemotron-3.5-content-safety` | NVIDIA NIM | Moderación/guardrails de contenido. | **OK para prueba puntual**: clasificó contenido unsafe y su categoría. | `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| `anthropic/claude-sonnet-5`, `openai/gpt-5.6-luna`, `deepseek/deepseek-v3.2` | OpenRouter API | Tres familias cloud para conectividad/routing unificado. | **OK sólo para conectividad**: 3/3 completions reales; no certifica calidad de auditoría. DeepSeek V3.2 además fabricó evidencia en su batería de auditor. | `08_REPORTS\TECH_RADAR\OPENROUTER_PRUEBA_REAL_2026-07-22.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |

## 2. APIs con key activa

| API | Qué da | Estado real verificado y límites | Fuente |
|---|---|---|---|
| NVIDIA NIM | Catálogo/endpoint NVIDIA para chat, PII, OCR, VLM, imagen, TTS y seguridad. | **Key activa y llamadas reales**. La cuota trial no es transparente; varios modelos del catálogo no quedaron utilizables y el acceso depende de Internet/cuota. | `08_REPORTS\TECH_RADAR\NVIDIA_NIM_CAPACIDAD_REAL_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| OpenRouter | API OpenAI-compatible que enruta Claude, GPT y open-weight mediante una sola superficie. | **Key activa**: autenticó, listó 342 modelos y completó 3 inferencias por USD 0.0002285. Aunque `is_free_tier=true`, `/auth/key` no expuso saldo/límite ni reflejó uso; no asumir gratuidad. La ronda amplia se bloqueó con HTTP 402 por reserva de tokens. | `08_REPORTS\TECH_RADAR\OPENROUTER_PRUEBA_REAL_2026-07-22.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| OpenAI | Proveedor nativo visible para OpenCode (catálogo GPT y modelos OpenAI). | **No verificado como key API activa por estas fuentes**: el catálogo está disponible, pero el radar declara que no hizo llamada directa de OpenAI en la ampliación; las pruebas de varios IDs por OpenCode hicieron timeout. No convertir disponibilidad de catálogo en credencial activa. | `08_REPORTS\TECH_RADAR\OPENCODE_INTEGRACION_2026-07-21.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |

## 3. CLIs y herramientas de agentes

| Herramienta | Qué es/hace | Estado y rol real hoy | Fuente |
|---|---|---|---|
| Codex CLI | Agente de código de terminal. | **Parcial**: instalado y usable; ejecutor de trabajo mecánico/pesado bajo el protocolo, con Claude como auditor. | `00_COMMAND_CENTER\TOOL_REGISTRY.md`; `08_REPORTS\TECH_RADAR\CODEX_PLUGIN_OFICIAL_2026-07-21.md` |
| OpenCode | CLI multi-proveedor de agentes. | **OK**: principal provisional para auditoría asistida de sólo lectura; proveedor/modelo se fija por tarea. Aún sin certificación final de auditor. | `08_REPORTS\TECH_RADAR\OPENCODE_INTEGRACION_2026-07-21.md`; `06_AGENT_FRAMEWORK\BACKUP_AUDITOR\CERTIFICATION_SUITE_2026-07-22\RESULTADOS.md` |
| Herdr | Multiplexor de terminales/panes para agentes. | **Parcial**: workspace y pane Codex probados; rol de coordinación visual/persistente. Windows beta y `agent start` sólo tiene workaround `pane run`; fuera de `HERDR_ENV=1` no se controla. | `00_COMMAND_CENTER\TOOL_REGISTRY.md`; `08_REPORTS\TECH_RADAR\HERDR_INSTALACION_2026-07-21.md`; `08_REPORTS\TECH_RADAR\HERDR_4_IAS_2026-07-21.md` |
| Kimi Code CLI | Agente terminal de Moonshot con one-shot, JSON y ACP. | **Bloqueado**: instalado, pero sin modelo/proveedor/login; sin rol operativo hasta autenticación y recertificación voluntarias. | `08_REPORTS\TECH_RADAR\KIMI_INTEGRACION_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| ZCode | ADE/editor visual que integra varios agentes. | **Sin rol**: abrió archivo, pero no completó tarea headless ni tiene CLI configurada; no aporta frente a Herdr + OpenCode. | `08_REPORTS\TECH_RADAR\ZCODE_EVALUACION_2026-07-22.md` |
| Claude Code CLI | Agente de código de Anthropic en terminal. | **Parcial**: instalado; superficie de auditoría/coordinación actual, con limitaciones Windows/Git Bash en algunos handoffs. | `00_COMMAND_CENTER\TOOL_REGISTRY.md`; `08_REPORTS\TECH_RADAR\CODEX_PLUGIN_OFICIAL_2026-07-21.md` |
| Ponytail | Plugin/skill YAGNI para reducir sobreingeniería. | **OK, opt-in**: instalado; no always-on, pues la medición mostró ahorro <1% y +7.22% de duración. | `08_REPORTS\TECH_RADAR\PONYTAIL_MEDICION_REAL_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| skills.sh | CLI para instalar, actualizar e inventariar skills. | **OK**: gestor/inventario de skills conocidas; no otorga confianza automática y las instalaciones manuales pueden aparecer sin origen. | `08_REPORTS\TECH_RADAR\SKILLS_VIDEO_NOTEBOOKLM_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |

## 4. Plugins/extensiones de Claude Code

| Plugin/extensión | Qué es/hace | Estado real verificado | Fuente |
|---|---|---|---|
| Codex Plugin oficial (`codex@openai-codex`) | Handoff in-session Claude Code → Codex. | **Parcial**: instalado; setup y runtime completaron tarea read-only. `/codex:rescue` falla en este Windows por Git Bash/MSYS fork; complemento del bridge, no reemplazo. | `08_REPORTS\TECH_RADAR\CODEX_PLUGIN_OFICIAL_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| Ponytail (`ponytail@ponytail`) | Plugin de minimalismo/KISS/YAGNI. | **OK, opt-in**: instalado desde marketplace local con fuente oficial; no activarlo por defecto por la medición real. | `08_REPORTS\TECH_RADAR\PONYTAIL_MEDICION_REAL_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| n8n MCP Server oficial | MCP de instancia n8n para workflows y ejecuciones. | **Bloqueado/no activo**: endpoint existe, pero no hay read-only ni allowlist server-side; no conectarlo a la instancia real. | `08_REPORTS\TECH_RADAR\N8N_MCP_2026-07-21.md`; `00_COMMAND_CENTER\TOOL_REGISTRY.md` |
| everything-claude-code | Colección externa de 57 agentes, skills, comandos, hooks y reglas. | **Evaluado, no adoptado como bundle**: sólo se identificaron candidatos de cherry-pick (p. ej., partes de `backend-patterns`); no hay piezas activadas desde el clon y se excluyen las que chocan con el protocolo. | `08_REPORTS\TECH_RADAR\EVERYTHING_CLAUDE_CODE_REVIEW_2026-07-22.md` |

## 5. Repos GitHub externos evaluados

> Los clones de `11_LAB/github_tools_review/` fueron evaluados de forma aislada (`git fsck` correcto y árbol limpio según el informe); ninguno fue integrado en Tchasky.

| Nombre | Qué es/hace | Estado real verificado y aplicabilidad a Tchasky | Fuente |
|---|---|---|---|
| Mercado Pago SDK Node | SDK oficial de pagos/webhooks. | **Evaluado; sí, condicionado:** candidato para API Node/TypeScript con adaptador e idempotencia. | `08_REPORTS\TECH_RADAR\GITHUB_TOOLS_MARKETPLACE_2026-07-22.md` |
| PostGIS | Extensión geoespacial de PostgreSQL. | **Evaluado; sí, condicionado:** radio/cobertura si se usa PostgreSQL; no es integración actual. | Misma fuente |
| Supabase | Plataforma Postgres con Auth, Storage, Realtime y RLS. | **Evaluado; tal vez:** referencia de RLS; adoptarlo requiere decisión arquitectónica. | Misma fuente |
| WhatsApp API examples | Ejemplos Meta para WhatsApp Cloud API. | **Evaluado; referencia puntual:** rama principal desactualizada, no base de producción. | Misma fuente |
| Upstash Rate Limit | Rate limiting distribuido con Redis. | **Evaluado; sí, condicionado:** mitiga abuso; añade servicio/Redis. | Misma fuente |
| BullMQ | Cola Redis para jobs, reintentos y deduplicación. | **Evaluado; sí, condicionado:** útil para holds, notificaciones y pagos; no evita sola doble-reserva. | Misma fuente |
| Cal.com DIY | Producto completo de scheduling/reservas. | **Evaluado; sólo referencia:** extraer pruebas/patrones, no incorporar monorepo. | Misma fuente |
| ALTCHA | CAPTCHA autoalojable proof-of-work. | **Evaluado; sí, condicionado:** complemento antispam con CPU/fricción. | Misma fuente |
| OpenAI Guardrails Python | Validación configurable y moderación. | **Evaluado; tal vez:** patrón útil, pero Python/API externa no encaja directo en API TS. | Misma fuente |
| Resend Node | SDK Node de email transaccional. | **Evaluado; sí:** candidato ligero con outbox/adaptador propio. | Misma fuente |
| Novu | Workflows de notificación multicanal. | **Evaluado; tal vez:** activo pero sobredimensionado para email inicial. | Misma fuente |
| Sharp | Procesamiento de imágenes Node/libvips. | **Evaluado; sí:** validación, resize, limpieza de metadata y miniaturas. | Misma fuente |
| Orama | Búsqueda full-text embebible para TS/Node. | **Evaluado; sí, condicionado:** catálogo ligero sin vector/RAG inicial. | Misma fuente |
| everything-claude-code | Colección de agentes, comandos, hooks, reglas y skills. | **Inventariado; no activado:** 57 piezas; sólo insumos de revisión compatibles con el protocolo. | `08_REPORTS\TECH_RADAR\EVERYTHING_CLAUDE_CODE_REVIEW_2026-07-22.md`; `11_LAB\everything-claude-code\README.md` |

## 6. Infraestructura local

| Nombre | Qué es/hace | Estado real verificado | Fuente |
|---|---|---|---|
| Docker Desktop / Engine | Runtime local de contenedores. | **Operativo:** Engine 29.5.2 documentado; al corte Hermes y n8n están arriba. | `00_COMMAND_CENTER\CURRENT_STATE.md`; `docker ps -a` (2026-07-22) |
| Open WebUI + AnythingLLM | Interfaces locales de chat/RAG por Docker. | **Instalados, detenidos:** ambos contenedores figuran `Exited`; no son servicio residente. | `00_COMMAND_CENTER\CURRENT_STATE.md`; `docker ps -a` (2026-07-22) |
| LlamaIndex + Weaviate | RAG híbrido BM25/vector/rerank y endpoint HTTP. | **Aprobado:** certificación 10/10 con fuentes reales y smoke test HTTP; `weaviate-lab` se detuvo tras cleanup. | `11_LAB\rag-comparison\CERTIFICATION_RESULTS.md` |
| Graphiti + Neo4j | Memoria temporal/grafo self-hosted. | **Bloqueado/depriorizado:** entorno creado, retry bloqueado por rate limit OpenAI; Neo4j detenido. | `11_LAB\graphiti-experiment\CERTIFICATION_RESULTS.md`; `docker ps -a` (2026-07-22) |
| Hermes Agent | Agente Docker con skills y volumen persistente. | **Operativo:** `hermes-agent-lab` arriba; dependencias Google persistidas en el bind mount. | `11_LAB\tool-stack\docker\hermes-agent\README.md`; `08_REPORTS\TECH_RADAR\HERMES_PRUEBA_FUNCIONAL_2026-07-22.md` |
| n8n | Automatización local por Docker/localhost. | **Operativo con uso controlado:** `n8n-local-automation` arriba. | `00_COMMAND_CENTER\CURRENT_STATE.md`; `docker ps -a` (2026-07-22) |

## 7. Automatización personal

| Nombre | Qué es/hace | Estado real verificado | Fuente |
|---|---|---|---|
| Hermes + Gmail | Consulta de correo mediante OAuth Google. | **PASS sólo lectura:** autenticación válida y búsqueda Inbox devolvió cinco metadatos; sin envío/modificación. | `08_REPORTS\TECH_RADAR\HERMES_PRUEBA_FUNCIONAL_2026-07-22.md` |
| Hermes + Google Drive | Consulta de Drive mediante OAuth Google. | **PASS sólo lectura:** devolvió cinco elementos; el wrapper no garantiza aún formalmente orden por `modifiedTime`. | Misma fuente |
| Hermes + Calendar | Consulta de calendario mediante OAuth Google. | **Lectura verificada; automatización pendiente:** `calendar list` respondió vacío; no hay flujo aprobado de escritura. OAuth actual solicita scopes amplios. | Misma fuente; `08_REPORTS\TECH_RADAR\HERMES_GOOGLE_OAUTH_PASOS_2026-07-21.md` |

## 8. Framework documental/organizativo

| Nombre | Qué es/hace | Estado real verificado | Fuente |
|---|---|---|---|
| Vault template Obsidian | Estructura documental para command center, proyectos, Tchasky, IA local, personal y archivo. | **Creado y presente:** once módulos raíz, incluidos `03_Tchasky` y `09_Workflow_IA_Local`. | `01_OBSIDIAN\BIS_BRAIN\`; `00_COMMAND_CENTER\CURRENT_STATE.md` |
| Documentación Graphify del vault | Mapa/notas conceptuales sobre Graphify. | **Existe documentación, no grafo vivo raíz:** hay referencias locales; `graphify-out/graph.json` no existe en la raíz al corte. | `01_OBSIDIAN\BIS_BRAIN\00_Command_Center\Mapa_General.md`; inspección local 2026-07-22 |
| Puente Codex–Claude | Cola compartida/auditable de tareas y respuestas. | **Elegido y operativo como transporte:** filesystem queue; no es daemon autónomo de Claude. | `06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\DESIGN.md`; `CLAUDE_SIDE_QUICKSTART.md` |
| Protocolo `CLAUDE.md` / guard crítico | Reglas de roles, verificación, RAM y escalación; hook de riesgo. | **Documentado e instalado:** hook registrado; el estado documenta que requería reinicio de Claude Code para detección del watcher. | `AGENTS.md`; `00_COMMAND_CENTER\CURRENT_STATE.md` |

## 9. Recursos de cómputo NVIDIA

| Nombre | Qué es/hace | Estado real verificado | Fuente |
|---|---|---|---|
| NVIDIA NIM API | Inferencia alojada para chat, embedding, rerank, parse y PII. | **Probada puntualmente:** varios endpoints respondieron; embedding/rerank no superaron baseline local. No entrega VRAM propia. | `08_REPORTS\TECH_RADAR\NVIDIA_NIM_CAPACIDAD_REAL_2026-07-21.md` |
| NVIDIA Developer Program | Membresía con NIM/NGC, software y formación. | **Sin GPU/VRAM general documentada:** API/NGC autenticados son inferencia y catálogo/descarga, no GPU asignada. | `08_REPORTS\TECH_RADAR\NVIDIA_DEVELOPER_PROGRAM_PROFUNDO_2026-07-21.md` |
| DLI / créditos potenciales | Labs y posible campaña de créditos Google Cloud por logros. | **Acotado/no presupuestable:** DLI sólo provee GPU durante labs; monto/vigencia de créditos de cuenta no verificados. | Misma fuente |
| GPU local RTX 3070 | GPU física del equipo. | **Detectada:** RTX 3070 con driver 591.86; no se documenta VRAM disponible para NIM self-hosted. | `00_COMMAND_CENTER\CURRENT_STATE.md` |
| NVIDIA Blueprints / NGC | Arquitecturas y artefactos para NIM. | **No incluyen compute:** el blueprint multiagente citado recomienda 4 H100 para self-hosting, no provistas por Developer. | `08_REPORTS\TECH_RADAR\NVIDIA_DEVELOPER_PROGRAM_PROFUNDO_2026-07-21.md` |

## Huecos / gaps visibles

- Ningún repo evaluado está integrado ni autorizado para modificar Tchasky.
- Graphiti sigue bloqueado; el RAG aprobado se usa bajo demanda, no como servicio residente.
- Calendar sólo tiene lectura vacía; no hay flujo aprobado de creación/edición ni alcance OAuth mínimo.
- No hay VRAM/NVIDIA cloud reutilizable asignada documentada; verificar portal antes de planificar créditos.
