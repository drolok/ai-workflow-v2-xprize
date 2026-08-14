# Automation Setup

Ultima actualizacion: 2026-07-21

## Objetivo

Dejar una capa de automatizacion manual y segura en `C:\AI_WORKFLOW\03_AUTOMATION`, limitada a lectura, generacion de reportes y nuevos artefactos. En esta fase no se activan cron jobs, Task Scheduler ni workflows automaticos en background.

## Decision sobre n8n

- Decision final: instalar `n8n` por Docker, no por `npm`
- Motivo practico:
  - La documentacion oficial de `n8n` recomienda Docker para la mayoria de despliegues self-hosted.
  - La opcion por `npm` es valida para local, pero incluso su propia documentacion asume Docker para servicios auxiliares.
  - En este equipo ya existe Docker estable y operativo, asi que Docker evita tocar dependencias globales de Node o el `PATH`.
- Estado final:
  - Contenedor: `n8n-local-automation`
  - URL: `http://localhost:5678`
  - Bind: `127.0.0.1:5678 -> 5678`
  - Datos: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\data`
  - Workflows activos por defecto: ninguno

Prueba real de n8n:

```text
docker ps -> n8n-local-automation   Up ...   127.0.0.1:5678->5678/tcp
curl.exe -i http://localhost:5678/ -> HTTP/1.1 200 OK
curl.exe -i http://localhost:5678/rest/settings -> HTTP/1.1 200 OK
```

Observacion:

- `n8n` deja una advertencia de task runner interno por falta de Python dentro del contenedor. No bloquea Fase 5 porque no hay workflows activos ni despliegue en produccion.

## Estructura creada

- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS`
- `C:\AI_WORKFLOW\03_AUTOMATION\WATCHERS`
- `C:\AI_WORKFLOW\03_AUTOMATION\N8N`

## Scripts

### `health_check.ps1`

Que hace:

- Revisa Git, Python, Node.js, Docker, Ollama, LM Studio, Open WebUI, AnythingLLM y `n8n`
- Genera reporte Markdown y JSON en `C:\AI_WORKFLOW\08_REPORTS\HEALTH_CHECKS`

Como correrlo:

```powershell
& 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\health_check.ps1'
```

Output real:

```text
Git           OK     git version 2.55.0.windows.2
Python        OK     Python 3.13.0
Node.js       OK     v24.18.0
Docker Engine OK     29.5.2
Ollama        OK     ollama version is 0.32.1
LM Studio     OK     LM Studio (PID 34060)
Open WebUI    OK     HTTP 200; listener: com.docker.backend (PID 29956)
AnythingLLM   OK     HTTP 200; listener: com.docker.backend (PID 29956)
n8n           OK     Up 6 minutes|127.0.0.1:5678->5678/tcp|docker.n8n.io/n8nio/n8n:latest; listener: com.docker.backend (PID 29956)
```

Artefactos:

- `C:\AI_WORKFLOW\08_REPORTS\HEALTH_CHECKS\health_check_20260718_141525.md`
- `C:\AI_WORKFLOW\08_REPORTS\HEALTH_CHECKS\health_check_20260718_141525.json`
- `C:\AI_WORKFLOW\08_REPORTS\HEALTH_CHECKS\latest_health_check.json`

### `scan_ports.ps1`

Que hace:

- Escanea puertos vigilados y reporta proceso, PID, direccion y path
- Acepta puertos extra con `-AdditionalPorts`

Como correrlo:

```powershell
& 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\scan_ports.ps1' -AdditionalPorts 5678
```

Output real:

```text
1234  LISTEN  LM Studio           34060
3100  LISTEN  com.docker.backend  29956
3101  LISTEN  com.docker.backend  29956
5678  LISTEN  com.docker.backend  29956
6379  LISTEN  com.docker.backend  29956
6379  LISTEN  wslrelay            36480
11434 LISTEN  ollama              33552
```

Artefactos:

