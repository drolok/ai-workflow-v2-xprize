# Protocolo de sesión persistente para despachos multi-IA

## Comandos exactos verificados — copiar/pegar, no reinventar (2026-07-27)

Todos probados en vivo hoy desde esta misma máquina. Usar estos tal cual
antes de improvisar variantes nuevas.

### Kimi CLI (PowerShell nativo — Windows, NUNCA WSL)

```powershell
kimi -p "PROMPT AQUI" -m kimi-code/k3-lean   # tarea acotada, esfuerzo bajo
kimi -p "PROMPT AQUI" -m kimi-code/k3        # tarea compleja, esfuerzo alto (default)
kimi -r session_<id>                          # resume — el id sale en el output de la corrida anterior ("To resume this session: kimi -r session_...")
```
**NUNCA agregar `-y`/`--yolo` ni `--auto` junto con `-p`** — Kimi tira
`error: Cannot combine --prompt with --yolo` (y lo mismo con `--auto`),
confirmado 2026-08-02. `-p` por sí solo ya corre no-interactivo y
aprueba tool calls sin bloquear — no hace falta ninguna flag extra de
auto-aprobación.

Config/logs reales: `<WINDOWS_HOME>\.kimi-code\config.toml`,
`<WINDOWS_HOME>\.kimi-code\logs\kimi-code.log`.

### Codex CLI (dos instalaciones distintas según entorno)

Desde WSL (worktrees de Tchasky viven ahí, es el caso normal):
```bash
wsl -d Ubuntu -- bash -lc "timeout 600 ~/.npm-global/bin/codex exec -s read-only 'PROMPT AQUI' < /dev/null 2>&1"
```
`bash -lc` (login shell) es obligatorio — `bash -c` simple no carga
`~/.npm-global` al PATH. `< /dev/null` es obligatorio (si no, cuelga
esperando stdin). Resume: `codex exec resume <thread_id>` con
`-c sandbox_mode="read-only"` (ver skill `grill-with-docs-codex` para el
flujo completo de review adversarial).

### Reporte crudo obligatorio por task (TASK-17)

Toda invocación directa de `codex exec` que ejecute un task debe persistir su
último mensaje con `-o`/`--output-last-message`. La ruta canónica es
`.ai/reports/TASK-NN.codex.md`; rondas posteriores usan
`.ai/reports/TASK-NN.codex.r2.md`, `.r3.md`, etc. Es el reporte original de
Codex: no se copia ni se resume a mano.

```bash
wsl -d Ubuntu -- bash -lc 'cd /mnt/c/RUTA/AL/WORKTREE && mkdir -p .ai/reports && timeout 600 ~/.npm-global/bin/codex exec -s read-only -o .ai/reports/TASK-NN.codex.md "PROMPT AQUI" < /dev/null 2>&1'
```

El modo `read-only` del ejemplo es el de una revision. Un task de OWNER que
tiene que escribir se lanza con `danger-full-access` (seccion 7 del protocolo
critico: caso por caso, o dentro de la ventana temporal activa), y el prompt
largo entra por stdin -- `cat handoff.md | codex exec ... -` -- en vez de ir
como argumento; con stdin ocupado NO se agrega la redireccion de /dev/null.
Esa forma con stdin es la verificada hoy 2026-08-11 en las tres invocaciones
de TASK-15/16/17.

`bash -lc` sigue siendo obligatorio porque el login shell carga
`~/.npm-global` en el PATH; con `bash -c` el binario puede no encontrarse.
La redireccion de /dev/null es obligatoria cuando el prompt va como argumento:
evita que `codex exec` quede esperando entrada estandar.

Antes de cerrar un task de Codex, correr `python .ai/bin/reality.py
reports-check`; un reporte ausente o vacio deja el chequeo en rojo. El puente
conserva `response_markdown` en `queue/responses/`; esta convencion cubre
solamente el camino directo y no duplica esa cola.

