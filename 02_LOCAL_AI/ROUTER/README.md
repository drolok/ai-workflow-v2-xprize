# Enrutador de respuestas del buscador de notas

Cadena: Gemini → Ollama local (`qwen2.5:3b-instruct`) → NVIDIA. El router
expone el dialecto OpenAI en `POST /v1/chat/completions`; no modifica embeddings
ni el almacenamiento de AnythingLLM.

## Tiempos y criterio de respaldo

- Sonda exacta: `Responde exactamente: ROUTER_NVIDIA_OK`.
- Remotos (Gemini y NVIDIA): 8 segundos por intento. El objetivo es
  abandonar pronto un proveedor que no responde y dar paso al respaldo local.
- Respaldo local inmediato: 120 segundos (`ROUTER_LOCAL_TIMEOUT_SECONDS`). Es
  un margen de red y ejecución, no el objetivo de latencia; el benchmark de
  TASK-96 exige menos de 20 segundos y el modelo configurado lo cumplió.
- Válida: HTTP 2xx y texto no vacío. Se acepta `message.content` o, si ese
  campo viene vacío, texto en `message.reasoning`, `reasoning_content` o
  `analysis`; el router lo normaliza a `message.content` para AnythingLLM.
- Frecuencia: al iniciar y cada 300 segundos. Si una sonda o consulta falla,
  NVIDIA se salta hasta la siguiente sonda satisfactoria.

NVIDIA lee su clave desde `/run/secrets/nvidia_api_key`, montada como archivo de
solo lectura por el compose.

## Cómo volver a agregar Claude

El código del proveedor se conserva en `anthropic_provider()` pero Claude no
forma parte de `providers()` porque actualmente no hay una clave. Cuando exista
una, estos tres cambios bastan para restaurar el eslabón al final de la cadena:

1. En `environment` de `docker-compose.yml`, agregar la variable
   `ROUTER_ANTHROPIC_KEY_FILE: /run/secrets/anthropic_api_key`.
2. En `volumes`, montar el archivo de credenciales en esa ruta con `:ro`.
3. En la lista devuelta por `providers()` en `router.py`, agregar
   `anthropic_provider(),` después de `nvidia,` y recrear el contenedor.

El valor de la clave debe permanecer fuera del repositorio y nunca debe
escribirse en el compose ni en los registros.

Los logs JSONL contienen únicamente proveedor, milisegundos, resultado y motivo;
no incluyen claves, prompts ni respuestas.

## Puerto persistente de Ollama

El compose usa `host.docker.internal:11435` de forma explícita. Los scripts y
laboratorios que se ejecutan en Windows leen `OLLAMA_HOST` y conservan 11434
como valor por omisión. Para que Ollama vuelva a servir en 11435 después de un
reinicio, fija la variable para el usuario desde PowerShell y reinicia por
completo Ollama:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11435", "User")
```

Después del reinicio, verifica la API, no solo la existencia del proceso:

```powershell
Invoke-WebRequest http://127.0.0.1:11435/api/tags -UseBasicParsing
```

`start_lab_stack.ps1 -Profiles core -IncludeOllama` usa el mismo valor y
comprueba `/api/tags` antes de informar que Ollama ya está en ejecución.

## Medición TASK-93

Con la misma consulta RAG del workspace `bis_brain-segundo-cerebro`, y Gemini
forzado a fallar, `qwen3.5:9b` respondió en 41,133 segundos dentro del eslabón
local y 58,120 segundos de extremo a extremo. `qwen2.5:7b-instruct` tardó
67,744 segundos dentro del eslabón local y 79,576 segundos de extremo a extremo;
una segunda pasada agotó el timeout de 120 segundos. Ninguno alcanzó 20
segundos y el candidato fue peor. Por el criterio de aceptación se conserva
`qwen3.5:9b`; el modelo instruct queda instalado, pero no se configura como
respaldo.

## Medición TASK-96

Se repitió la misma consulta RAG real de TASK-93, con Gemini forzado a devolver
404 durante cada medición. Los cuatro modelos devolvieron el texto nativamente
en `message.content` y la consulta recuperó cuatro fuentes.

| Modelo | Eslabón local | Extremo a extremo | Campo |
|---|---:|---:|---|
| `qwen2.5:3b-instruct` | 4,234 s | 6,609 s | `content` |
| `llama3.2:3b` | 12,428 s | 18,735 s | `content` |
| `gemma2:2b` | 35,641 s | 43,563 s | `content` |
| `phi4-mini` | 11,828 s | 13,999 s | `content` |

Se eligió `qwen2.5:3b-instruct` por ser el candidato más rápido y quedar
holgadamente por debajo de 20 segundos. Una demostración final independiente
registró primero el 404 de Gemini (1,038 s) y luego el éxito local (5,604 s),
con 10,864 s de extremo a extremo. La invalidación temporal se retiró tras la
prueba.
