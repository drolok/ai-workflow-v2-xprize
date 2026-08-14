# Investigación: cómo hacer el RAG más potente, rápido y eficiente

Investigación despachada a 4 IAs en paralelo (fronts distintos) el 2026-07-28, a pedido del fundador tras montar el RAG de cybersecurity skills (2578 docs, AnythingLLM + LanceDB + Ollama). Todas las fuentes citadas son de las IAs, no verificadas línea por línea por Claude salvo donde se indica explícitamente.

## Estado actual (contexto)

- **Graphify**: grafo estático de código/docs, 4106 nodos, 8308 aristas, 272 comunidades. Construido, consultable vía CLI (`graphify.exe query/explain/path`), pero **desconectado** del RAG vectorial.
- **AnythingLLM + LanceDB + Ollama**: RAG vectorial, `bge-m3` para embeddings (migrado desde `nomic-embed-text` el 2026-07-28, ver addendum al final), `qwen2.5-coder:7b` para chat, workspace dedicado `cybersecurity-skills-reference` con 2578 documentos ya embebidos y verificados con una consulta real.
- **Obsidian vault**: carpeta de markdown que Claude lee/escribe directamente, sin ninguna herramienta de integración.
- Los tres sistemas hoy son independientes — nunca se combinaron hasta esta investigación.

## 1. Graphify + RAG vectorial: ¿es un patrón real? (Kimi, Antigravity)

**Sí, patrón consolidado y con ventaja real en nuestro caso.** Se llama **GraphRAG** (formalizado por Microsoft Research, `microsoft/graphrag` en GitHub), y nuestra situación es favorable porque **ya tenemos el grafo construido** — evitamos la parte cara del patrón original (extracción de entidades vía LLM).

**Proyectos open-source reales que hacen exactamente esto** (Antigravity, con fuentes):
- `vitali87/code-graph-rag` — Tree-sitter → AST → Memgraph (grafo) + LanceDB (vectorial), expuesto vía MCP. El más análogo a nuestro stack.
- Aider — Repository Map con Tree-sitter, sin base de grafo separada.
- Sourcegraph Cody — SCIP/LSIF como grafo persistente + RAG vectorial.
- Continue.dev — AST parsing + LanceDB para autocomplete.

**Patrones aplicables a nuestro stack concreto (Kimi, priorizados):**

1. **Local Search con expansión por grafo** (alto impacto, esfuerzo bajo-medio): query → embedding → top-k en LanceDB → por cada hit, `graphify.exe query/path` agrega al contexto los archivos que lo importan y sus dependencias directas. Resuelve el fallo clásico de RAG puro sobre código: encontrar el archivo correcto pero no sus dependencias.
2. **Reranking con señal de grafo** (alto impacto, esfuerzo bajo): reordenar candidatos del retrieval vectorial usando centralidad del grafo (un archivo importado por 40 módulos pesa más que uno huérfano) — regla determinística, no requiere modelo nuevo.
3. **Comunidades como unidad de resumen** (impacto medio, esfuerzo medio): generar un resumen offline por cada una de las 272 comunidades ya detectadas por Graphify, embeberlos como colección separada — equivalente al "global search" de GraphRAG para preguntas holísticas ("¿cómo está organizada la autenticación en Tchasky?").
4. **Filtrado por subgrafo** (barato, nicho): guardar `community_id`/`file_path` como metadata en LanceDB para restringir búsquedas cuando la query menciona un módulo conocido.

**Lo que NO conviene** (Kimi): montar el pipeline completo de Microsoft GraphRAG (extracción LLM de entidades + Leiden + community reports) — nuestro grafo ya existe y es estructural (imports reales), más confiable que uno extraído por LLM para código.

