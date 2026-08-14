---
type: "operational"
key: "tool_registry"
namespace: "ai_workflow.operations"
tags:
  - "registro de herramientas"
  - "herramientas"
  - "servicios"
  - "puertos"
  - "anythingllm"
  - "docker"
  - "versiones"
status: "stale"
generated: false
verified: "2026-08-13"
stale_after: "2026-08-13"
sources:
  - "auditoria manual de fases 1 y 2"
  - "registros generados SCRIPTS SERVICES MCP SKILLS AGENTS PLUGINS"
  - "git log del propio documento"
confidence: "baja; la tabla manual no fue revalidada por completo y contiene versiones historicas"
verification_notes: "La tabla manual se audito por ultima vez en julio de 2026; filas puntuales agregadas el 2026-08-13 tienen fecha propia."
grounds_to:
  - "{\"id\":\"tool_registry.tchasky_repo\",\"claim\":\"El monorepo real de Tchasky existe\",\"check\":\"path_exists\",\"path\":\"{tchasky_repo}\",\"kind\":\"dir\"}"
  - "{\"id\":\"tool_registry.postgres_running\",\"claim\":\"lifeos_postgres está activo\",\"check\":\"docker_running\",\"container\":\"lifeos_postgres\"}"
  - "{\"id\":\"tool_registry.redis_running\",\"claim\":\"lifeos_redis está activo\",\"check\":\"docker_running\",\"container\":\"lifeos_redis\"}"
  - "{\"id\":\"tool_registry.ollama_port\",\"claim\":\"Ollama usa el puerto 11435\",\"check\":\"ollama_via_router\",\"field\":\"port\",\"expected\":11435}"
  - "{\"id\":\"tool_registry.anythingllm_port\",\"claim\":\"AnythingLLM usa el puerto 3110\",\"check\":\"docker_published_port\",\"container\":\"anythingllm-localai\",\"port\":3110}"
---
# Tool Registry

**Re-medir, en un paso:**

**Desde Windows PowerShell, no desde WSL:**

```powershell
Set-Location 'C:\AI_WORKFLOW_V2'
python '.\.ai\bin\build_registries.py'      # ~210 s. Regenera .ai/generated/*.json con su _meta
Get-Content -Raw '.\.ai\generated\INVENTORY_MANIFEST.json'
```

**Ojo:** regenera los registros **automaticos**; **no vuelve a comprobar la tabla
manual de abajo**, que sigue dependiendo de una auditoria a mano.

**Gotcha 59** — un documento de estado sin fecha de verificacion se lee como
vigente. Antes de repetir lo que dice este documento, corre el comando de
re-medir y compara. Si lo re-mediste, actualiza `verified` y `stale_after` en
el frontmatter OKF: es parte de la tarea, no un extra.

---