- `C:\AI_WORKFLOW\08_REPORTS\PORT_SCANS\port_scan_20260718_141418.md`
- `C:\AI_WORKFLOW\08_REPORTS\PORT_SCANS\port_scan_20260718_141418.json`
- `C:\AI_WORKFLOW\08_REPORTS\PORT_SCANS\latest_port_scan.json`

### `repo_summary.py`

Que hace:

- Resume estructura, volumen, extensiones y archivos mas grandes de un repo o carpeta
- Es solo lectura

Como correrlo:

```powershell
python 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\repo_summary.py' 'C:\AI_WORKFLOW'
```

Output real:

```text
Root: C:\AI_WORKFLOW
Files: 315
Directories: 106
Total size: 6.2 GB
Report: C:\AI_WORKFLOW\08_REPORTS\REPO_SUMMARIES\repo_summary_AI_WORKFLOW_20260718_141422.md
```

### `generate_context_pack.py`

Que hace:

- Genera un context pack Markdown desde una plantilla y datos del proyecto
- En la prueba usa `PROJECT_TEMPLATE` como base sintetica

Como correrlo:

```powershell
python 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\generate_context_pack.py' `
  --project-root 'C:\AI_WORKFLOW\07_PROJECTS\PROJECT_TEMPLATE' `
  --template 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\context_pack_template.md' `
  --data-json 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\context_pack_data_example.json'
```

Output real:

```text
Project root: C:\AI_WORKFLOW\07_PROJECTS\PROJECT_TEMPLATE
Output: C:\AI_WORKFLOW\07_PROJECTS\PROJECT_TEMPLATE\CONTEXT_PACKS\CP_01_AUTOGEN_20260718_141419.md
Project name: PROJECT_TEMPLATE
Markdown files counted: 7
```

### `update_current_state.py`

Que hace:

- Lee los JSON mas recientes de `health_check` y `scan_ports`
- Inserta o actualiza un bloque administrado en `CURRENT_STATE.md`
- Hace backup antes de sobrescribir y muestra diff

Como correrlo:

```powershell
python 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\update_current_state.py'
```

Output real:

```text
Backup: C:\AI_WORKFLOW\00_COMMAND_CENTER\CURRENT_STATE.backup_20260718_141611.md
Updated: C:\AI_WORKFLOW\00_COMMAND_CENTER\CURRENT_STATE.md
Health JSON: C:\AI_WORKFLOW\08_REPORTS\HEALTH_CHECKS\latest_health_check.json
Ports JSON: C:\AI_WORKFLOW\08_REPORTS\PORT_SCANS\latest_port_scan.json
```

Tambien mostro diff real agregando el bloque `Automation Snapshot`.

### `document_ingest_pipeline.py`

Que hace:

- Envuelve Docling, whisper.cpp y Tesseract sobre archivos de `00_Inbox`
- Usa carpetas por corrida para evitar sobrescrituras
- Permite filtrar inputs con `--glob` y `--exclude-glob`

Como correrlo:

```powershell
python 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\document_ingest_pipeline.py' `
  --source-dir 'C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox' `
  --glob 'phase4_*' `
  --exclude-glob '*retry*' `
  --exclude-glob '*.html' `
  --run-label 'phase5_phase4_curated'
```

Output real:

```text
Source dir: C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\00_Inbox
Run label: phase5_phase4_curated
Markdown dir: C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\ingest_phase5_phase4_curated
Processed dir: C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Processed\ingest_phase5_phase4_curated
docling: OK
whisper: OK
ocr: OK
```

Artefactos:

- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Markdown_Output\ingest_phase5_phase4_curated`
- `C:\AI_WORKFLOW\04_DOCUMENT_PROCESSING\Processed\ingest_phase5_phase4_curated\manifest.md`

### `agent_handoff_template.py`

Que hace:

- Genera un handoff Markdown desde plantilla y datos JSON
- Queda listo para reutilizarse en Fase 6

Como correrlo:

```powershell
python 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\agent_handoff_template.py' `
  --template 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\agent_handoff_template.md' `
  --data-json 'C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\agent_handoff_data_example.json' `
  --project-name 'AI_WORKFLOW_PHASE5' `
  --objective 'Leave automation artifacts ready for Fase 6.'
```

Output real:

```text
Template: C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\agent_handoff_template.md
Output: C:\AI_WORKFLOW\08_REPORTS\AGENT_HANDOFFS\agent_handoff_20260718_141419.md
Project name: AI_WORKFLOW_PHASE5
Objective: Leave automation artifacts ready for Fase 6.
```

## Plantillas

- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\context_pack_template.md`
- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\agent_handoff_template.md`
- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\context_pack_data_example.json`
- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\templates\agent_handoff_data_example.json`

## Seguridad aplicada

- No se crearon tareas programadas
- No se activaron watchers en background
- No se tocaron credenciales existentes
- No se modifico `PATH`
- `document_ingest_pipeline.py` usa salidas por corrida y filtros de entrada
- `update_current_state.py` hace backup y muestra diff antes de escribir

## Observaciones

- La primera corrida de `health_check.ps1` requirio un ajuste menor por `Set-StrictMode`.
- `update_current_state.py` requirio tolerancia a BOM UTF-8 producido por PowerShell 5.1.
- `document_ingest_pipeline.py` recibio filtros `--glob` y `--exclude-glob` para no mezclar audios de calibracion o PDFs de retry con el set curado de Fase 4.

## n8n Learning Lab - 2026-07-19

La decision original de Fase 5 fue dejar `n8n` instalado pero sin workflows activos. Este laboratorio agrega 3 workflows reales y un bridge local para que el contenedor pueda ejecutar scripts del host sin tocar el repo real de Tchasky.

### Bridge local usado por n8n

- Host runner: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\host_runner.py`
- Start script: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\start_host_runner.ps1`
- Stop script: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\stop_host_runner.ps1`
- Puerto host runner: `127.0.0.1:8765`
- Log: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\host_runner.log`
- Secreto del bridge: variable de entorno `AIW_N8N_RUNNER_TOKEN`
- Los 4 workflows de `n8n` lo consumen via `{{$env.AIW_N8N_RUNNER_TOKEN}}`

Endpoints expuestos al contenedor:

- `GET /health`
- `POST /run/health-check`
- `POST /run/scan-ports`
- `POST /run/test-runner`
- `GET /monitor/tchasky`

### Workflows activos

1. `AIW Health Check Periodic`
   - Definicion: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\workflows\health_check_periodic.json`
   - Intervalo: cada `30` minutos
   - Flujo: `Schedule Trigger -> Run Health Check -> Run Port Scan`
   - Resultado: genera nuevos artefactos en `C:\AI_WORKFLOW\08_REPORTS\HEALTH_CHECKS` y `C:\AI_WORKFLOW\08_REPORTS\PORT_SCANS`

2. `AIW Tchasky Test Runner`
   - Definicion: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\workflows\test_runner_webhook.json`
   - Trigger: webhook manual
   - Flujo: `Webhook -> Run API Tests`
   - Endpoint esperado por n8n: `POST /webhook/tchasky-test-runner`

3. `AIW Tchasky Stack Monitor`
   - Definicion: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\workflows\tchasky_stack_monitor.json`
   - Intervalo: cada `5` minutos
   - Flujo: `Schedule Trigger -> Monitor Stack`
   - Revisa: `postgres`, `redis` y `http://localhost:3001/health`

### Evidencia real

- El `host_runner.log` confirma ejecuciones periodicas reales:
  - `POST /run/test-runner` a las `12:03:10`
  - `POST /run/health-check` y `POST /run/scan-ports` a las `12:31` y `13:00`
  - `GET /monitor/tchasky` cada 5 minutos entre `12:05` y `13:10`
- El workflow de tests genero:
  - `C:\AI_WORKFLOW\08_REPORTS\N8N\TEST_RUNS\test_run_20260719_120256.md`
  - `C:\AI_WORKFLOW\08_REPORTS\N8N\TEST_RUNS\test_run_20260719_120256.json`