**Contraste con nuestra propia evidencia empírica (Claude, benchmark real 2026-07-20 y 2026-07-28):** Graphify por sí solo (sin el patrón de expansión descrito arriba) **falló** en capturar el flujo runtime completo (HTTP→ruta→servicio→DB) en el test T2 del benchmark — encontró el cluster correcto pero el camino corto era estructural, no el flujo real de ejecución. Esto no contradice la propuesta de arriba, la refuerza: Graphify solo (sin combinar con retrieval vectorial + LLM) no alcanza para ese tipo de pregunta, que es justo el caso de uso que GraphRAG dice resolver combinándolo con retrieval.

## 2. Mejoras concretas al RAG actual, priorizadas por impacto/esfuerzo (Kimi)

| # | Mejora | Impacto | Esfuerzo | Nota |
|---|---|---|---|---|
| P1 | Hybrid search: BM25/FTS + vector (RRF) | Muy alto | Bajo | El cambio más rentable — términos exactos (CVE-ids, nombres de función) se diluyen en embeddings puros. LanceDB soporta FTS nativo. AnythingLLM no expone esto directo — requiere orquestador propio. |
| P2 | Reranking con cross-encoder (`bge-reranker-v2-m3`) | Alto | Bajo-medio | ~50-200ms extra en CPU para 20 candidatos, mejora de precisión consistente en la literatura. |
| P3 | Chunking por estructura, no tamaño fijo | Alto | Medio | Para markdown: chunkear por headers `##`, mantener el path de headers como prefijo. Para código: chunking AST-aware (paper CAST, arXiv 2506.15655) vía tree-sitter. |
| P4 | Evaluar alternativas de embeddings (BGE-M3, qwen3-embedding) | Medio | Medio | `nomic-embed-text` es el default correcto para laptop — no cambiar a ciegas, armar 30 queries de prueba y medir recall@5 antes de decidir. Reindexar 2578 docs es barato (minutos). |
| P5 | Metadata filtering (`source_type`, `community_id`, `file_path`) | Medio | Bajo | Habilita el patrón de filtrado por subgrafo de la sección 1. |
| P6 | Query expansion (HyDE / multi-query) con LLM local | Medio-bajo | Bajo | Ayuda con vocabulario asimétrico. |

**No priorizar ahora:** cambiar de LanceDB a Qdrant (2578 docs es trivial para LanceDB — Antigravity sugirió considerar migración "si el volumen crece a decenas de miles", no es el caso hoy), fine-tuning de embeddings, upgrades de GPU.

**Hallazgo arquitectónico clave (Kimi + Antigravity, coinciden):** AnythingLLM solo, tal como está montado, **no puede hacer ninguna de estas mejoras** (hybrid search, reranking, expansión por grafo) — hace falta un **orquestador propio** (script o workflow n8n, ya disponible en el framework) entre la query del usuario y AnythingLLM/LanceDB. AnythingLLM queda como frontend de chat; el orquestador hace el trabajo real de retrieval.

**Orden de ejecución sugerido (Kimi):** P1 + P5 (una sesión) → P2 (media sesión) → P3 (una-dos sesiones) → A/B de embeddings P4 → patrones de grafo (sección 1, puntos 1 y 2) → comunidades (punto 3).

## 3. Modelos de embeddings locales — comparativa (Antigravity)

| Modelo | Contexto | Fortaleza | Caso ideal |
|---|---|---|---|
| `nomic-embed-text` (actual) | 8192 tokens | Liviano, eficiente en CPU | Default correcto para recursos limitados |
| `mxbai-embed-large` | 512 tokens | Mejor calidad pura en MTEB (sub-500M) | Máxima precisión semántica |
| `bge-m3` (BAAI) | 8192 tokens | Híbrido nativo (denso + sparse + multi-vector), multilingüe | Cubriría P1 (hybrid search) sin necesitar FTS separado |
| `snowflake-arctic-embed` | 512 tokens | Muy rápido en hardware heterogéneo | Inferencia rápida |

## 4. Agentic RAG — patrón real, distinto de "hyperretrieval" (Antigravity)