| Herramienta | Rol | Local/Online | Estado | Ruta | Puerto | Notas | Próxima revisión |
|---|---|---|---|---|---|---|---|
| Windows 11 Pro | Sistema base | Local | OK | n/a | n/a | Build 26100 | — |
| PowerShell 5.1 | Shell base | Local | OK | Integrado en Windows | n/a | `CurrentUser` en `RemoteSigned`; `pwsh` diferido | — |
| winget | Gestor de paquetes | Local | OK | `<WINDOWS_HOME>\AppData\Local\Microsoft\WindowsApps\winget.exe` | n/a | Chocolatey no detectado | — |
| Git | Control de versiones | Local | OK | `C:\Program Files\Git\cmd\git.exe` | n/a | Validado en Fase 1 | — |
| Python 3.13.0 | Runtime | Local | OK | `<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe` | n/a | `python`, `pip` y `venv` funcionales | — |
| pip 24.2 | Gestor de paquetes Python | Local | OK | `<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\Scripts\pip.exe` | n/a | `PATH` de usuario reparado | — |
| venv | Entornos virtuales | Local | OK | Modulo de Python 3.13 | n/a | Disponible via `python -m venv` | — |
| Node.js | Runtime JavaScript | Local | OK | `C:\Program Files\nodejs\node.exe` | n/a | Instalado con `winget` | — |
| npm | Gestor de paquetes JavaScript | Local | OK | `C:\Program Files\nodejs\npm.cmd` | n/a | Requiere `RemoteSigned` o uso de `.cmd` en PowerShell clasico | — |
| pnpm | Gestor de paquetes JavaScript | Local | OK | `<WINDOWS_HOME>\AppData\Roaming\npm\pnpm.cmd` | n/a | Instalado a nivel usuario; ya no depende del fallback de Codex | — |
| Docker Desktop | Contenedores | Local | OK | `C:\Program Files\Docker\Docker\Docker Desktop.exe` | 5432, 6379 | Engine validado; politica vigente desde 2026-07-20: solo `lifeos_postgres` y `lifeos_redis` quedan residentes, todo laboratorio pesado es bajo demanda | — |
| WSL 2 | Runtime Linux | Local | OK | `C:\Windows\system32\wsl.exe` | n/a | Ubuntu configurado como distro por defecto; `<WINDOWS_HOME>\.wslconfig` fijado en `memory=20GB`, `swap=8GB`, `processors=8`, `autoMemoryReclaim=gradual`, `sparseVhd=true` | — |
| VS Code | Editor | Local | OK | `<WINDOWS_HOME>\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd` | n/a | Version 1.128.0; incluye extension embebida `GitHub Copilot 0.57.0`, cuya validacion end-to-end sigue siendo manual dentro de la UI | — |
| VS Code Insiders | Editor experimental | Local | Not installed | n/a | n/a | Auditoria del 2026-07-21: no se detectaron `code-insiders`, `<WINDOWS_HOME>\AppData\Local\Programs\Microsoft VS Code Insiders`, `<WINDOWS_HOME>\.vscode-insiders` ni `<WINDOWS_HOME>\AppData\Roaming\Code - Insiders`; ver `08_REPORTS\TECH_RADAR\VSCODE_INSIDERS_2026-07-21.md` | sin fecha, revisar manualmente |
| GitHub Copilot en VS Code | Asistencia IDE | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Local\Programs\Microsoft VS Code\8a7abeba6e\resources\app\extensions\copilot\package.json` | n/a | Extension detectada y lista para usar, pero esta auditoria no puede certificar la conversacion visible dentro del editor sin interaccion humana | 2026-09-19 |
| ChatGPT | Asistente general desktop | Online/Local | Partial | `C:\Program Files\WindowsApps\OpenAI.Codex_26.715.8383.0_x64__2p2nqsd0c76g0\app\ChatGPT.exe` | n/a | 2026-07-21: app oficial de OpenAI confirmada por `Get-AppxPackage`/`AppxManifest.xml`; Windows la instala con identidad MSIX `OpenAI.Codex` version `26.715.8383.0`. No se abrio UI en esta tarea. Deja runtime local en `<WINDOWS_HOME>\AppData\Local\OpenAI\Codex`, incluyendo `codex.exe` embebido `0.129.0-alpha.15` | 2026-09-19 |
| Codex CLI | Agente de codigo en terminal | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Roaming\npm\codex.ps1` | n/a | 2026-07-21: paquete global npm `@openai/codex` `0.144.6` detectado y `codex --version` respondio `codex-cli 0.144.6`; queda instalado y usable en terminal, pero fuera de esta comprobacion no se certifico un workflow separado adicional | 2026-09-19 |
| Claude | Asistente general desktop | Online/Local | Partial | `C:\Program Files\WindowsApps\Claude_1.24012.0.0_x64__pzs8sxrjxfjjc\app\Claude.exe` | n/a | 2026-07-21: app oficial de Anthropic confirmada por `Get-AppxPackage`/`AppxManifest.xml`; version instalada `1.24012.0.0`. No se abrio UI en esta tarea | 2026-09-19 |
| Claude Code CLI | Agente de codigo en terminal | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Roaming\npm\claude.ps1` | n/a | 2026-07-21: paquete global npm `@anthropic-ai/claude-code` `2.1.216` detectado y `claude --version` respondio `2.1.216 (Claude Code)`; distinto de la extension ya catalogada en VS Code | 2026-09-19 |
| Microsoft Copilot | Asistente general desktop | Online/Local | Partial | `C:\Program Files (x86)\Microsoft\Copilot\Application\150.0.4078.65\mscopilot.exe` | n/a | 2026-07-21: app desktop de Copilot confirmada por uninstall key, `winget list` y `Get-AppxPackage`; version instalada `150.0.4078.65`. No se probo conversacion real | 2026-09-19 |
| GitHub Copilot CLI | Agente/assistant de codigo en terminal | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Local\Microsoft\WinGet\Links\copilot.exe` | n/a | 2026-07-21: `winget list` la reporta instalada en `v1.0.71`; `copilot --version` respondio correctamente. El `winget show` actual marca `v1.0.73` disponible, asi que la instalacion local esta un release atras | 2026-09-19 |
| ZCode | Editor/ADE agentico de codigo | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Local\Programs\ZCode\ZCode.exe` | n/a | 2026-07-21: version `3.3.6` instalada; segun el manifest de `winget`, es un editor AI que unifica agentes como Claude Code, Codex y Gemini con UI desktop. Tambien quedo el instalador `ZCode-3.3.6-win-x64.exe` en `Downloads` | 2026-09-19 |
| Herdr | Multiplexor terminal-native para agentes | Local | Partial | `<WINDOWS_HOME>\AppData\Local\Programs\Herdr\bin\herdr.exe` | n/a | 2026-07-21: version `0.7.5-preview.2026-07-21-0f10e1453a7f` instalada con el comando oficial `powershell -ExecutionPolicy Bypass -c "irm https://herdr.dev/install.ps1 \| iex"`; la propia doc la marca como `Windows beta`. Integraciones oficiales activas: `claude current (v7)` y `codex current (v6)`. Workspace persistido `AI_WORKFLOW` + tab `bridge` en `<WINDOWS_HOME>\AppData\Roaming\herdr\session.json`; prueba real desde pane Herdr: Codex respondio `HERDR_OK cwd=C:\AI_WORKFLOW`. Se abre dentro del terminal integrado de VS Code con la tarea `Herdr: abrir workspace AI_WORKFLOW`. Organiza/lee panes gestionados, pero no captura retroactivamente `codex exec` externos; para esos y la cola existe la tarea terminal `Monitor: Claude/Codex + bridge`. Complementa a ZCode; no lo reemplaza | 2026-09-19 |
| Letta Code CLI | CLI para agentes stateful | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Roaming\npm\letta.ps1` | n/a | 2026-07-22: `@letta-ai/letta-code` `0.28.11`; la doc oficial confirma bloques de memoria persistentes/editables, pero no se certificó persistencia: la prueba headless falló antes de crear agente por falta de `LETTA_API_KEY`. Complemento potencial para estado autorevisable de un agente, no sustituto del vault; evidencia en `08_REPORTS\TECH_RADAR\LETTA_MEM0_EVALUACION_2026-07-21.md`. | 2026-09-19 |
| Mem0 CLI | Capa de memoria para agentes en CLI | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Roaming\npm\mem0.ps1` | n/a | 2026-07-22: `@mem0/cli` `0.2.11`; la doc oficial confirma API de memoria persistente con ámbitos por entidad, pero no se certificó persistencia: `add` y una búsqueda en proceso separado fallaron por falta de `MEM0_API_KEY`. Complemento potencial de recall programático, no sustituto del vault; evidencia en `08_REPORTS\TECH_RADAR\LETTA_MEM0_EVALUACION_2026-07-21.md`. | 2026-09-19 |
| Windows Terminal | Terminal | Local | OK | `C:\Program Files\WindowsApps\Microsoft.WindowsTerminal_1.24.11911.0_x64__8wekyb3d8bbwe` | n/a | Version 1.24.11911.0 | — |
| Obsidian | Base de conocimiento | Local | OK | `<WINDOWS_HOME>\AppData\Local\Programs\Obsidian\Obsidian.exe` | n/a | Version 1.12.7.0 | — |
| Obsidian Vault Template | Vault documental | Local | OK | `C:\AI_WORKFLOW\01_OBSIDIAN\VAULT_TEMPLATE` | n/a | Vault nuevo y aislado del proyecto real | — |
| Obsidian Auditideas Test Vault | Vault experimental | Local | OK | `C:\AI_WORKFLOW\01_OBSIDIAN\VAULT_AUDITIDEAS_TEST` | n/a | Prueba separada sobre `C:\auditideas` | — |
| TCHASKY Documentation Space | Documentacion de proyecto | Local | OK | `C:\AI_WORKFLOW\01_OBSIDIAN\VAULT_TEMPLATE\03_Tchasky` | n/a | Solo framework; no es el proyecto real | — |
| Tchasky Monorepo Real | Codigo fuente real | Local | OK | `\\wsl$\Ubuntu\home\<USER>\<PRIVATE_PROJECT>` | n/a | Monorepo pnpm real; mezcla nombres heredados `lifeos` y `Chasqui`; repo Git local presente, pero sin remoto GitHub configurado | — |
| Tchasky Local Dev Stack | Runtime producto | Local | OK | `\\wsl$\Ubuntu\home\<USER>\<PRIVATE_PROJECT>` | 3001, 5173, 5432, 6379 | Reactivado el 2026-07-18; `docker compose` sano; migraciones `0001` a `0013` verificadas; por politica residente solo quedan `lifeos_postgres` y `lifeos_redis`, `API` y `web` se levantan solo durante desarrollo activo | — |
| Project Template | Plantilla documental | Local | OK | `C:\AI_WORKFLOW\07_PROJECTS\PROJECT_TEMPLATE` | n/a | Reutilizable para nuevos proyectos | — |
| Ollama | Runtime local de LLM | Local | OK | `<WINDOWS_HOME>\AppData\Local\Programs\Ollama\ollama.exe` | 11435 | Runtime activo comprobado en `0.32.9`; la via automatizable confirmada hoy es la API HTTP (`/api/generate`), no el TUI de `ollama agent`; variables de contencion fijadas: `OLLAMA_MAX_LOADED_MODELS=1` y `OLLAMA_NUM_PARALLEL=1`; modo de uso: bajo demanda, no residente fuera de pruebas activas | — |
| Ollama Agent CLI | Asistente local de tareas simples | Local | Blocked | `<WINDOWS_HOME>\AppData\Local\Programs\Ollama\ollama.exe` | 11435 | `ollama agent --help` existe desde la prueba histórica en `0.32.1`, pero las pruebas no interactivas del domingo 19 de julio de 2026 abrieron el TUI con el prompt fijo `what changed on this branch?` y no consumieron `stdin`; la via oficial automatizable sigue siendo la API/`ollama launch`, no este subcomando | sin fecha, revisar manualmente |
| LM Studio | UI/model runner local | Local | OK | `<WINDOWS_HOME>\AppData\Local\Programs\LM Studio\LM Studio.exe` | 1234 | Version 0.4.19+2; `qwen2.5-coder-7b.gguf` importado por hard link; identificador cargado `qwenlocal` | — |
| Kimi Desktop | Asistente cloud con webbridge | Online/Local | Partial | `<WINDOWS_HOME>\AppData\Local\Programs\kimi-desktop\Kimi.exe` | 10086 | 2026-07-21: version `3.1.2` confirmada; `kimi-webbridge v1.11.3` sigue en `127.0.0.1:10086` con `extension_connected=false` / `no extension connected`. No usarlo como superficie de automatizacion: existe la CLI oficial independiente; ver `08_REPORTS\TECH_RADAR\KIMI_INTEGRACION_2026-07-21.md` | 2026-09-19 |
| Kimi Code CLI | Agente terminal oficial de MoonshotAI | Online/Local | Partial | `<WINDOWS_HOME>\.kimi-code\bin\kimi.exe` | n/a | 2026-07-21: instalada oficialmente, `kimi --version` = `0.28.1`; soporta ejecucion no interactiva (`kimi -p`), `stream-json` y ACP (`kimi acp`), independiente de Kimi Desktop/webbridge. La prueba read-only sobre `C:\AI_WORKFLOW` llego hasta la CLI pero no ejecuto por `No model configured`; falta que el fundador complete `kimi login` (OAuth device-code) o configure una API key de Kimi Platform. Tras eso es la via recomendada para Herdr; evidencia y comando de retest en `08_REPORTS\TECH_RADAR\KIMI_INTEGRACION_2026-07-21.md` | 2026-09-19 |
| NVIDIA NIM Nemotron Chat | Burst cloud de razonamiento/codigo | Online | OK | `https://integrate.api.nvidia.com/v1/chat/completions` | 443 | 2026-07-21: `nvidia/nemotron-3-super-120b-a12b` respondio en `4.116s` con helper Python util; en el mismo prompt supero al `qwen2.5-coder:7b` local por latencia (`11.226s`) y pragmatismo. No reemplaza `Codex`/`Claude` ni el rol offline de `Ollama`/`LM Studio`; depende de internet y de cuota trial no transparente | — |
| OpenRouter API | Broker/routing multi-provider de LLMs | Online | OK, uso controlado | `https://openrouter.ai/api/v1` | 443 | 2026-07-22: key real autenticó y `/models` devolvió `342` modelos. Tres chats reales completaron: `anthropic/claude-sonnet-5` vía Amazon Bedrock (`3.152s`, USD `0.0001500`), `openai/gpt-5.6-luna` vía OpenAI (`1.194s`, USD `0.0000580`) y `deepseek/deepseek-v3.2` vía Friendli (`3.529s`, USD `0.0000205`); total exacto reportado `USD 0.0002285`. Aporta acceso API unificado a Claude/GPT/open-weight que NIM no cubre como una sola superficie. La key se declara free-tier, pero `/auth/key` no expuso saldo/límite ni reflejó el gasto (`usage=0`), por lo que no asumir cuota gratuita. Candidato remoto cuarto para el auditor sólo con gateway read-only, modelo/presupuesto fijos y aprobación del fundador; evidencia en `08_REPORTS\TECH_RADAR\OPENROUTER_PRUEBA_REAL_2026-07-22.md`. | revisar antes de automatizar/cargar créditos |
| NVIDIA NIM GLiNER PII | Deteccion/redaccion PII previa a indexacion | Online | OK | `https://integrate.api.nvidia.com/v1/chat/completions` | 443 | 2026-07-21: `nvidia/gliner-pii` extrajo `email`, `phone_number`, `city` y `postcode` reales en `496ms`; util como helper cloud de gobernanza antes de RAG o exportacion | — |
| NVIDIA NIM nemotron-parse | OCR/layout cloud selectivo para imagenes y scans | Online | Partial / no aplicable al corpus actual | `https://integrate.api.nvidia.com/v1/chat/completions` | 443 | 2026-07-22: auditoría del corpus real del RAG (`353` archivos consolidados + `70` del overlay) encontró `0` PDF y `0` imágenes; los `3` DOCX omitidos tienen texto nativo, no son scans. No se integró para no gastar API en texto. Mantener como candidato: la prueba del 2026-07-21 extrajo texto/bounding boxes de imagen pura en `1.279s`, pero devuelve `400` si se mezcla texto en el prompt. Reabrir solo al entrar un scan/imagen pura y recertificar después | cuando ingrese un scan/imagen pura |
| NVIDIA NIM DiffusionGemma VLM | QA multimodal sobre imagenes y slides | Online | OK | `https://integrate.api.nvidia.com/v1/chat/completions` | 443 | 2026-07-21: `google/diffusiongemma-26b-a4b-it` leyo `nvidia_parse_probe.png` en `1.178s` y devolvio el titulo exacto `AI_WORKFLOW RAG benchmark` + el top stack correcto (`Weaviate hybrid + rerank`). Bueno para OCR-lite / document QA multimodal; no reemplaza parse/layout detallado | — |
| NVIDIA NIM FLUX.2-klein-4b | Generacion de imagen cloud para mockups | Online | OK | `https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b` | 443 | 2026-07-21: genero un JPG de `85.6 KB` en `2.619s`; el concepto del robot con bins salio bien, pero el texto embebido del poster salio ilegible. Bueno para concept art y mockups rapidos; flojo para branding o texto exacto | — |
| NVIDIA NIM Magpie TTS | Text-to-speech cloud multilenguaje | Online | OK | `https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize` | 443 | 2026-07-21: `nvidia/magpie-tts-multilingual` listó voces y sintetizó `audio/wav` mono `44.1kHz` de `5.619s` en `1.552s`; candidato real para accesibilidad, voice UI o narracion | — |
| NVIDIA Health ESM2-650m | Embeddings biologicos / proteins | Online | OK | `https://health.api.nvidia.com/v1/biology/meta/esm2-650m` | 443 | 2026-07-21: devolvio `.npz` en `1.390s` con `embeddings [1,1280]` y `representations [1,46,1280]`. Encaje directo bajo para AI_WORKFLOW, pero confirma que la trial llega a endpoints BioNeMo/health | — |
| NVIDIA cuOpt | Optimizacion de rutas / VRP cloud | Online | OK | `https://optimize.api.nvidia.com/v1/nvidia/cuopt` | 443 | 2026-07-21: resolvio un VRP chico en `86.241s`, `status=0`, `solution_cost=2.0` y rutas para `2` vehiculos. Potencial para scheduling, logistica o field ops; no encaje inmediato en el hueco actual de RAG | — |
| NVIDIA NIM Nemotron 3.5 Content Safety | Moderacion / guardrails de contenido | Online | OK | `https://integrate.api.nvidia.com/v1/chat/completions` | 443 | 2026-07-21: `nvidia/nemotron-3.5-content-safety` marco `unsafe` y categoria `Criminal Planning/Confessions` en `779ms`; encaje fuerte para moderacion de posts/chat y pre-filtros de agentes | — |
| Open WebUI | UI local para LLM | Local | OK | `Docker: ghcr.io/open-webui/open-webui:main` + `C:\AI_WORKFLOW\02_LOCAL_AI\OPEN_WEBUI\data` | 3100 | Bind a `127.0.0.1`; conectado a Ollama via `http://host.docker.internal:11434`; modo de uso: bajo demanda, no residente | — |
| Hermes Agent | Runtime de asistente persistente / gateway OpenAI-compatible | Local | OK | `Docker: nousresearch/hermes-agent:latest` + `C:\AI_WORKFLOW\11_LAB\tool-stack\docker\hermes-agent\data` | 8642, 9119 | 2026-07-22: OAuth y prueba funcional read-only de Calendar/Gmail/Drive aprobadas. Se instaló `google-api-python-client==2.198.0` + auth libs en `data\.local` (montado como `/opt/data`, persistente al recrear el contenedor mientras se conserve `data`); `gws` no es necesario porque la skill usa fallback Python. Evidencia: `08_REPORTS\TECH_RADAR\HERMES_PRUEBA_FUNCIONAL_2026-07-22.md`. Dashboard activo en `http://127.0.0.1:9119`, sin credenciales: el dashboard queda enlazado a loopback dentro del contenedor y el puerto Docker también está publicado solo en loopback del host; se verificó `HTTP 200`. Sigue configurado con Ollama local (`qwen3.5:9b`) y queda residente por pedido del fundador. | — |
| AnythingLLM | Workspace RAG local | Local | Supersedida | `Docker: mintplexlabs/anythingllm:latest` + `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\storage` | 3110 | Supersedida por `Tchasky Operational RAG`: pese a recuperar fuentes reales, la certificacion estricta del 2026-07-19 fue `4/10` y persistio el error LanceDB en `document_inventory.csv/json`. No aporta un rol RAG distinto frente al pipeline operativo `10/10`; conservar solo como laboratorio historico de discovery/reindexacion, bajo demanda y sin optimizacion pendiente. | reabrir solo si aparece un caso de uso no cubierto por el RAG operativo |
| AnythingLLM Corpus Import Builder | Helper de import masivo RAG | Local | OK | `C:\AI_WORKFLOW\02_LOCAL_AI\ANYTHINGLLM\build_tchasky_corpus_import.py` | n/a | Genera JSON docs para `update-embeddings` a partir de `_DOCUMENTACION_CONSOLIDADA`; quedo complementado por `anythingllm_partition_sync.py`, `anythingllm_query.py` y `anythingllm_build_obsidian_overlay.py` | — |
| n8n | App de automatizacion local | Local | OK | `Docker: docker.n8n.io/n8nio/n8n:latest` + `C:\AI_WORKFLOW\03_AUTOMATION\N8N\data` | 5678 | Rol operativo real: capa de operaciones continuas del framework con 4 workflows activos y sanos al domingo 19 de julio de 2026: `AIW Health Check Periodic`, `AIW Tchasky Test Runner`, `AIW Tchasky Stack Monitor` y `AIW Banco Count Sync`; modo de uso: bajo demanda, no residente fuera de sesiones activas de automatizacion | — |
| n8n MCP Server oficial (instance-level) | MCP nativo de n8n para workflows/ejecuciones | Local | Blocked | `http://localhost:5678/mcp-server/http` | 5678 | 2026-07-21: endpoint oficial presente en `n8n 2.30.7`, pero no se activa contra la instancia real porque la documentacion oficial no ofrece modo read-only nativo ni allowlist server-side de tools; el auth correcto es OAuth2 o MCP Access Token propio de n8n, no `AIW_N8N_RUNNER_TOKEN`; ver `08_REPORTS\TECH_RADAR\N8N_MCP_2026-07-21.md` | sin fecha, revisar manualmente |
| n8n Host Runner | Bridge Windows -> contenedor n8n | Local | OK | `C:\AI_WORKFLOW\03_AUTOMATION\N8N\host_runner.py` | 8765 | Expone ejecucion controlada de `health_check`, `scan_ports`, `test-runner`, `monitor/tchasky` y `sync-banco-counts` al contenedor | — |
| AI_WORKFLOW Automation Scripts | Automatizacion manual segura | Local | OK | `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS` | n/a | Scripts read-only o de generacion; sin cron, sin Task Scheduler, sin borrados destructivos | — |
| AI_WORKFLOW Agent Framework | Coordinacion entre agentes | Local | OK | `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK` | n/a | Fase 6 crea roles, plantillas, context packs y handoffs autocontenidos; reutiliza scripts de Fase 5 sin reescribirlos | — |
| AI_WORKFLOW Fase 4 venv | Entorno Python dedicado | Local | OK | `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\.venv` | n/a | Aislado del entorno global; contiene dependencias de Docling y del pipeline sintetico | — |
| Docling | Extraccion a Markdown | Local | OK | `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\.venv\Scripts\docling.exe` | n/a | Version 2.113.0; PDF, DOCX y PPTX sinteticos convertidos a Markdown | — |
| whisper.cpp | Transcripcion local | Local | OK | `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\WHISPER\bin_v191\Release\whisper-cli.exe` | n/a | Version v1.9.1; usa `ggml-tiny.en.bin` para validacion sintetica | — |
| Tesseract OCR | OCR local | Local | OK | `C:\Program Files\Tesseract-OCR\tesseract.exe` | n/a | Version 5.5.0.20241111; se ejecuta por ruta absoluta para no tocar `PATH` | — |
| qwen3.5:9b | Modelo local exploratorio | Local | No clear role | `<WINDOWS_HOME>\.ollama\models\blobs\sha256-dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c` | 11434 | `6594462816` bytes; perdio tambien la prueba final de razonamiento de negocio del 2026-07-19: `qwen2.5-coder:7b` respondio algo aunque desviado, mientras `qwen3.5:9b` devolvio `0` caracteres tras `29.661s`; se mantiene instalado pero sin rol asignado | sin fecha, revisar manualmente |
| LangGraph Lab | Framework experimental de grafos | Local | OK | `C:\AI_WORKFLOW\11_LAB\langgraph-experiment` | n/a | `langgraph 1.2.9` + `langchain-ollama 1.1.0`; la certificacion estricta del 2026-07-19 paso `4/4` casos reales (`positivo`, `negativo`, `DB viva`, `multi-fuente`) sin falsos positivos; candidato fuerte para pipeline auditado de preguntas `[VERIFICAR]` | — |
| LlamaIndex + Qdrant Certification Lab | RAG comparativo estricto | Local | Supersedida | `C:\AI_WORKFLOW\11_LAB\rag-comparison\llamaindex_qdrant_benchmark.py` | 6333 | Supersedida por `Tchasky Operational RAG`: mismo rol de retrieval con LlamaIndex, pero baseline `1/10` y mejor variante BM25+vector+rerank `5/10` (fuentes reales `10/10`, calidad insuficiente). No aporta capacidad funcional distinta frente a Weaviate `10/10`; conservar como benchmark historico, sin optimizacion pendiente. | reabrir solo si se necesita evaluar Qdrant por un requisito nuevo de infraestructura |
| Tchasky Operational RAG (LlamaIndex + Weaviate) | RAG operativo/local | Local | OK | `C:\AI_WORKFLOW\11_LAB\rag-comparison\manage_tchasky_rag.ps1` | 8180 / 8787 | 2026-07-21: pipeline operativo reproducible con [tchasky_rag_system.py](/C:/AI_WORKFLOW/11_LAB/rag-comparison/tchasky_rag_system.py), chunking estructurado, filtrado de corpus ruidoso y weighting por autoridad/recencia/senal; certificacion estricta final `10/10` en [llamaindex_weaviate_hybrid_rerank_2026-07-21_optimized.json](/C:/AI_WORKFLOW/11_LAB/rag-comparison/artifacts/llamaindex_weaviate_hybrid_rerank_2026-07-21_optimized.json). Endpoint `/query` validado por HTTP real: `/health` confirmó `TchaskyOperationalRag` (`148` documentos, `4477` chunks) y tres `POST /query` (`admin_logs`, búsqueda textual, pagos) devolvieron `200`, `8` fuentes y el `extractiveAnswer` exacto del artefacto `10/10`. Se corrigió el conflicto PowerShell `$Host` -> `$BindHost` (alias `-Host`) del wrapper. Stack apagado al terminar (`weaviate-lab=exited`, puerto `8787` libre). | — |
| Cognee Lab | Memoria / RAG candidato | Local | OK | `C:\AI_WORKFLOW\11_LAB\tool-stack\cognee-memory\.venv` | n/a | 2026-07-21: ruta Windows certificada. `Visual Studio Build Tools 2022` (`17.14.36`) instalado y `link.exe` confirmado; `cognee 1.4.0` quedo instalado en el venv tras exponer `cargo`/`rustup` temporales para el build de `litellm`; smoke real `remember` + `recall` aprobado en dataset `cert_smoke_20260721` con Ollama (`qwen2.5-coder:7b` + `nomic-embed-text`). Advertencias no bloqueantes: rutas en `.env` deben ser absolutas y sin `transformers` el conteo de tokens cae a fallback aproximado. | — |
| Graphiti Self-Hosted Certification | Memoria temporal en grafo | Local | Blocked | `C:\AI_WORKFLOW\11_LAB\graphiti-experiment` | 7474, 7687 | Ruta elegida por decision del fundador el 2026-07-20: Neo4j local + `graphiti-core 0.29.2`, sin `ZEP_API_KEY`; reintento funcional real del 2026-07-21: `build_indices_and_constraints()` dejo indices `ONLINE` en Neo4j local, pero `add_episode` volvio a bloquearse por `Rate limit exceeded` de OpenAI; continuacion `codex exec` del 2026-07-21 abortada antes de Neo4j por politica fija: `FREE_RAM_GB=3.54` y stack extra activo en `127.0.0.1:11434`; contenedor de laboratorio `graphiti-neo4j-lab`, uso bajo demanda | cuando se resuelva el rate limit de OpenAI |
| Agentic Radar | Escaneo OWASP para agentes | Local | OK | `C:\AI_WORKFLOW\11_LAB\tool-stack\python-memory\.venv\Scripts\agentic-radar.exe` | n/a | Reportes reales en `C:\AI_WORKFLOW\11_LAB\security-audit\agentic-radar`; `n8n` mostro `5` hallazgos `LLM01/T6`, LangGraph no mostro esos hallazgos en su HTML generado | — |
| PostgresAI / postgres-checkup | Checkup de Postgres | Local | Partial | `C:\AI_WORKFLOW\11_LAB\security-audit\postgres-checkup` | 5432 | 2026-07-21: el tag viejo `registry.gitlab.com/postgres-ai/postgres-checkup:latest` sigue roto (`go1.11.5` + `go get` sin pinning -> errores `cmp` / `iter` / `slices`); el tag oficial actual `postgresai/postgres-checkup:latest` genero `artifacts\lifeos_dev\md_reports\20260721001_2026_07_21T01_02_31_+0000\0_Full_report.md`. Quedan checks SSH-dependientes y `K000` omitidos por falta de SSH y `pg_stat_statements` | 2026-09-19 |
| Graphify Operativo | Acelerador de navegacion para desarrollo | Local | OK | `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\GRAPHIFY` | n/a | Grafo operativo sin proceso residente: `query`, `path` y `explain` leen `graph.json` y terminan; fuerte para hubs, imports y estructura de modulo; no es fuente de verdad arquitectonica ni sustituto de verificacion manual en flujos runtime, pagos, escrow o auth; benchmark del 2026-07-20: `5/5` correcto con ayuda, pero mas lento que el metodo manual en tareas ya conocidas | — |
| Codex-Claude Bridge | Cola auditable de handoffs rutinarios | Local | Partial | `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE` | n/a | Mecanismo elegido hoy: cola en disco con JSON + JSONL; elimina el copy-paste del contenido entre agentes, pero la automatizacion completa sigue limitada por falta de una CLI/API estable de Claude accesible desde PowerShell externo | 2026-09-19 |
| Codex Plugin oficial para Claude Code | Handoff in-session Claude -> Codex | Local/Online | Partial | `<WINDOWS_HOME>\.claude\plugins\cache\openai-codex\codex\1.0.6` | n/a | 2026-07-21: plugin `codex@openai-codex` `1.0.6` instalado en scope local para `C:\AI_WORKFLOW`, con marketplace declarado en [settings.local.json](/C:/AI_WORKFLOW/.claude/settings.local.json). `/codex:setup` paso dentro de Claude Code y el runtime oficial (`codex-companion.mjs task`) completo una tarea read-only real, pero el handoff por slash command `/codex:rescue` sigue fallando en este host Windows por errores de Git Bash/MSYS fork. Mantener como complemento del bridge manual, no como reemplazo; ver `08_REPORTS\TECH_RADAR\CODEX_PLUGIN_OFICIAL_2026-07-21.md`. | 2026-09-19 |
| Ponytail | Plugin de comportamiento YAGNI/minimalismo para Claude Code | Local | OK | `C:\AI_WORKFLOW\11_LAB\ponytail_unpack_20260721\ponytail-4.8.4` | n/a | 2026-07-21: fuente oficial `DietrichGebert/ponytail` `v4.8.4` descargada al workspace e instalada como `ponytail@ponytail` en scope local de Claude Code. El alta directa por GitHub fallo en este host Windows por SSH/MSYS fork, asi que el marketplace local se apunto al artefacto oficial extraido en `11_LAB`. Medicion real propia sobre `claude-sonnet-5` y una micro-tarea de edicion repetida (`n=5` por brazo): `-0.76%` costo, `-0.55%` tokens reportados y `+7.22%` tiempo con Ponytail ON vs OFF; mantener instalado pero no always-on por defecto. Ver `08_REPORTS\TECH_RADAR\PONYTAIL_MEDICION_REAL_2026-07-21.md`. | 2026-10-19 |
| skills.sh | Gestor/inventario de agent skills | Local/Online | OK | `npx skills` (ejecución efímera) | n/a | 2026-07-22: CLI oficial comprobada por `npx`; `list --global --json` detectó Herdr, Grill Me/familia, Graphify y las nuevas `watch`/`notebooklm`. Gestiona fuentes y rutas de sus propias instalaciones, pero las skills manuales aparecen sin origen y un `codex-build` preexistente fue omitido por YAML inválido. Telemetría desactivada en esta ejecución. Ver `08_REPORTS\TECH_RADAR\SKILLS_VIDEO_NOTEBOOKLM_2026-07-21.md`. | 2026-10-22 |
| Claude Video (`watch`) | Extracción de frames + transcripción para análisis de video | Local/Online | OK, condicional | `<WINDOWS_HOME>\.agents\skills\watch` | n/a | 2026-07-22: `bradautomates/claude-video` instalado con skills.sh para Claude Code/Codex; dependencias `FFmpeg 8.1.2` y `yt-dlp 2026.7.4`. Prueba real TEDx: 4 JPEG + 8 segmentos timestamped desde captions en `11_LAB\claude_video_smoketest_20260722_run3`. Videos sin captions necesitan clave Groq/OpenAI con cuota; Whisper OpenAI devolvió 429 de cuota en un run previo, por lo que esa vía no está certificada. | 2026-10-22 |
| NotebookLM-py | CLI/skill no oficial para NotebookLM | Local/Online | Pending founder action | `<WINDOWS_HOME>\.local\bin\notebooklm.exe` | n/a | 2026-07-22: `notebooklm-py[browser]` 0.7.3 instalado con pipx y skill instalada para Claude Code/Codex. No existe sesión (`auth check --test`: falta `storage_state.json`); no se hizo login ni se leyeron cookies. Requiere login Google/cookies o token; automatiza superficie web/RPC no oficial y es frágil ante expiración, anti-abuso o cambios internos. No usar con datos sensibles ni cuenta principal; requiere una cuenta de prueba y acción explícita del fundador. Ver `08_REPORTS\TECH_RADAR\SKILLS_VIDEO_NOTEBOOKLM_2026-07-21.md`. | tras prueba autorizada |
| Grill Me / Grill With Docs | Skill de discovery antes de ejecutar | Local/Online | OK | `C:\AI_WORKFLOW\11_LAB\grill-me_eval_20260721\workspace-skills` | n/a | 2026-07-21: familia oficial confirmada en `mattpocock/skills`; `grill-me` y `grill-with-docs` son wrappers finos sobre `grilling` y `domain-modeling`. Instaladas en el workspace y copiadas a `<WINDOWS_HOME>\.claude\skills` para runtime real en Claude Code. Prueba real sobre `11_LAB\crewai-experiment`: inspeccionaron la carpeta y preguntaron aclaraciones concretas antes de proponer plan. Ver `08_REPORTS\TECH_RADAR\GRILL_ME_2026-07-21.md`. | — |
| Grill Me Codex | Overlay de plan hardening + review adversario con Codex | Local/Online | Partial | `C:\AI_WORKFLOW\11_LAB\grill-me_eval_20260721\workspace-skills` | n/a | 2026-07-21: familia separada confirmada en `chaseai-yt/grill-me-codex`; incluye `grill-me-codex`, `grill-with-docs-codex`, `codex-review` y `codex-build`. Act 1 real en Claude Code: pregunto aclaraciones concretas antes de planear. Act 2 automatico Claude -> Codex tuvo friccion real en este host Windows por Git Bash/MSYS fork y permisos, pero el review read-only manual de Codex sobre el `PLAN.md` generado devolvio `VERDICT: REVISE` con 6 objeciones concretas, asi que la capa no es cosmetica. Ver `08_REPORTS\TECH_RADAR\GRILL_ME_2026-07-21.md`. | 2026-09-19 |
| OpenCode (CLI oficial + Desktop) | Agente de codigo terminal/desktop | Online/Local | OK | CLI: `<WINDOWS_HOME>\AppData\Roaming\npm\opencode.cmd`; Desktop: `<WINDOWS_HOME>\AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe` | dinamico (Desktop observado: 58840) | 2026-07-21: `opencode-ai@1.18.4` instalado globalmente desde el paquete oficial y `opencode --version` responde. Pruebas reales read-only sobre este workspace con `opencode run --agent plan --dir C:\AI_WORKFLOW` leyeron y resumieron `00_COMMAND_CENTER\TOOL_REGISTRY.md` (modelo reportado: `z-ai/glm-5.2`). Desktop sigue usando un sidecar protegido: genera un UUID por arranque como password de HTTP Basic Auth; por eso `GET /` y `/health` sin credenciales devolvieron `401`. No automatizar contra ese sidecar: invocar la CLI. Proceso y evidencia en `08_REPORTS\TECH_RADAR\OPENCODE_INTEGRACION_2026-07-21.md`. | — |
| CrewAI Lab | Framework experimental multiagente | Local | Rol distinto pendiente | `C:\AI_WORKFLOW\11_LAB\crewai-experiment` | n/a | No compite como RAG: puede servir en el futuro para orquestar roles de investigacion, auditoria y redaccion sobre evidencia ya recuperada por `Tchasky Operational RAG`. Hoy no es operativo: `0/2` briefs (`B3.1`, `E1.1`) pasan la citacion estricta; dejó de inventar rutas, pero emitió anchors Markdown en vez de paths reales del `sourcePacket`. No optimizar en esta ronda. Pendiente futuro separado: disenar y certificar un workflow multiagente con gate determinista de citas antes de evaluar su adopcion. | cuando se priorice una iniciativa multiagente separada |
| GitHub Actions / CodeQL cloud | CI remota | Online | Blocked | `\\wsl$\Ubuntu\home\<USER>\<PRIVATE_PROJECT>\.github\workflows\ci.yml` | n/a | Workflow preparado, pero el repo vivo no tiene remoto GitHub; la ejecucion cloud queda bloqueada hasta decidir si se publica el repositorio | cuando se configure remoto GitHub |
| PostHog self-hosted | Analitica de producto | Local | Partial | `Docker: posthog/posthog` + `<HOME>/ai_tool_stack/posthog-hobby` | 3800 | Responde cuando arranca aislado, pero con `lifeos_postgres` y `lifeos_redis` residentes hundio la RAM libre hasta `5.6 GB`; usar solo bajo demanda y certificar en sesiones aisladas | 2026-09-19 |
| GitHub CLI | Utilidad dev | Online/Local | OK | `C:\Program Files\GitHub CLI\gh.exe` | n/a | Version 2.96.0 | — |
| PowerShell 7 | Shell moderna | Local | OK | `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.3.0_x64__8wekyb3d8bbwe\pwsh.exe` | n/a | Version 7.6.3 | — |
| `milestones.py` | Hitos del proyecto (§28) | Local | OK | `.ai/bin/milestones.py` | n/a | Un hito es un corte sobre `EVENTS.jsonl`, no un formato paralelo. Uso: `python .ai/bin/milestones.py ver --ultimos 10` y `patrones --ultimos 10`. **Es lo mas barato que se puede correr al retomar una sesion** — dice que se viene repitiendo sin leer un handoff entero. Creado por el carril D el 2026-08-13 | 2026-09-13 |
| `registry_check.py` | Validador de los registros (§18-20) | Local | OK | `.ai/bin/registry_check.py` | n/a | Valida los seis YAML de `.ai/registry/` (`AGENTS`, `CAPABILITIES`, `MCP`, `MODELS`, `PLUGINS`, `SKILLS`) sobre el parser que ya tenia `reality.py`, **sin dependencias nuevas**. Creado por el carril D el 2026-08-13 | 2026-09-13 |
| `eval_rag.py` | Medicion de recuperacion del RAG | Local | OK | `02_LOCAL_AI/ANYTHINGLLM/eval_rag.py` | n/a | Corre **en Windows**, no en contenedor. Mide recall@1/3/5 y MRR sobre `rag_golden_set.json` en tres escenarios (control, sin `lote_*`, sin `lote_*` + respaldo + duplicados). Compara por `metadata.docSource` completo: **nunca por titulo**, hay 24 documentos llamados `README`. Medicion vigente 2026-08-13: 58,3 % control, 75,0 % sin `lote_*` | 2026-09-13 |