Sintaxis de `exec resume` VERIFICADA 2026-08-11 (S5, dos intentos fallidos
antes de acertar — no repetir):
```bash
wsl -d Ubuntu -- bash -lc 'cd /mnt/c/RUTA/AL/WORKTREE && timeout 1800 ~/.npm-global/bin/codex exec resume <thread_id> --json -c sandbox_mode="workspace-write" -o /mnt/c/.../salida.md - < /mnt/c/.../prompt.md > /mnt/c/.../stream.jsonl 2>&1'
```
- `exec resume` NO acepta `-C` ni `-s` (exit 2, "unexpected argument"): el
  working dir se fija con `cd` ANTES del binario, y el sandbox va como
  `-c sandbox_mode="..."`.
- El prompt va por STDIN con el argumento `-` — NUNCA `"$(cat file)"`, que
  ejecuta los backticks del markdown y entrega el prompt mutilado (gotcha 33
  de GOTCHAS_TECNICOS_CRITICOS.md).
- Resume genuino verificado: el stream arranca con `thread.started` y el
  MISMO thread_id — Codex retoma el contexto del task anterior sin re-pagar
  el prompt completo (167s la ronda de TASK-3 contra ~240s la ronda 1 fría
  de TASK-2).

#### Protocolo de `model_reasoning_effort` — cuándo usar cada nivel (2026-08-02)

Con cuenta ChatGPT, Codex está fijo a un solo modelo (probado: `sol`,
`terra`, `luna` son alias del mismo modelo, mismo sufijo interno
`-1p-codexswic-ev3`, no hay opción de modelo más chico). El único lever
real de costo/calidad es `-c model_reasoning_effort=<valor>`. Valores
válidos: `none, low, medium, high, xhigh, max`. Sin esta flag, el
default ya es `none` (el piso).

**Dato medido (benchmark real, misma tarea — agregar un rate limiter
siguiendo un patrón ya existente):**

| Effort | Input tokens | Output tokens |
|---|---|---|
| `none` | 231,599 | 1,634 |
| `low` | 376,812 | 3,017 (+63% vs none) |
| `medium` | 510,952 | 4,616 (+2.2x vs none) |

**Regla de uso — default `none`, escalar solo si hace falta:**

- **`none` (default, usar para el 90%+ de los dispatches):**
  implementar algo que sigue un patrón ya existente en el código
  (rate limiters, endpoints nuevos calcados de uno viejo, fixes con
  diagnóstico ya dado), auditorías/investigaciones con alcance claro
  (todas las 10 auditorías de seguridad del 2026-08-02 se hicieron a
  `none` con resultados detallados y verificados), consolidaciones/
  merges de ramas.
- **`low`/`medium` — escalar SOLO si `none` falló o dio un resultado
  incompleto/incorrecto** en un intento real (no como punto de partida
  por las dudas). Reservado para: diagnóstico de un bug sin pistas
  claras todavía, decisiones de arquitectura con trade-offs genuinos,
  tareas donde `none` ya demostró no alcanzar.
- **`high`/`xhigh`/`max` — no usar sin consultar al fundador primero**
  (costo alto, sección 5 de CLAUDE.md). Reservado para problemas
  genuinamente atascados después de que `medium` tampoco alcanzó.

No hay evidencia de que `low`/`medium` mejoren la calidad para tareas
de "seguir un patrón existente" — en el benchmark, `none` ya produjo
código correcto (test pasando, sin errores TS) al mismo nivel de
calidad que `medium`, con menos de la mitad del costo.

### Gemini CLI (accesible desde ambos, pero WSL exige un flag extra)

```powershell
gemini -p "PROMPT AQUI"                                    # PowerShell nativo
```
```bash
wsl -d Ubuntu -- bash -lc "gemini -p 'PROMPT AQUI' --skip-trust"   # WSL — sin --skip-trust falla con "not running in a trusted directory"
```

### OpenCode / modelos NVIDIA (el caballo de batalla de esta noche)

