# Local AI Setup

Ultima actualizacion: 2026-07-19

## Objetivo

Dejar operativa la Fase 3 de IA local usando `Ollama` como motor principal, `LM Studio` como superficie secundaria y dos UIs locales separadas:

- `Open WebUI` para chat y prueba rapida.
- `AnythingLLM` para workspace y RAG.

Todo quedo aislado dentro de `C:\AI_WORKFLOW\02_LOCAL_AI` y limitado a `localhost`.

## Decisiones de instalacion

- `Ollama` no se reinstalo porque ya estaba operativo.
- `LM Studio` se instalo de forma nativa por `winget` porque el objetivo era contar con UI de escritorio y servidor local.
- `Open WebUI` se instalo por Docker porque era la ruta mas simple y limpia para conectarlo a Ollama sin exponer nada fuera del equipo.
- `AnythingLLM` se instalo por Docker por la misma razon: persistencia clara, UI en navegador y aislamiento dentro de `C:\AI_WORKFLOW`.
- Se eligio un solo modelo mediano: `qwen2.5-coder:7b`.
- Se eligio un solo embedding model para RAG: `nomic-embed-text:latest`.

## Componentes finales

| Componente | Estado | Ruta o persistencia | Puerto host | Notas |
|---|---|---|---|---|
| Ollama | OK | `<WINDOWS_HOME>\AppData\Local\Programs\Ollama\ollama.exe` | `11434` | Motor principal |
| LM Studio | OK | `<WINDOWS_HOME>\AppData\Local\Programs\LM Studio\LM Studio.exe` | `1234` | Servidor local y UI secundaria |
| Open WebUI | OK con observacion | `C:\AI_WORKFLOW\02_LOCAL_AI\OPEN_WEBUI\data` | `3100` | Docker `open-webui-localai` |
| AnythingLLM | OK | `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\storage` | `3101` | Docker `anythingllm-localai` |
| Test docs | OK | `C:\AI_WORKFLOW\02_LOCAL_AI\TEST_DOCS` | n/a | Documentos sinteticos para validacion |

## Puertos finales

- `127.0.0.1:11434` -> Ollama
- `127.0.0.1:1234` -> LM Studio local server
- `127.0.0.1:3100` -> Open WebUI
- `127.0.0.1:3101` -> AnythingLLM
- `6379` -> contenedor previo `lifeos_redis` ya existente

No se expuso ningun servicio nuevo fuera de localhost.

## Ajuste posterior a Fase 3

- Los puertos de host se remapearon despues del cierre inicial de Fase 3 para evitar choques futuros con servidores dev locales en `3000/3001`.
- Cambio aplicado:
  - Open WebUI: `3000 -> 3100`
  - AnythingLLM: `3001 -> 3101`
- El puerto interno de cada contenedor no cambio.
- Los bind mounts se mantuvieron iguales y no hubo perdida de datos.

## Modelos usados

- Chat principal: `qwen2.5-coder:7b`
- Embeddings para RAG: `nomic-embed-text:latest`

Ver detalle de tamanos y rutas en `MODELS_REGISTRY.md`.

## Validaciones completadas

- Ollama respondio una prueba minima:
  - Prompt: `Responde solo con: OK_CODER`
  - Respuesta: `OK_CODER`
- LM Studio abrio, importo el mismo archivo del modelo por hard link y respondio:
  - Prompt: `Responde solo con: OK_LMSTUDIO`
  - Respuesta: `OK_LMSTUDIO`
- Open WebUI abrio en `http://localhost:3100`, se conecto a Ollama con la misma cuenta local existente y respondio:
  - Prompt: `Say only: OK_OPENWEBUI_CLEAN`
  - Respuesta: `OK_OPENWEBUI_CLEAN`
- AnythingLLM abrio en `http://localhost:3101`, mantuvo `Mi espacio de trabajo`, sus hilos previos y el mismo storage persistente.
- Workspace de prueba usado en AnythingLLM: `Mi espacio de trabajo`.
- AnythingLLM cargo el archivo `phase3_rag_test.md`.
- AnythingLLM contesto correctamente una pregunta RAG:
  - Pregunta: `Segun el documento cargado, cual es el codigo interno de esta prueba?`
  - Respuesta: `ORBITA-314`
- Prueba rapida post-remapeo:
  - Open WebUI `3100` -> `OK_OPENWEBUI_3100`
  - AnythingLLM `3101` -> `OK_ANYTHINGLLM_3101`

## Archivo sintetico de prueba

- Ruta: `C:\AI_WORKFLOW\02_LOCAL_AI\TEST_DOCS\phase3_rag_test.md`
- Uso: validacion segura de carga, indexacion y QA sin tocar documentos reales.

## Credenciales locales de prueba

- Open WebUI:
  - Email: `localai-admin@localhost`
  - Password: `LocalAI!2026`
- AnythingLLM:
  - Modo `Solo yo`
  - Sin password local en esta validacion

Si el sistema se va a conservar mas alla de la prueba, conviene rotar o borrar la cuenta local de Open WebUI.

## Observaciones conocidas