## Politica de uso bajo demanda (2026-07-20)

| Herramienta pesada | Modo de uso | Encendido | Apagado | Nota |
|---|---|---|---|---|
| Ollama | Bajo demanda, no residente | [start_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\start_lab_stack.ps1) con `-IncludeOllama` o arranque manual | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Solo se enciende para pruebas activas de modelos |
| Hermes Agent | Residente por pedido del fundador; apagar manualmente si no se usa | `docker compose up -d` en `C:\AI_WORKFLOW\11_LAB\tool-stack\docker\hermes-agent` | `docker compose stop` en `C:\AI_WORKFLOW\11_LAB\tool-stack\docker\hermes-agent` | Puerto `8642`; hoy usa `Ollama` local con `qwen3.5:9b`; Gmail/Calendar/Drive read-only aprobados el 2026-07-22; dependencias Google persistidas bajo `data\.local` |
| Open WebUI | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `3100` |

## Auditor de respaldo — certificación comparable 2026-07-22

Evidencia: `06_AGENT_FRAMEWORK/BACKUP_AUDITOR/CERTIFICATION_SUITE_2026-07-22/RESULTADOS.md`.

- **OpenCode:** resultado provisional líder; verificó A/B mediante herramientas, B 3/3 y escaló el borrado de D. No promover a “certificado” aún: el caso C de esta ronda fue invalidado por una premisa de discrepancia no real.
- **qwen2.5-coder:7b (Ollama):** fallback local sólo con gateway/citas validadas; fabricó evidencia en B/C cuando se invocó sin filesystem.
- **OpenRouter / DeepSeek V3.2:** no apto aún para auditoría autónoma; fabricó evidencia en B/C y consumió USD 0.001863151 en cuatro requests. Requiere gateway read-only, validador de citas y presupuesto aprobado.
- **Kimi Code CLI:** bloqueado; `kimi -p test` indicó que no hay modelo configurado y requiere `/login`. Sin prueba simulada.
| AnythingLLM | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `3110` |
| n8n | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `5678` |
| Qdrant | Bajo demanda, no residente | `-Profiles rag-qdrant` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `6333` |
| Neo4j / Graphiti | Bajo demanda, no residente | `-Profiles graph-rag` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puertos `7474` y `7687` |
| Weaviate | Bajo demanda, no residente | `-Profiles rag-weaviate` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `8180` |
| Metabase | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `3200` |
| PgHero | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `3710` |
| Unleash | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `4242` |
| Plane | Bajo demanda, no residente | `-Profiles management` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puertos `3210` y `3211` |
| PostHog | Bajo demanda, no residente | `-Profiles observability` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto `3800`; muy pesado en RAM |
| Sentry self-hosted | Bajo demanda, no residente | `-Profiles observability` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Puerto validado `3900`; muy pesado en RAM |
| SeaweedFS auxiliar | Bajo demanda, no residente | `-Profiles observability` | [stop_lab_stack.ps1](C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\stop_lab_stack.ps1) | Auxiliar de observabilidad, no dejar residente |