- **"Hyperretrieval" / "Agentic RAG hyperretrieval": NO es un término académico o industrial establecido.** Es marketing de un vendor específico (HyperLLM/Toolify AI, ligado a "Hybrid Retrieval Transformers"). No se usa en LangChain, LlamaIndex, Microsoft Research, Anthropic ni OpenAI. Diagnóstico honesto de Antigravity, no de Claude — Claude no verificó esta fuente de forma independiente.
- **Agentic RAG SÍ es real y bien documentado**: en vez de 1 paso pasivo (query → top-k → respuesta), un agente planifica sub-búsquedas, ejecuta retrieval multi-paso con múltiples herramientas, y se autoevalúa/reformula si el contexto es insuficiente (patrones **Self-RAG** y **Corrective RAG/CRAG**, arXiv 2310.11511).
- **Valor real para nuestro caso (auditorías de seguridad/código):** alto — reduce alucinaciones al forzar al agente a validar el contexto recuperado antes de reportar un hallazgo, en vez de confiar en una sola consulta vectorial.
- Relación con la sección 1: el orquestador propio que ya se necesita para hybrid search/reranking/expansión por grafo es también la pieza que habilitaría un loop agentic (planificar → buscar → evaluar → refinar), no son mejoras separadas — es la misma pieza de infraestructura faltante.

## 5. GraphRAG vs RAG vectorial — cuándo aporta valor real (Gemini)

Confirmado por dos fuentes independientes (Gemini + Antigravity), consistente:

| Dimensión | RAG vectorial simple | GraphRAG |
|---|---|---|
| Relaciones | Implícitas (cercanía semántica) | Explícitas (imports, llamadas, herencia) |
| Bueno para | Texto narrativo, búsquedas puntuales | Corpus interconectado (código, patentes) |
| Ejemplo de pregunta | "¿Cómo configuro X?" | "¿Qué se rompe si cambio X?" |

Casos concretos donde vectorial simple falla y GraphRAG gana: análisis de impacto de cambios, trazado de flujo de datos/control, detección de violaciones de patrón arquitectónico (ej. controladores que saltan la capa de servicios) — este último requiere consultar la *ausencia* de una relación topológica, algo que retrieval vectorial no puede expresar en absoluto.

## Conclusión y próximo paso concreto

Las 4 fuentes convergen en lo mismo sin haberse coordinado entre sí: **el cuello de botella real no es el modelo de embeddings ni la base vectorial — es la ausencia de un orquestador propio** entre la query y AnythingLLM. Ese orquestador es el prerequisito único que habilita hybrid search (P1), reranking (P2), expansión por grafo (sección 1), y eventualmente un loop agentic (sección 4). Sin escalar más investigación, el siguiente paso concreto y de mayor ROI es: prototipar ese orquestador con P1 (hybrid search) + P5 (metadata filtering) primero, medible con un set de ~30 queries reales antes de decidir si vale la pena seguir a P2/P3.

**No implementado aún — esto es investigación, no una decisión tomada. Queda para que el fundador decida si y cuándo se construye.**

## Actualización 2026-07-28 (mismo día) — MVP construido y probado, con hallazgo real

Se construyó un MVP real del orquestador propuesto en la sección "Conclusión": `06_AGENT_FRAMEWORK\GRAPHIFY\rag_orchestrator.py`. Implementa:
- Retrieval vectorial real contra AnythingLLM (endpoint `/vector-search`, confirmado funcional y documentado — no está en el `openapi.json` público pero responde correctamente).
- Boost híbrido barato (P1 simplificado): combina score de similitud coseno con match literal de keywords de la query, sin dependencias nuevas.
- Expansión estructural vía Graphify (patrón sección 1) cuando la query menciona un archivo de código conocido.