- Open WebUI funciono y respondio bien con `qwen2.5-coder:7b`, pero en chats nuevos vuelve a adjuntar `nomic-embed-text:latest` como modelo secundario y muestra el aviso `"does not support chat"`.
- Esa observacion no bloquea el uso principal ni invalida la prueba, pero conviene corregir la seleccion por defecto antes de sesiones mas largas.
- Open WebUI tambien descargo su propio cache interno de embeddings `all-MiniLM-L6-v2` al arrancar por primera vez. No forma parte del stack principal aprobado, pero es una dependencia interna del contenedor.

## Reinicio rapido

- Iniciar contenedores:
  - `docker start open-webui-localai anythingllm-localai`
- Ver estado:
  - `docker ps`
- Abrir LM Studio:
  - `Start-Process '<WINDOWS_HOME>\AppData\Local\Programs\LM Studio\LM Studio.exe'`
- Cargar o verificar modelo en LM Studio:
  - `& '<WINDOWS_HOME>\AppData\Local\Programs\LM Studio\resources\app\.webpack\lms.exe' ps`
- Ver modelos en Ollama:
  - `ollama ls`

## Siguiente paso recomendado

Pasar a Fase 4 - document processing con un lote pequeno de documentos sinteticos, definir politica de chunking y validar pipeline antes de tocar material real.

## Exploratory Update - 2026-07-19

Esta sesion agrego tres pruebas nuevas sobre el stack local: corpus real en `AnythingLLM`, verificacion de `Ollama 0.32.x` con modo agente, y comparacion de un modelo nuevo apto para `8 GB VRAM`.

### Ollama 0.32.x

- Version verificada en esta maquina: `0.32.1`
- Ruta ya existente: `<WINDOWS_HOME>\AppData\Local\Programs\Ollama\ollama.exe`
- No fue necesario reinstalar ni actualizar.

Prueba de modo agente:

- `ollama agent --help` confirma la disponibilidad de:
  - `--auto-approve-tools`
  - `--no-tools`
  - `--think`
  - `--format`
- Se intento una corrida no interactiva por `stdin` con:

```text
cmd /c "echo Say only OK_AGENT|ollama agent --model qwen2.5-coder:7b --no-tools --format json"
```

- Resultado: timeout tras ~`34s`, sin output util capturable.
- Conclusion: el modo agente existe y ya viene con la CLI nueva, pero en esta maquina quedo validado como experiencia interactiva/manual, no como herramienta facil de automatizar desde shell.

### AnythingLLM - corpus real consolidado

Origen indexado:

- Carpeta fuente: `C:\AI_WORKFLOW\07_PROJECTS\TCHASKY\_DOCUMENTACION_CONSOLIDADA`
- Conteo fuente: `353` archivos
- Peso fuente: `62102015` bytes
- Breakdown:
  - `.md`: `272`
  - `.txt`: `35`
  - `.csv`: `17`
  - `.json`: `26`
  - `.docx`: `3`

Herramientas auxiliares creadas:

- Builder: `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\build_tchasky_corpus_import.py`
- Manifest: `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\tchasky_corpus_import_manifest_2026-07-19.json`
- Body de update: `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\tchasky_update_embeddings_body.json`
- Storage de documentos preparados: `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\storage\documents\tchasky-consolidated-2026-07-19`

Estado real al cierre de la sesion:

- Documentos preparados para import: `353/353`
- Documentos asociados al workspace `Mi espacio de trabajo`: `229/353`
- Faltantes al cierre: `124`
- El contenedor quedo procesando embeddings en segundo plano y los logs mostraron una corrida larga de `3877` chunks sobre el corpus restante.

### Pruebas reales de preguntas

1. B1.7 / lending de dos velocidades
   - Resultado: correcto
   - Respuesta recuperada: `declarative` = acuerdo contractual sin cobro previo; `escrow` = alquiler + deposito retenido por la plataforma
   - Fuente util recuperada por AnythingLLM: `03_ESTADO_POR_FASE/downloads/CORRECCION_B1_1_LENDING_FLOW_V2.md`

2. Distrito piloto / candidatos del corpus
   - Resultado: contenido correcto pero retrieval flojo
   - Respuesta recuperada: `Lince`, `Pueblo Libre`, `Jesús María`, `Magdalena`, `Surquillo`
   - Problema observado: a veces cito el gran documento `taskychasky/2026-04-30_87795fc4.md` o incluso dijo que no encontraba el doc exacto pedido, aunque el contenido estaba en el corpus consolidado.

3. Take rate / N1-PAGOS
   - Resultado: incorrecto o inconsistente
   - Falla observada: para la pregunta sobre `2026-06-09_18009231.md` devolvio una respuesta equivocada basada en otro documento grande, y en una variante mas estricta dijo explicitamente que no encontraba el documento.

### Conclusiones sobre AnythingLLM