## Certificación estricta

Artefacto resumen de esta ronda: `C:\AI_WORKFLOW\08_REPORTS\STRICT_CERTIFICATION_2026-07-19.json`

### n8n

Qué se probó:

- Reinicio completo del contenedor `n8n-local-automation`.
- Verificación de persistencia/reactivación de los 4 workflows vía `C:\AI_WORKFLOW\03_AUTOMATION\N8N\data\database.sqlite`.
- Falla real reversible: parada temporal de `lifeos_postgres` y observación de la siguiente corrida del monitor.
- Disparo real del webhook `tchasky-test-runner` y revisión del reporte generado.

Resultado exacto:

- `4/4` workflows siguieron activos tras el reinicio: `AIW Health Check Periodic`, `AIW Tchasky Stack Monitor`, `AIW Tchasky Test Runner`, `AIW Banco Count Sync`.
- El monitor detectó correctamente la caída simulada de Postgres en la siguiente ventana (`Failing services: postgres`) y el contenedor volvió a `healthy` ~`10s` después del `docker start`.
- El test runner por webhook ejecutó la suite real de backend y dejó reporte verificable con `144/144 passed`.

Propuesta de rol definitivo:

- Aprobarlo como capa de operaciones continuas del framework: health checks, alertas locales, test orchestration y sincronizaciones documentales acotadas. La evidencia de resiliencia ya es suficiente para ese rol.