```powershell
wsl -d Ubuntu -e bash -c 'cd <HOME>/<worktree> && opencode run "$(cat "/mnt/c/ruta/al/prompt.md")" --agent build --model nvidia/z-ai/glm-5.2 --dir <HOME>/<worktree> --auto --format json > <HOME>/<log>.log 2>&1'
```
Reglas duras, ambas causaron fallos reales esta noche cuando se
ignoraron:
1. **El string completo de PowerShell tiene que ir en comillas SIMPLES
   por fuera** (`'...'`), nunca dobles. Con comillas dobles, PowerShell
   evalúa `$(cat ...)` él mismo antes de mandarlo a WSL — el prompt le
   llega vacío a `opencode` y responde cualquier cosa genérica sin hacer
   la tarea real. Pasó 4 veces seguidas hasta detectarlo (diff vacío en
   los 4 worktrees).
2. **NO envolver con `nohup ... &` dentro del `bash -c`.** Dejar que el
   propio parámetro `run_in_background: true` de la tool de PowerShell/Bash
   sostenga el proceso — si se backgroundea *dentro* de bash y el script
   termina, `wsl.exe` retorna y el proceso hijo muere en silencio (log
   queda vacío, sin error visible). El patrón correcto es UN solo comando
   en foreground dentro del `bash -c`, con `run_in_background: true` en la
   tool call que lo envuelve.

Verificar que quedó vivo de verdad (no solo que la tool no tiró error):
```powershell
wsl -d Ubuntu -e bash -c "wc -l <HOME>/<log>.log; pgrep -af 'opencode run'"
```
Resume de sesión: agregar `--session <sessionID>` (el id sale del stream
JSON, campo `"sessionID":"ses_..."`, en la primera corrida).

### Antigravity (bridge de archivos pasivo — NUNCA invocar el binario directo)

```powershell
cd C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE
python bridge_queue.py enqueue --from-agent claude --to-agent antigravity --kind task --title "TITULO" --task-id "id_unico" --body-text "PROMPT AQUI"
```
Antigravity lo recoge solo con su vigía pasivo interno. Respuesta aparece
en `queue\responses\<task_id>.json` (campo `response_markdown`). Armar
SIEMPRE, en la misma tanda de tool calls que el enqueue, un watcher
redundante:
```powershell
while (-not (Test-Path 'C:\AI_WORKFLOW_V2\...\queue\responses\<task_id>.json')) { Start-Sleep -Seconds 20 }; Write-Output "RESPUESTA LISTA: <task_id>"
```
(`run_in_background: true`). Jamás `antigravity-ide.cmd --new-window` —
prohibido explícitamente por el fundador, consume ~1GB RAM permanente por
invocación.


Reemplaza, desde 2026-07-26, el patrón de "prompt completo desde cero en
cada ronda" que se usó toda la noche vía `bridge_queue.py` para Codex,
Kimi y Antigravity. Motivo: cada ronda de corrección re-pegaba el
boilerplate completo (reglas de worktree, puertos, protocolo de auditoría,
formato de respuesta) + la tarea entera, en vez de continuar la sesión ya
existente del agente — el equivalente a pagar de nuevo por todo el
contexto en cada vuelta cuando el propio backend del agente ya lo tenía
cacheado.

Confirmado que los tres ejecutores usados esta noche soportan sesión
persistente nativa:

| Agente  | Flag de sesión                          | Notas |
|---------|------------------------------------------|-------|
| Codex   | `codex exec --json -o file` → parsear `thread_id`; ronda siguiente: `codex exec resume <thread_id>` | Ya formalizado en los skills `codex-build`/`codex-review` (`~/.claude/skills/`) — usar esos, no reinventar. |
| Gemini  | `--resume <latest\|índice>`, `--session-id <uuid>` | Bloqueado esta noche por auth OAuth que no se comparte Windows↔WSL y por el bug de cmd.exe con rutas UNC — pendiente de resolver con API key en vez de OAuth. |
| OpenCode| `-c, --continue`, `-s, --session <id>`, `--fork` | Confirmado disponible en `opencode --help` 2026-07-26. |
| Kimi    | `-S, --session [id]`, `-c, --continue` | Confirmado disponible en `kimi --help` 2026-07-26. |

## Entorno real de ejecución de cada IA — NO asumir, verificar acá primero (2026-07-27)