**Hallazgo real durante la prueba, no anticipado por ninguna de las 4 investigaciones:** query en español ("qué skill usaría para detectar ataques de path traversal") devolvió resultados **completamente irrelevantes** (forense de memoria, dumping de credenciales, Suricata) con scores altos (0.55-0.56) — el corpus tiene versiones `SKILL.md` (inglés) y `SKILL.es.md` (español) del mismo contenido, y `nomic-embed-text` sesga fuertemente por idioma de la query sobre relevancia semántica real. La misma pregunta en inglés ("path traversal directory traversal vulnerability testing") recuperó el skill correcto exacto en 1er lugar (`performing-directory-traversal-testing`, score 0.758).

**Esto valida con evidencia concreta la recomendación P4 de Kimi** (evaluar `BGE-M3`, multilingüe nativo) — no era solo teoría de la investigación, es un problema real y reproducible en nuestro propio corpus. Próximo paso concreto si se quiere seguir: reindexar con BGE-M3 y repetir esta misma prueba española/inglesa para confirmar si se corrige.

## Actualización 2026-07-28 (mismo día) — A/B test aislado y migración real ejecutada

**A/B test aislado** (`06_AGENT_FRAMEWORK\GRAPHIFY\_embedding_ab_test.py`, contra la API de Ollama directamente, sin pasar por AnythingLLM): 3 documentos (1 correcto en inglés + 2 distractores en español) × 2 queries (español/inglés). `nomic-embed-text` falló la query en español (0.5691 el incorrecto vs 0.5464 el correcto); `bge-m3` acertó ambas (español 0.5120 correcto gana; inglés 0.7337 vs 0.7630 de nomic, diferencia marginal de ~4%, sin cambio de ranking). Decisión del fundador aplicando la regla ya dada ("si funciona se queda"): adoptar `bge-m3`.

**Migración ejecutada** (alcance global — `EmbeddingModelPref` de AnythingLLM no admite configuración por workspace):
1. Cambio de `EmbeddingEngine`/`EmbeddingModelPref` a `ollama`/`bge-m3:latest` vía `POST /api/v1/system/update-env`.
2. **Efecto secundario real detectado en el momento**: el cambio de modelo desvinculó instantáneamente los documentos de las 8 workspaces existentes (`workspace_documents` y `document_vectors` quedaron en 0 filas, confirmado directo en `anythingllm.db` vía Prisma) — no fue borrado de datos (los 2934 archivos fuente en `storage/documents` quedaron intactos), pero cambió el plan original de "pilotar un workspace chico antes de tocar los grandes": el desenganche ya había ocurrido en las 8 a la vez como efecto del propio cambio de config, así que el pilotaje pasó a aplicarse solo al **re-embebido** (reasociación), no al desenganche.
3. Piloto de humo real en `Tchasky Estado Vivo` (3 docs): re-asociado, 28 vectores generados, query real en español ("cuáles son las preguntas priorizadas del banco de decisiones") devolvió `PREGUNTAS_PRIORIZADAS.md` como resultado #1 (score 0.638) — confirmado funcional antes de tocar el workspace grande.
4. Re-embed completo de `cybersecurity-skills-reference` (2578 docs): ~19.4 minutos, 3194 vectores generados. Benchmark real a escala de producción (mismas 2 queries del A/B test aislado, contra el corpus completo, no solo 3 docs): español → `performing-directory-traversal-testing/SKILL.md` gana con score 0.55; inglés → mismo doc gana con score 0.73. **Ambos idiomas correctos, confirmando que la mejora del A/B test aislado se sostiene a escala real.**

**Pendiente**: re-embeber los 6 workspaces Tchasky restantes (`Mi espacio de trabajo`, `Tchasky PC Audit`, `Tchasky Handoffs Y Estado`, `Tchasky Decisiones Y Pagos`, `Tchasky Arquitectura Y Codigo`, `Tchasky Growth E Intel` — 585 documentos en total) con el mismo patrón de re-embed + verificación puntual, uno por uno.