### AnythingLLM

Qué se probó:

- Batería de `10` preguntas ya cerradas de TIER `0/1/2` sobre el workspace `tchasky-estado-vivo`, sin pistas extra y contra corpus real.
- Revisión manual de exactitud factual y de la calidad real de las fuentes citadas/recuperadas.

Resultado exacto:

- `4/10` correctas con fuente real (`40%`): `Q1 B7.7`, `Q6 B12.1`, `Q7 B8.1`, `Q10 E1.1`.
- `6/10` incorrectas: `admin_logs`, filtro admin por `execution_mode`, `50` invites listos, expiración de rutas, ubicación exacta antes de aceptar y take rate oficial.
- El retrieval sí recuperó documentos reales del vault vivo, pero varias respuestas aterrizaron mal el estado vigente aun con fuente disponible.

Propuesta de rol definitivo:

- Supersedida por `Tchasky Operational RAG` (`10/10`): no aporta un rol RAG distinto que justifique optimizarla ahora. Mantenerla solo como antecedente histórico de discovery/reindexación; no es primera parada para TIER `3+` y no tiene trabajo pendiente salvo que surja un caso de uso no cubierto por el RAG operativo.

### Ollama modo agente / API

Qué se probó:

- Un último intento no interactivo exclusivamente por HTTP contra `http://127.0.0.1:11434/api/generate`.
- Resumen de un archivo real corto del corpus (`C:\AI_WORKFLOW\01_OBSIDIAN\VAULT_TEMPLATE\03_Tchasky\PROJECT_BRIEF.md`) sin CLI interactivo ni internet.