Error real cometido esta noche: se buscó el binario de Kimi dentro de WSL
(`which kimi`, `npm ls -g` en la distro Ubuntu) y no se encontró nada, lo
que llevó a reportarle al fundador un falso hallazgo de "Kimi no está
instalado en este entorno". La realidad: Kimi corre **nativo en Windows**,
no en WSL — el binario real es `<WINDOWS_HOME>\.kimi-code\bin\kimi.exe`,
invocado directo desde PowerShell (`kimi -p "..." -m kimi-code/k3-lean`),
NUNCA desde `wsl -e bash -c "kimi ..."`. Sus logs/config tampoco viven en
`~/.kimi-code/` de WSL (esa ruta no existe ahí) sino en
`<WINDOWS_HOME>\.kimi-code\` del lado Windows (`config.toml`,
`logs\kimi-code.log`, `session_index.jsonl`, `sessions\`).

Tabla de referencia — dónde vive y cómo se invoca cada IA, para no repetir
este error de nuevo con ninguna herramienta:

| IA / herramienta | Entorno real de ejecución | Cómo invocar | Dónde NO buscarla |
|---|---|---|---|
| **Kimi CLI** | Windows nativo | `PowerShell`: `kimi -p "..." -m kimi-code/k3\|k3-lean` | WSL/Ubuntu — el binario no existe ahí |
| **Codex CLI** | Ambos, pero son instalaciones DISTINTAS | Windows: `codex` (via `/mnt/c/.../npm/codex`, arquitectura Windows) — falla con "Missing optional dependency @openai/codex-linux-x64" si se llama desde dentro de WSL usando el path de Windows. Dentro de WSL usar la instalación nativa: `~/.npm-global/bin/codex` (WSL no carga `~/.npm-global` en `bash -c` no interactivo — usar `bash -lc` o el path completo). | No usar el `codex` del PATH de Windows montado en `/mnt/c` cuando se ejecuta *dentro* de WSL — es el binario equivocado para esa arquitectura. |
| **Gemini CLI** | Windows nativo (`/mnt/c/.../npm/gemini`), también accesible desde WSL vía el mismo mount | PowerShell o WSL: `gemini -p "..."`. Dentro de WSL requiere `--skip-trust` o `GEMINI_CLI_TRUST_WORKSPACE=true` (si no, error "not running in a trusted directory"). | — |
| **OpenCode (modelos NVIDIA)** | Windows nativo (`/mnt/c/.../npm/opencode`), accesible desde WSL vía el mismo mount | `opencode run "..." --agent build --model nvidia/... --dir <worktree>` — funciona bien desde `wsl -e bash -c` porque resuelve al binario de `/mnt/c`, no necesita instalación WSL-nativa. | — |
| **Antigravity** | Bridge de archivos únicamente (`bridge_queue.py` + carpeta `queue/`) | `python bridge_queue.py enqueue --from-agent claude --to-agent antigravity --kind task --title "..." --task-id "..." --body-text "..."`, Antigravity lo recoge con su propio vigía pasivo interno. | Nunca invocar `antigravity-ide.cmd` directo (consume ~1GB RAM permanente por ventana, prohibido explícitamente por el fundador). |

**Regla general para no repetir este error con cualquier IA nueva**: antes
de reportar "no está instalado" o "no está disponible", probar la
invocación real (ping corto) en AMBOS entornos — PowerShell nativo Y `wsl
bash -lc` — antes de concluir que algo no existe. Un `which`/`npm ls -g`
negativo en un solo entorno no es evidencia suficiente cuando el proyecto
mezcla routing Windows/WSL constantemente.

## Cadena de fallback de modelos NVIDIA vía OpenCode (verificado 2026-07-27)

NVIDIA hizo un recorte grande de catálogo justo el 2026-07-27 — varios
modelos que parecían buenos candidatos (Llama 4 Maverick, Qwen3-Coder
480B, Qwen3.5-397B) devuelven `410 Gone` con fecha de fin de vida ese
mismo día. No asumir que un modelo del catálogo (`opencode models`) sigue
vivo solo porque aparece listado — probarlo con un ping antes de darle
una tarea real.

Confirmados funcionando esa noche (usar en este orden):
1. `nvidia/z-ai/glm-5.2` — usado toda la noche para cluster5/cluster7,
   sin costo reportado.
2. `nvidia/meta/llama-3.3-70b-instruct` — confirmado con ping y con tarea
   real (taxonomia cluster7), sin costo reportado.
3. `nvidia/deepseek-ai/deepseek-v4-pro` — confirmado con ping, SI tiene
   costo real por token (a diferencia de los otros dos) - preferir los
   dos anteriores primero si el costo importa.

Confirmados NO disponibles (no reintentar sin volver a chequear el
catalogo primero): `nvidia/meta/llama-4-maverick-17b-128e-instruct`,
`nvidia/qwen/qwen3-coder-480b-a35b-instruct`,
`nvidia/qwen/qwen3.5-397b-a17b`.

## Control de esfuerzo de razonamiento (Kimi, específico)

Kimi CLI usa por defecto `kimi-code/kimi-for-coding`, que tiene
`always_thinking` — no se puede apagar ni graduar el razonamiento con ese
alias. Verificado en `~/.kimi-code/config.toml` (2026-07-26) que el alias
`kimi-code/k3` sí soporta `support_efforts = ["low","high","max"]`. Se
agregó un alias nuevo `kimi-code/k3-lean` (mismo modelo `k3`, `default_effort
= "low"`) para tareas donde no hace falta razonamiento máximo. Uso:
- Tarea genuinamente compleja (lo que el fundador quiere reservar para
  Kimi): `-m kimi-code/k3` (effort `high`, el default del alias).
- Tarea donde se necesita Kimi pero el problema es acotado: `-m
  kimi-code/k3-lean` (effort `low`) — reduce el volumen de razonamiento
  interno que se factura como output tokens, sin cambiar de modelo.
- Nunca usar el alias por defecto `kimi-for-coding` para dispatches
  largos si se puede evitar — no permite ajustar el esfuerzo en absoluto.

## Regla de despacho, en adelante

1. **Primera ronda de cada tarea**: prompt completo (boilerplate de
   worktree/puertos/auditoría + tarea específica), igual que antes.
   Capturar el identificador de sesión que devuelva el ejecutor (thread_id
   de Codex, session id de OpenCode/Gemini).
2. **Rondas de corrección** (cuando Claude audita y encuentra algo que
   arreglar): NO redespachar el prompt completo. Usar el flag de resume
   del agente + un mensaje corto con el problema puntual. El agente ya
   tiene todo el contexto de la ronda anterior.
3. Guardar el id de sesión en el mismo lugar donde se guarda el estado del
   dispatch (hoy: los archivos `_body_*.md`/log de la tarea) para poder
   resumirlo después sin tener que buscarlo en logs crudos.

## Boilerplate canónico (no volver a re-tipear por agente)

Los cuatro `_body_*.md` de esta noche repetían casi textual este bloque —
de ahora en más, un dispatch nuevo solo debe REFERENCIAR este archivo
("leé primero SESSION_RESUME_PROTOCOL.md § Boilerplate") en vez de
reincluir el texto:

- Worktree aislado asignado, rama, y qué otros worktrees existen en
  paralelo (no tocar).
- Postgres/Redis compartidos entre worktrees; puerto de API dedicado por
  worktree (mapa de puertos vive en `CURRENT_STATE.md`).
- No push, no commit hasta que Claude coordine el merge.
- Nivel de auditoría estándar: cobertura razonable, cero warnings nuevos
  de lint, cero `any`/`@ts-ignore` nuevos, tests reales.
- Validación final: suite completa contra el puerto propio, eslint,
  typecheck.
- Detenerse y reportar ambigüedad real en vez de inventar; seguir con
  ítems independientes.

## Por qué esto no aplica igual a Antigravity

Antigravity se despacha vía `antigravity-ide.cmd chat --mode agent
--reuse-window`, que reutiliza la ventana/sesión de IDE ya abierta — el
mecanismo de continuidad ahí es distinto (una sesión de IDE persistente,
no un thread_id de API) pero el efecto es el mismo: no hace falta
repasarle todo el contexto en cada mensaje nuevo si la ventana sigue
abierta. Mismo principio, mecanismo distinto.