- Resultado real del test runner:
  - `144/144` tests pasando
  - Duracion real observada: `13.53s`
- Verificacion manual del monitor al cierre de esta sesion:

```json
{
  "generated_at": "2026-07-19 13:29:09",
  "status": "ok",
  "checks": {
    "postgres": { "ok": true, "detail": "connected" },
    "redis": { "ok": true, "detail": "connected" },
    "api": { "ok": true, "detail": "200" }
  }
}
```

### Como probarlos

1. Iniciar o verificar el host runner:

```powershell
& 'C:\AI_WORKFLOW\03_AUTOMATION\N8N\start_host_runner.ps1'
```

`start_host_runner.ps1` toma `AIW_N8N_RUNNER_TOKEN` desde la env de proceso/usuario si no se pasa `-Token`.

2. Confirmar salud del bridge:

```powershell
$token = [Environment]::GetEnvironmentVariable('AIW_N8N_RUNNER_TOKEN', 'User')
$headers = @{ 'X-Runner-Token' = $token }
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -Headers $headers
```

3. Probar el stack monitor sin esperar al scheduler:

```powershell
$token = [Environment]::GetEnvironmentVariable('AIW_N8N_RUNNER_TOKEN', 'User')
$headers = @{ 'X-Runner-Token' = $token }
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/monitor/tchasky' -Headers $headers
```

4. Probar el test runner:
   - Desde la UI de `n8n`, lanzar el webhook de `AIW Tchasky Test Runner`
   - O disparar el webhook correspondiente desde el propio contenedor/UI local
   - Verificar que aparezca un nuevo `test_run_*.md` en `08_REPORTS\N8N\TEST_RUNS`

### Nota operativa

- `latest_alert.md` conserva una alerta historica de una corrida temprana donde el chequeo HTTP de API todavia estaba afinandose; no refleja el estado actual del monitor.
- El estado real vigente al cierre de esta sesion es `status = ok` para `postgres`, `redis` y `api`.

## Actualizacion operativa - 2026-07-19 tarde

El laboratorio paso de `3` a `4` workflows activos reales en `n8n`, sin poner nada destructivo en produccion.

### Workflow activo nuevo

4. `AIW Banco Count Sync`
   - Definicion: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\workflows\banco_count_sync.json`
   - Intervalo: cada `5` minutos
   - Flujo: `Schedule Trigger -> Sync Banco Counts`
   - Endpoint usado por el contenedor: `POST http://host.docker.internal:8765/run/sync-banco-counts`
   - Funcion operativa: mantener sincronizado el conteo de `BANCO_PREGUNTAS_ESTADO.md` con el banco fuente consolidado

### Script y estado asociados

- Script invocado por el workflow:
  - `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\sync_banco_counts.py`
- Estado persistente:
  - `C:\AI_WORKFLOW\03_AUTOMATION\WATCHERS\banco_count_sync_state.json`
- Ultimo reporte:
  - `C:\AI_WORKFLOW\08_REPORTS\N8N\BANCO_SYNC\latest_banco_sync.json`

### Evidencia real del cuarto workflow

- Conteo real sincronizado al domingo 19 de julio de 2026:
  - `146` total
  - `29` cerradas
  - `39` abiertas de verificacion
  - `78` pendientes de decision
- `latest_banco_sync.json` confirmo:
  - `"ok": true`
  - `"changed": false`
  - `"updated_file": false`
- `banco_count_sync_state.json` guardo hashes del banco fuente y del estado vivo para detectar cambios reales antes de reescribir

### Estado final de n8n

- `n8n` ya no queda solo como app instalada para configurar despues
- Queda validado como capa de operaciones continuas del framework con cuatro roles concretos:
  - salud periodica
  - monitoreo del stack Tchasky
  - disparo controlado de tests
  - sincronizacion automatica del conteo del banco de preguntas