Resultado exacto:

- La llamada HTTP respondió correctamente en `1.351s` con `done_reason = stop`.
- El subcomando `ollama agent` sigue bloqueado como vía automatizable: abre el TUI y no consume `stdin` en este entorno.

Propuesta de rol definitivo:

- Aprobar `Ollama` como asistente local simple vía API para tareas one-shot offline de bajo costo. No aprobar `ollama agent` CLI como superficie operativa mientras siga bloqueado en modo TUI.

### qwen3.5:9b

Qué se probó:

- Prueba final decisiva distinta a código y resumen: razonamiento de negocio sobre `E4.1` usando contexto real del corpus, con el mismo prompt para `qwen2.5-coder:7b` y `qwen3.5:9b`.

Resultado exacto:

- `qwen2.5-coder:7b`: `6.75s`, `done_reason = length`, `891` caracteres de salida, pero desviado del foco de `E4.1`.
- `qwen3.5:9b`: `29.661s`, `done_reason = length`, `0` caracteres de salida efectiva.
- Como la regla de esta ronda era “si gana aquí, se le asigna ese rol”, el modelo no ganó la prueba final.

Propuesta de rol definitivo:

- Mantenerlo instalado pero sin rol asignado y sin reintento operativo hasta nueva versión del modelo. No hay evidencia suficiente para darle un nicho mejor que `qwen2.5-coder:7b` en este hardware.