- Sirve para memoria amplia y recall rapido sobre el corpus consolidado.
- Funciona mejor con preguntas muy ancladas a terminos distintivos del documento.
- Todavia no es confiable para decisiones sensibles cuando la respuesta depende de una fuente exacta dentro de un corpus grande y heterogeneo.
- Antes de convertirlo en herramienta permanente para Tchasky conviene:
  - terminar la ingesta `353/353`
  - considerar separar el corpus por espacios de trabajo o por temas
  - refinar chunking y naming para reducir colisiones con documentos gigantes tipo `taskychasky/*.md`

## Operational Hardening Update - 2026-07-19

### AnythingLLM - workspaces tematicos reales

- Workspaces operativos confirmados:
  - `tchasky-arquitectura-y-codigo` -> `31` docs
  - `tchasky-decisiones-y-pagos` -> `70` docs
  - `tchasky-growth-e-intel` -> `27` docs
  - `tchasky-handoffs-y-estado` -> `71` docs
  - `tchasky-pc-audit` -> `155` docs
  - `tchasky-estado-vivo` -> `3` docs autoritativos de Obsidian
- Manifest de particion:
  - `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\partitions\partition_manifest_2026-07-19.json`
- Helpers operativos creados:
  - `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\anythingllm_partition_sync.py`
  - `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\anythingllm_query.py`
  - `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\anythingllm_build_obsidian_overlay.py`

Estado real de ingesta:

- Cobertura directa 1:1 del corpus consolidado: `351/353`.
- Los dos documentos que siguieron fallando al domingo 19 de julio de 2026 fueron:
  - `C:\AI_WORKFLOW\07_PROJECTS\TCHASKY\_DOCUMENTACION_CONSOLIDADA\02_HANDOFFS_Y_AUDITORIAS\codex\document_inventory.csv`
  - `C:\AI_WORKFLOW\07_PROJECTS\TCHASKY\_DOCUMENTACION_CONSOLIDADA\02_HANDOFFS_Y_AUDITORIAS\codex\document_inventory.json`
- Motivo observado: error interno de `LanceDB` al vectorizar esas dos serializaciones grandes del inventario; la variante `document_inventory.md` si entro.

Prueba real repetida de take rate despues de particionar:

- Workspace probado: `tchasky-estado-vivo`
- Pregunta: `Segun la documentacion viva actual de Tchasky, cual es el take rate oficial ratificado y en que documento se registra?`
- Resultado real: siguio respondiendo `10% para beta`, que es incorrecto frente al estado vivo actual.
- Artefactos:
  - `C:\AI_WORKFLOW\08_REPORTS\LOCAL_AI\anythingllm_take_rate_query_after_prompt_2026-07-19.json`
  - `C:\AI_WORKFLOW\08_REPORTS\LOCAL_AI\anythingllm_take_rate_query_estado_vivo_2026-07-19.json`

Decision operativa derivada:

- `AnythingLLM` queda util para `discovery` rapido y memoria amplia del corpus.
- No queda autorizado como fuente unica de verdad para preguntas sensibles de estado vigente o decisiones oficiales.
- Regla de uso recomendada desde ahora:
  - primero `AnythingLLM` para localizar donde parece hablarse de `X`
  - luego verificacion manual directa en archivo si la respuesta afecta decision, conteo o estado oficial

### Ollama Agent CLI - veredicto operativo

- Documentacion oficial revisada el domingo 19 de julio de 2026:
  - `https://docs.ollama.com/cli`
  - `https://docs.ollama.com/api/introduction`
  - `https://docs.ollama.com/integrations`
- Hallazgo:
  - la documentacion oficial actual enfatiza `ollama run`, la API HTTP y `ollama launch` para integraciones;
  - no documenta un flujo scriptable comparable para `ollama agent`.
- Pruebas locales nuevas:
  - `ollama agent --help` confirma flags (`--auto-approve-tools`, `--no-tools`, `--format`, `--think`)
  - dos pruebas no interactivas distintas (una en el workspace y otra en un directorio temporal limpio) abrieron el TUI con el prompt fijo `what changed on this branch?`, ignoraron el texto enviado por `stdin` y terminaron por timeout
- Conclusión:
  - el subcomando existe, pero no quedo operacional como herramienta automatizable en esta maquina al domingo 19 de julio de 2026
  - la via local automatizable sigue siendo la API de `Ollama`, no `ollama agent`

### qwen3.5:9b - prueba real en espanol

- Documento usado:
  - `C:\AI_WORKFLOW\07_PROJECTS\TCHASKY\_DOCUMENTACION_CONSOLIDADA\01_ANALISIS_Y_ARQUITECTURA\proyectos_privados\DOCTRINA_CONFLUENCIA_TCHASKY_2026-06-19.md`
- Artefacto:
  - `C:\AI_WORKFLOW\08_REPORTS\LOCAL_AI\qwen_spanish_summary_compare_2026-07-19.json`
- Resultado:
  - `qwen2.5-coder:7b` -> `23.285s`, respuesta completa, obediencia razonable al formato
  - `qwen3.5:9b` -> `89.671s`, corto por `length` y derivo hacia propuestas no pedidas
- Conclusion:
  - `qwen3.5:9b` no gano un rol claro como modelo de analisis/resumen documental en espanol
  - `qwen2.5-coder:7b` sigue siendo el modelo local mas util en este hardware para el stack actual