### LangGraph

Qué se probó:

- `4` casos reales adicionales sobre el repo vivo y la DB viva:
- Positivo: `b7.5_admin_actions`.
- Negativo: `b7.5_admin_logs`.
- DB viva: `b17.6` (`SELECT COUNT(*) || '|' || COUNT(*) FILTER (WHERE is_active) FROM beta_invites;`).
- Multi-fuente: `b12.5`.

Resultado exacto:

- `4/4` coincidieron con el veredicto manual (`100%`).
- El caso negativo pasó sin falso positivo: el grafo contradijo correctamente la existencia de `admin_logs`.
- El caso con DB viva leyó `0|0` y devolvió contradicción correcta para “ya hay 50 invites listos”.

Propuesta de rol definitivo:

- Aprobarlo como candidato fuerte para pipeline auditado de preguntas `[VERIFICAR]`, con revisión humana previa antes de activarlo sobre TIER `3+`. Es la herramienta que mejor mantuvo el estándar de evidencia en esta ronda.

### CrewAI

Qué se probó:

- Reescritura del lab para usar `sourcePacket` real completo por pregunta y exigir citas solo de rutas exactas permitidas.
- Dos preguntas `[DECIDIR]` adicionales: `B3.1` y `E1.1`.
- Validación automática posterior de si el brief final citó paths reales del packet o, en su defecto, escribió `fuente no disponible`.

Resultado exacto:

- `0/2` pasan el criterio estricto de citación (`0%`).
- En ambos casos dejó de inventar rutas Windows inexistentes, pero tampoco citó paths reales del packet: cayó en anchors Markdown internos (`#...`) y no usó `fuente no disponible`.
- Calidad narrativa parcial, pero incumplimiento estructural del requisito mínimo de trazabilidad.

Propuesta de rol definitivo:

- No aprobarlo para briefs operativos de TIER `3+`. No está supersedido como concepto: su rol distinto potencial es una orquestación multiagente (`investigación -> auditoría -> redacción`) sobre evidencia aportada por `Tchasky Operational RAG`. Dejarlo como sandbox hasta una iniciativa separada que implemente y certifique un gate determinista de citas de paths reales.
